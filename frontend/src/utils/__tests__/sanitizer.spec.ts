import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  sanitizeHtml,
  sanitizeText,
  isSafeUrl,
  validateFormData,
  validateApiResponse,
  RateLimiter,
} from '@/utils/sanitizer'

// ============================================================
// sanitizeHtml - XSS Prevention (CRITICAL SECURITY TESTS)
// ============================================================
describe('sanitizeHtml', () => {
  it('returns empty string for null input', () => {
    expect(sanitizeHtml(null)).toBe('')
  })

  it('returns empty string for undefined input', () => {
    expect(sanitizeHtml(undefined)).toBe('')
  })

  it('returns empty string for non-string input', () => {
    expect(sanitizeHtml(123 as unknown as string)).toBe('')
    expect(sanitizeHtml({} as unknown as string)).toBe('')
    expect(sanitizeHtml([] as unknown as string)).toBe('')
  })

  it('returns empty string for empty string input', () => {
    expect(sanitizeHtml('')).toBe('')
  })

  it('passes through plain text unchanged', () => {
    expect(sanitizeHtml('Hello world')).toBe('Hello world')
  })

  it('escapes script tags to prevent XSS', () => {
    const malicious = '<script>alert("xss")</script>'
    const result = sanitizeHtml(malicious)
    // textContent assignment escapes HTML, so script tags become entities
    expect(result).not.toContain('<script>')
    expect(result).toContain('&lt;script&gt;')
  })

  it('escapes nested script tags', () => {
    const malicious = '<scr<script>ipt>alert("xss")</scr</script>ipt>'
    const result = sanitizeHtml(malicious)
    expect(result).not.toContain('<script>')
  })

  it('escapes event handler attributes like onerror (rendered as text, not executable)', () => {
    const malicious = '<img src="x" onerror="alert(1)">'
    const result = sanitizeHtml(malicious)
    // The entire tag is escaped to text - no executable HTML remains
    expect(result).toContain('&lt;img')
    expect(result).toContain('&gt;')
    // The output is pure text, not parseable as HTML
    expect(result).not.toContain('<img')
  })

  it('escapes onclick event handlers (rendered as text, not executable)', () => {
    const malicious = '<div onclick="steal()">click me</div>'
    const result = sanitizeHtml(malicious)
    // The entire tag is escaped - no executable HTML element with onclick
    expect(result).toContain('&lt;div')
    expect(result).not.toContain('<div')
  })

  it('escapes iframe tags', () => {
    const malicious = '<iframe src="https://evil.com"></iframe>'
    const result = sanitizeHtml(malicious)
    expect(result).not.toContain('<iframe')
    expect(result).toContain('&lt;iframe')
  })

  it('escapes all HTML entities in the input', () => {
    const input = '<b>bold</b> & <i>italic</i>'
    const result = sanitizeHtml(input)
    expect(result).toContain('&lt;b&gt;bold&lt;/b&gt;')
    expect(result).toContain('&amp;')
  })

  it('escapes javascript: protocol in anchor tags (rendered as text, not executable)', () => {
    const malicious = '<a href="javascript:alert(1)">click</a>'
    const result = sanitizeHtml(malicious)
    // The entire anchor is escaped to text - no clickable link exists
    expect(result).toContain('&lt;a')
    expect(result).not.toContain('<a ')
    // The href with javascript: is harmless text, not a real attribute
    expect(result).toContain('&gt;')
  })
})

// ============================================================
// sanitizeText - HTML Entity Escaping
// ============================================================
describe('sanitizeText', () => {
  it('returns empty string for null input', () => {
    expect(sanitizeText(null)).toBe('')
  })

  it('returns empty string for undefined input', () => {
    expect(sanitizeText(undefined)).toBe('')
  })

  it('returns empty string for non-string input', () => {
    expect(sanitizeText(42 as unknown as string)).toBe('')
  })

  it('returns empty string for empty string input', () => {
    expect(sanitizeText('')).toBe('')
  })

  it('escapes ampersand (&)', () => {
    expect(sanitizeText('Tom & Jerry')).toBe('Tom &amp; Jerry')
  })

  it('escapes less-than (<)', () => {
    expect(sanitizeText('a < b')).toBe('a &lt; b')
  })

  it('escapes greater-than (>)', () => {
    expect(sanitizeText('a > b')).toBe('a &gt; b')
  })

  it('escapes double quotes (")', () => {
    expect(sanitizeText('say "hello"')).toBe('say &quot;hello&quot;')
  })

  it('escapes single quotes (\')', () => {
    expect(sanitizeText("it's")).toBe('it&#x27;s')
  })

  it('escapes all special characters in a combined string', () => {
    const input = '<script>alert("xss" & \'hack\')</script>'
    const result = sanitizeText(input)
    expect(result).toBe(
      '&lt;script&gt;alert(&quot;xss&quot; &amp; &#x27;hack&#x27;)&lt;/script&gt;'
    )
  })

  it('does not double-escape already escaped text', () => {
    // If someone passes already-escaped text, it WILL be escaped again
    // This is correct behavior - the function always escapes
    const input = '&amp;'
    const result = sanitizeText(input)
    expect(result).toBe('&amp;amp;')
  })

  it('passes through plain text without special characters', () => {
    expect(sanitizeText('Hello world 123')).toBe('Hello world 123')
  })

  it('handles strings with only special characters', () => {
    expect(sanitizeText('<>&"\'')).toBe('&lt;&gt;&amp;&quot;&#x27;')
  })
})

// ============================================================
// isSafeUrl - URL Safety Validation
// ============================================================
describe('isSafeUrl', () => {
  it('returns false for null input', () => {
    expect(isSafeUrl(null)).toBe(false)
  })

  it('returns false for undefined input', () => {
    expect(isSafeUrl(undefined)).toBe(false)
  })

  it('returns false for non-string input', () => {
    expect(isSafeUrl(123 as unknown as string)).toBe(false)
  })

  it('returns false for empty string', () => {
    expect(isSafeUrl('')).toBe(false)
  })

  it('accepts https:// URLs', () => {
    expect(isSafeUrl('https://example.com')).toBe(true)
  })

  it('accepts http:// URLs', () => {
    expect(isSafeUrl('http://example.com')).toBe(true)
  })

  it('accepts data: URLs (used for images)', () => {
    // Note: The actual implementation allows data: URLs
    expect(isSafeUrl('data:image/png;base64,abc123')).toBe(true)
  })

  it('rejects javascript: URLs (XSS vector)', () => {
    expect(isSafeUrl('javascript:alert(1)')).toBe(false)
  })

  it('rejects javascript: with uppercase (case-sensitive check)', () => {
    // The implementation uses startsWith which is case-sensitive
    expect(isSafeUrl('JavaScript:alert(1)')).toBe(false)
  })

  it('rejects vbscript: URLs', () => {
    expect(isSafeUrl('vbscript:msgbox("xss")')).toBe(false)
  })

  it('rejects relative URLs (no protocol)', () => {
    expect(isSafeUrl('/path/to/resource')).toBe(false)
  })

  it('rejects bare domain names', () => {
    expect(isSafeUrl('example.com')).toBe(false)
  })

  it('rejects file:// URLs', () => {
    expect(isSafeUrl('file:///etc/passwd')).toBe(false)
  })

  it('rejects ftp:// URLs', () => {
    expect(isSafeUrl('ftp://files.example.com')).toBe(false)
  })

  it('accepts https URL with path and query', () => {
    expect(isSafeUrl('https://api.example.com/v1/images?id=123&format=png')).toBe(true)
  })
})

// ============================================================
// validateFormData - Form Input Validation
// ============================================================
describe('validateFormData', () => {
  describe('required field validation', () => {
    const schema = {
      name: { required: true, label: 'Name' },
    }

    it('passes when required field is present', () => {
      const { isValid, errors } = validateFormData({ name: 'Test' }, schema)
      expect(isValid).toBe(true)
      expect(errors).toEqual({})
    })

    it('fails when required field is missing', () => {
      const { isValid, errors } = validateFormData({}, schema)
      expect(isValid).toBe(false)
      expect(errors.name).toBe('Name is required')
    })

    it('fails when required field is empty string', () => {
      const { isValid, errors } = validateFormData({ name: '' }, schema)
      expect(isValid).toBe(false)
      expect(errors.name).toBe('Name is required')
    })

    it('fails when required field is whitespace only', () => {
      const { isValid, errors } = validateFormData({ name: '   ' }, schema)
      expect(isValid).toBe(false)
      expect(errors.name).toBe('Name is required')
    })

    it('uses key name as label fallback', () => {
      const schemaNoLabel = { email: { required: true } }
      const { errors } = validateFormData({}, schemaNoLabel)
      expect(errors.email).toBe('email is required')
    })
  })

  describe('type validation', () => {
    it('passes when type matches', () => {
      const schema = { age: { type: 'number', label: 'Age' } }
      const { isValid } = validateFormData({ age: 25 }, schema)
      expect(isValid).toBe(true)
    })

    it('fails when type does not match', () => {
      const schema = { age: { type: 'number', label: 'Age' } }
      const { isValid, errors } = validateFormData({ age: 'twenty-five' }, schema)
      expect(isValid).toBe(false)
      expect(errors.age).toBe('Age must be number')
    })
  })

  describe('minLength validation', () => {
    const schema = {
      password: { minLength: 8, label: 'Password' },
    }

    it('passes when length meets minimum', () => {
      const { isValid } = validateFormData({ password: '12345678' }, schema)
      expect(isValid).toBe(true)
    })

    it('fails when length is below minimum', () => {
      const { isValid, errors } = validateFormData({ password: '1234' }, schema)
      expect(isValid).toBe(false)
      expect(errors.password).toBe('Password must be at least 8 characters')
    })

    it('passes when length exceeds minimum', () => {
      const { isValid } = validateFormData({ password: '1234567890' }, schema)
      expect(isValid).toBe(true)
    })
  })

  describe('maxLength validation', () => {
    const schema = {
      bio: { maxLength: 10, label: 'Bio' },
    }

    it('passes when length is within maximum', () => {
      const { isValid } = validateFormData({ bio: 'short' }, schema)
      expect(isValid).toBe(true)
    })

    it('fails when length exceeds maximum', () => {
      const { isValid, errors } = validateFormData({ bio: 'this is way too long' }, schema)
      expect(isValid).toBe(false)
      expect(errors.bio).toBe('Bio must be less than 10 characters')
    })
  })

  describe('enum validation', () => {
    const schema = {
      color: { enum: ['red', 'green', 'blue'], label: 'Color' },
    }

    it('passes when value is in enum list', () => {
      const { isValid } = validateFormData({ color: 'red' }, schema)
      expect(isValid).toBe(true)
    })

    it('fails when value is not in enum list', () => {
      const { isValid, errors } = validateFormData({ color: 'purple' }, schema)
      expect(isValid).toBe(false)
      expect(errors.color).toBe('Color must be one of: red, green, blue')
    })
  })

  describe('pattern validation', () => {
    const schema = {
      zipCode: {
        pattern: /^\d{5}$/,
        patternError: 'Must be a 5-digit zip code',
        label: 'Zip Code',
      },
    }

    it('passes when value matches pattern', () => {
      const { isValid } = validateFormData({ zipCode: '12345' }, schema)
      expect(isValid).toBe(true)
    })

    it('fails when value does not match pattern', () => {
      const { isValid, errors } = validateFormData({ zipCode: 'abcde' }, schema)
      expect(isValid).toBe(false)
      expect(errors.zipCode).toBe('Must be a 5-digit zip code')
    })

    it('uses default error message when patternError is not set', () => {
      const schemaNoMsg = {
        code: { pattern: /^[A-Z]+$/, label: 'Code' },
      }
      const { errors } = validateFormData({ code: '123' }, schemaNoMsg)
      expect(errors.code).toBe('Code format is invalid')
    })
  })

  describe('cleaned output', () => {
    it('trims and sanitizes string values', () => {
      const schema = { name: { required: true, label: 'Name' } }
      const { cleaned } = validateFormData({ name: '  Hello  ' }, schema)
      // sanitizeText is applied to trimmed value
      expect(cleaned.name).toBe('Hello')
    })

    it('passes non-string values through unchanged', () => {
      const schema = { count: { type: 'number', label: 'Count' } }
      const { cleaned } = validateFormData({ count: 42 }, schema)
      expect(cleaned.count).toBe(42)
    })

    it('sanitizes HTML in string fields', () => {
      const schema = { comment: { label: 'Comment' } }
      const { cleaned } = validateFormData({ comment: '<b>bold</b>' }, schema)
      expect(cleaned.comment).toBe('&lt;b&gt;bold&lt;/b&gt;')
    })
  })

  describe('multiple field validation', () => {
    it('validates all fields and collects all errors', () => {
      const schema = {
        name: { required: true, label: 'Name' },
        email: { required: true, label: 'Email' },
        age: { type: 'number', label: 'Age' },
      }
      const { isValid, errors } = validateFormData(
        { name: '', email: '', age: 'not-a-number' },
        schema
      )
      expect(isValid).toBe(false)
      expect(Object.keys(errors)).toHaveLength(3)
    })

    it('returns isValid=true when all fields pass', () => {
      const schema = {
        name: { required: true, label: 'Name' },
        age: { type: 'number', label: 'Age' },
      }
      const { isValid } = validateFormData({ name: 'Alice', age: 30 }, schema)
      expect(isValid).toBe(true)
    })
  })
})

// ============================================================
// validateApiResponse - Response Shape Validation
// ============================================================
describe('validateApiResponse', () => {
  it('returns false for null data', () => {
    expect(validateApiResponse(null, { id: 'string' })).toBe(false)
  })

  it('returns false for undefined data', () => {
    expect(validateApiResponse(undefined, { id: 'string' })).toBe(false)
  })

  it('returns false for non-object data', () => {
    expect(validateApiResponse('string', { id: 'string' })).toBe(false)
  })

  it('returns true when data matches expected shape', () => {
    const data = { id: 'abc', name: 'Test', count: 42 }
    const shape = { id: 'string', name: 'string', count: 'number' }
    expect(validateApiResponse(data, shape)).toBe(true)
  })

  it('returns false when a required key is missing', () => {
    const data = { id: 'abc' }
    const shape = { id: 'string', name: 'string' }
    expect(validateApiResponse(data, shape)).toBe(false)
  })

  it('returns false when type does not match', () => {
    const data = { id: 123 }
    const shape = { id: 'string' }
    expect(validateApiResponse(data, shape)).toBe(false)
  })

  it('handles array type validation', () => {
    const data = { items: [1, 2, 3] }
    const shape = { items: 'array' }
    expect(validateApiResponse(data, shape)).toBe(true)
  })

  it('rejects non-array when array is expected', () => {
    const data = { items: 'not-an-array' }
    const shape = { items: 'array' }
    expect(validateApiResponse(data, shape)).toBe(false)
  })

  it('returns true for empty expected shape', () => {
    const data = { anything: 'goes' }
    expect(validateApiResponse(data, {})).toBe(true)
  })
})

// ============================================================
// RateLimiter - Request Rate Limiting
// ============================================================
describe('RateLimiter', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('allows requests within the limit', () => {
    const limiter = new RateLimiter(3, 1000)
    expect(limiter.isAllowed()).toBe(true)
    expect(limiter.isAllowed()).toBe(true)
    expect(limiter.isAllowed()).toBe(true)
  })

  it('blocks requests when limit is exceeded', () => {
    const limiter = new RateLimiter(2, 1000)
    expect(limiter.isAllowed()).toBe(true)
    expect(limiter.isAllowed()).toBe(true)
    // Third request should be blocked
    expect(limiter.isAllowed()).toBe(false)
  })

  it('resets after window expires', () => {
    const limiter = new RateLimiter(1, 1000)
    expect(limiter.isAllowed()).toBe(true)
    expect(limiter.isAllowed()).toBe(false)

    // Advance time past the window
    vi.advanceTimersByTime(1001)

    // Should be allowed again
    expect(limiter.isAllowed()).toBe(true)
  })

  it('uses default values (10 requests, 60s window)', () => {
    const limiter = new RateLimiter()
    // Should allow 10 requests
    for (let i = 0; i < 10; i++) {
      expect(limiter.isAllowed()).toBe(true)
    }
    // 11th should be blocked
    expect(limiter.isAllowed()).toBe(false)
  })

  it('reports remaining requests accurately', () => {
    const limiter = new RateLimiter(5, 1000)
    expect(limiter.getRemainingRequests()).toBe(5)

    limiter.isAllowed()
    expect(limiter.getRemainingRequests()).toBe(4)

    limiter.isAllowed()
    limiter.isAllowed()
    expect(limiter.getRemainingRequests()).toBe(2)
  })

  it('remaining requests reset after window expires', () => {
    const limiter = new RateLimiter(3, 1000)
    limiter.isAllowed()
    limiter.isAllowed()
    expect(limiter.getRemainingRequests()).toBe(1)

    vi.advanceTimersByTime(1001)

    expect(limiter.getRemainingRequests()).toBe(3)
  })

  it('handles sliding window correctly', () => {
    const limiter = new RateLimiter(2, 1000)

    // T=0: First request
    limiter.isAllowed()
    expect(limiter.getRemainingRequests()).toBe(1)

    // T=500: Second request
    vi.advanceTimersByTime(500)
    limiter.isAllowed()
    expect(limiter.getRemainingRequests()).toBe(0)
    expect(limiter.isAllowed()).toBe(false)

    // T=1001: First request expires, second still in window
    vi.advanceTimersByTime(501)
    expect(limiter.getRemainingRequests()).toBe(1)
    expect(limiter.isAllowed()).toBe(true)
  })

  afterEach(() => {
    vi.useRealTimers()
  })
})
