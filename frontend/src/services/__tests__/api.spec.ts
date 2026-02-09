import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ApiService } from '@/services/api'

// ============================================================
// ApiService Unit Tests
// Uses global fetch mock (jsdom environment)
// ============================================================

describe('ApiService', () => {
  let service: ApiService
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    service = new ApiService('https://api.test.com')
    fetchMock = vi.fn()
    global.fetch = fetchMock
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ----------------------------------------------------------
  // Constructor & Configuration
  // ----------------------------------------------------------
  describe('Constructor & Configuration', () => {
    it('creates an instance with the provided base URL', () => {
      const custom = new ApiService('https://custom.api.com')
      // Verify by making a request and checking the URL
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })
      custom.get('/test')
      expect(fetchMock).toHaveBeenCalledWith(
        'https://custom.api.com/test',
        expect.any(Object)
      )
    })

    it('sets Content-Type header to application/json by default', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/test')

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].headers['Content-Type']).toBe('application/json')
    })
  })

  // ----------------------------------------------------------
  // Authentication
  // ----------------------------------------------------------
  describe('Authentication', () => {
    it('sets Authorization header with Bearer token', async () => {
      service.setAuthToken('my-secret-token')

      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/protected')

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].headers['Authorization']).toBe('Bearer my-secret-token')
    })

    it('clears Authorization header', async () => {
      service.setAuthToken('token-to-clear')
      service.clearAuthToken()

      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/public')

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].headers['Authorization']).toBeUndefined()
    })

    it('persists auth token across multiple requests', async () => {
      service.setAuthToken('persistent-token')

      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/first')
      await service.get('/second')

      expect(fetchMock.mock.calls[0][1].headers['Authorization']).toBe('Bearer persistent-token')
      expect(fetchMock.mock.calls[1][1].headers['Authorization']).toBe('Bearer persistent-token')
    })
  })

  // ----------------------------------------------------------
  // GET Requests
  // ----------------------------------------------------------
  describe('GET Requests', () => {
    it('makes a GET request to the correct URL', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ id: 1 }),
      })

      await service.get('/users/1')

      expect(fetchMock).toHaveBeenCalledWith(
        'https://api.test.com/users/1',
        expect.objectContaining({ method: 'GET' })
      )
    })

    it('returns parsed JSON response', async () => {
      const mockData = { id: 1, name: 'Alice' }
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => mockData,
      })

      const result = await service.get('/users/1')
      expect(result).toEqual(mockData)
    })

    it('does not include a body in GET requests', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/data')

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].body).toBeUndefined()
    })
  })

  // ----------------------------------------------------------
  // POST Requests
  // ----------------------------------------------------------
  describe('POST Requests', () => {
    it('makes a POST request with JSON body', async () => {
      const payload = { name: 'New User', email: 'user@test.com' }
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ id: 2, ...payload }),
      })

      await service.post('/users', payload)

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].method).toBe('POST')
      expect(callArgs[1].body).toBe(JSON.stringify(payload))
    })

    it('handles POST without a body', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ triggered: true }),
      })

      await service.post('/trigger')

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].method).toBe('POST')
      expect(callArgs[1].body).toBeUndefined()
    })

    it('returns the created resource', async () => {
      const created = { id: 99, name: 'Created Item' }
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => created,
      })

      const result = await service.post('/items', { name: 'Created Item' })
      expect(result).toEqual(created)
    })
  })

  // ----------------------------------------------------------
  // PUT Requests
  // ----------------------------------------------------------
  describe('PUT Requests', () => {
    it('makes a PUT request with correct method', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.put('/users/1', { name: 'Updated' })

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].method).toBe('PUT')
      expect(callArgs[1].body).toBe(JSON.stringify({ name: 'Updated' }))
    })
  })

  // ----------------------------------------------------------
  // PATCH Requests
  // ----------------------------------------------------------
  describe('PATCH Requests', () => {
    it('makes a PATCH request with correct method', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.patch('/users/1', { status: 'active' })

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].method).toBe('PATCH')
      expect(callArgs[1].body).toBe(JSON.stringify({ status: 'active' }))
    })
  })

  // ----------------------------------------------------------
  // DELETE Requests
  // ----------------------------------------------------------
  describe('DELETE Requests', () => {
    it('makes a DELETE request with correct method', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.delete('/users/1')

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].method).toBe('DELETE')
    })

    it('does not include a body in DELETE requests', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.delete('/items/5')

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].body).toBeUndefined()
    })
  })

  // ----------------------------------------------------------
  // Custom Headers
  // ----------------------------------------------------------
  describe('Custom Headers', () => {
    it('merges custom headers with defaults', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/data', {
        headers: { 'X-Custom-Header': 'custom-value' },
      })

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].headers['Content-Type']).toBe('application/json')
      expect(callArgs[1].headers['X-Custom-Header']).toBe('custom-value')
    })

    it('allows overriding default headers', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/data', {
        headers: { 'Content-Type': 'text/plain' },
      })

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].headers['Content-Type']).toBe('text/plain')
    })
  })

  // ----------------------------------------------------------
  // Abort Signal (Request Cancellation)
  // ----------------------------------------------------------
  describe('Request Cancellation', () => {
    it('passes AbortSignal to fetch', async () => {
      const controller = new AbortController()

      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/cancellable', { signal: controller.signal })

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].signal).toBe(controller.signal)
    })

    it('throws "Request was cancelled" on abort', async () => {
      const abortError = new Error('The operation was aborted')
      abortError.name = 'AbortError'
      fetchMock.mockRejectedValue(abortError)

      await expect(service.get('/cancelled')).rejects.toThrow('Request was cancelled')
    })
  })

  // ----------------------------------------------------------
  // Error Handling
  // ----------------------------------------------------------
  describe('Error Handling', () => {
    it('throws on network error', async () => {
      fetchMock.mockRejectedValue(new Error('Network error'))

      await expect(service.get('/offline')).rejects.toThrow('Network error')
    })

    it('throws error with message from JSON response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 400,
        headers: { get: () => 'application/json' },
        json: async () => ({ message: 'Invalid input' }),
      })

      await expect(service.post('/validate', {})).rejects.toThrow('Invalid input')
    })

    it('throws error with error field from JSON response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 422,
        headers: { get: () => 'application/json' },
        json: async () => ({ error: 'Validation failed' }),
      })

      await expect(service.post('/validate', {})).rejects.toThrow('Validation failed')
    })

    it('throws generic HTTP error when no message in response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await expect(service.get('/server-error')).rejects.toThrow('HTTP 500')
    })

    it('throws on non-JSON error response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        headers: { get: () => 'text/html' },
      })

      await expect(service.get('/bad-gateway')).rejects.toThrow('HTTP 502: Bad Gateway')
    })

    it('returns empty object for non-JSON success response', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        status: 204,
        headers: { get: () => null },
      })

      const result = await service.delete('/items/1')
      expect(result).toEqual({})
    })

    it('wraps non-Error throws as unknown error', async () => {
      fetchMock.mockRejectedValue('string error')

      await expect(service.get('/unknown')).rejects.toThrow('An unknown error occurred')
    })
  })

  // ----------------------------------------------------------
  // URL Construction
  // ----------------------------------------------------------
  describe('URL Construction', () => {
    it('constructs URL from base URL and endpoint', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/api/v1/resources')

      expect(fetchMock).toHaveBeenCalledWith(
        'https://api.test.com/api/v1/resources',
        expect.any(Object)
      )
    })

    it('handles endpoints with query parameters', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({}),
      })

      await service.get('/search?q=test&page=1')

      expect(fetchMock).toHaveBeenCalledWith(
        'https://api.test.com/search?q=test&page=1',
        expect.any(Object)
      )
    })
  })

  // ----------------------------------------------------------
  // File Upload
  // ----------------------------------------------------------
  describe('File Upload', () => {
    it('uploads file using FormData', async () => {
      const file = new File(['test content'], 'test.png', { type: 'image/png' })

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => ({ url: 'https://cdn.test.com/test.png' }),
      })

      await service.uploadFile('/upload', file)

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[0]).toBe('https://api.test.com/upload')
      expect(callArgs[1].method).toBe('POST')
      expect(callArgs[1].body).toBeInstanceOf(FormData)
    })

    it('removes Content-Type header for file uploads (browser sets boundary)', async () => {
      const file = new File(['data'], 'doc.pdf', { type: 'application/pdf' })

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => ({ url: 'https://cdn.test.com/doc.pdf' }),
      })

      await service.uploadFile('/upload', file)

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].headers['Content-Type']).toBeUndefined()
    })

    it('appends additional data fields to FormData', async () => {
      const file = new File(['img'], 'photo.jpg', { type: 'image/jpeg' })
      const additionalData = { category: 'avatar', userId: '42' }

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => ({ url: 'https://cdn.test.com/photo.jpg' }),
      })

      await service.uploadFile('/upload', file, additionalData)

      const callArgs = fetchMock.mock.calls[0]
      const formData = callArgs[1].body as FormData
      expect(formData.get('file')).toBeInstanceOf(File)
      expect(formData.get('category')).toBe('avatar')
      expect(formData.get('userId')).toBe('42')
    })

    it('throws on upload failure with JSON error', async () => {
      const file = new File(['data'], 'big.bin', { type: 'application/octet-stream' })

      fetchMock.mockResolvedValue({
        ok: false,
        status: 413,
        json: async () => ({ message: 'File too large' }),
      })

      await expect(service.uploadFile('/upload', file)).rejects.toThrow('File too large')
    })

    it('throws generic HTTP error when upload fails without JSON', async () => {
      const file = new File(['data'], 'file.txt', { type: 'text/plain' })

      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('not json')
        },
      })

      await expect(service.uploadFile('/upload', file)).rejects.toThrow('HTTP 500')
    })

    it('includes auth token in upload requests', async () => {
      service.setAuthToken('upload-token')
      const file = new File(['data'], 'file.txt', { type: 'text/plain' })

      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => ({ url: 'https://cdn.test.com/file.txt' }),
      })

      await service.uploadFile('/upload', file)

      const callArgs = fetchMock.mock.calls[0]
      expect(callArgs[1].headers['Authorization']).toBe('Bearer upload-token')
    })
  })
})
