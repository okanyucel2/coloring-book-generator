/**
 * HTML Sanitizer Utility
 * Removes potentially dangerous HTML/JS from user content
 * Prevents XSS attacks in prompt library and variation history
 */

const DANGEROUS_TAGS: readonly string[] = [
  'script', 'iframe', 'object', 'embed', 'link', 'meta', 'style'
]

const DANGEROUS_ATTRS: readonly string[] = [
  'onclick', 'onload', 'onerror', 'onmouseover', 'onmouseout',
  'onkeydown', 'onkeyup', 'onfocus', 'onblur', 'onchange',
  'onsubmit', 'ondblclick', 'onwheel'
]

/**
 * Sanitize HTML string to prevent XSS
 */
export function sanitizeHtml(html: string | null | undefined): string {
  if (!html || typeof html !== 'string') return ''

  // Create temporary DOM element
  const temp = document.createElement('div')
  temp.textContent = html // Use textContent instead of innerHTML to prevent parsing
  return temp.innerHTML
}

/**
 * Sanitize plain text (escape HTML characters)
 */
export function sanitizeText(text: string | null | undefined): string {
  if (!text || typeof text !== 'string') return ''

  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

/**
 * Validate URL for safety
 */
export function isSafeUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string') return false

  // Allow http, https, and data URLs for images
  const safeProtocols = ['http://', 'https://', 'data:']
  return safeProtocols.some(protocol => url.startsWith(protocol))
}

export interface ValidationRule {
  type?: string
  required?: boolean
  label?: string
  minLength?: number
  maxLength?: number
  minValue?: number
  maxValue?: number
  pattern?: RegExp
  patternError?: string
  enum?: string[]
}

export interface ValidationSchema {
  [key: string]: ValidationRule
}

export interface ValidationResult {
  cleaned: Record<string, unknown>
  errors: Record<string, string>
  isValid: boolean
}

/**
 * Validate and clean form data
 */
export function validateFormData(data: Record<string, unknown>, schema: ValidationSchema): ValidationResult {
  const errors: Record<string, string> = {}
  const cleaned: Record<string, unknown> = {}

  for (const [key, rules] of Object.entries(schema)) {
    const value = data[key]

    // Check required
    if (rules.required && (!value || (typeof value === 'string' && !value.trim()))) {
      errors[key] = `${rules.label || key} is required`
      continue
    }

    // Check type
    if (value && rules.type && typeof value !== rules.type) {
      errors[key] = `${rules.label || key} must be ${rules.type}`
      continue
    }

    // Check min length
    if (value && rules.minLength && typeof value === 'string' && value.length < rules.minLength) {
      errors[key] = `${rules.label || key} must be at least ${rules.minLength} characters`
      continue
    }

    // Check max length
    if (value && rules.maxLength && typeof value === 'string' && value.length > rules.maxLength) {
      errors[key] = `${rules.label || key} must be less than ${rules.maxLength} characters`
      continue
    }

    // Check pattern
    if (value && rules.pattern && typeof value === 'string' && !rules.pattern.test(value)) {
      errors[key] = rules.patternError || `${rules.label || key} format is invalid`
      continue
    }

    // Check enum
    if (value && rules.enum && typeof value === 'string' && !rules.enum.includes(value)) {
      errors[key] = `${rules.label || key} must be one of: ${rules.enum.join(', ')}`
      continue
    }

    // Sanitize string values
    if (typeof value === 'string') {
      cleaned[key] = sanitizeText(value.trim())
    } else {
      cleaned[key] = value
    }
  }

  return { cleaned, errors, isValid: Object.keys(errors).length === 0 }
}

/**
 * Validate API response data
 */
export function validateApiResponse(data: unknown, expectedShape: Record<string, string>): boolean {
  if (!data || typeof data !== 'object') return false

  for (const [key, expectedType] of Object.entries(expectedShape)) {
    if (!(key in (data as Record<string, unknown>))) return false

    const actual = typeof (data as Record<string, unknown>)[key]
    if (actual !== expectedType && !(expectedType === 'array' && Array.isArray((data as Record<string, unknown>)[key]))) {
      return false
    }
  }

  return true
}

/**
 * Rate limiter for API calls
 */
export class RateLimiter {
  private maxRequests: number
  private windowMs: number
  private requests: number[]

  constructor(maxRequests = 10, windowMs = 60000) {
    this.maxRequests = maxRequests
    this.windowMs = windowMs
    this.requests = []
  }

  isAllowed(): boolean {
    const now = Date.now()
    // Remove old requests outside the window
    this.requests = this.requests.filter(time => now - time < this.windowMs)

    if (this.requests.length >= this.maxRequests) {
      return false
    }

    this.requests.push(now)
    return true
  }

  getRemainingRequests(): number {
    const now = Date.now()
    this.requests = this.requests.filter(time => now - time < this.windowMs)
    return this.maxRequests - this.requests.length
  }
}

/**
 * Data validator for prompt library
 */
export const promptValidationSchema: ValidationSchema = {
  name: {
    type: 'string',
    required: true,
    label: 'Prompt Name',
    minLength: 1,
    maxLength: 100
  },
  promptText: {
    type: 'string',
    required: true,
    label: 'Prompt Text',
    minLength: 10,
    maxLength: 2000
  },
  category: {
    type: 'string',
    required: false,
    label: 'Category',
    enum: ['landscape', 'portrait', 'abstract', 'animals', 'patterns', 'other']
  },
  tags: {
    type: 'array',
    required: false,
    label: 'Tags',
    maxLength: 10 // max 10 tags
  },
  isPublic: {
    type: 'boolean',
    required: false,
    label: 'Public Share'
  }
}

/**
 * Data validator for variation history
 */
export const variationValidationSchema: ValidationSchema = {
  id: {
    type: 'string',
    required: true,
    label: 'ID'
  },
  model: {
    type: 'string',
    required: true,
    label: 'Model',
    enum: ['dall-e-3', 'midjourney', 'stable-diffusion', 'flux']
  },
  prompt: {
    type: 'string',
    required: true,
    label: 'Prompt',
    minLength: 1,
    maxLength: 2000
  },
  imageUrl: {
    type: 'string',
    required: true,
    label: 'Image URL'
  },
  seed: {
    type: 'string',
    required: true,
    label: 'Seed',
    pattern: /^[0-9]+$/,
    patternError: 'Seed must be a number'
  },
  width: {
    type: 'number',
    required: true,
    label: 'Width'
  },
  height: {
    type: 'number',
    required: true,
    label: 'Height'
  },
  rating: {
    type: 'number',
    required: false,
    label: 'Rating',
    minValue: 0,
    maxValue: 5
  },
  notes: {
    type: 'string',
    required: false,
    label: 'Notes',
    maxLength: 500
  },
  createdAt: {
    type: 'string',
    required: true,
    label: 'Created At'
  }
}

export default {
  sanitizeHtml,
  sanitizeText,
  isSafeUrl,
  validateFormData,
  validateApiResponse,
  RateLimiter,
  promptValidationSchema,
  variationValidationSchema
}
