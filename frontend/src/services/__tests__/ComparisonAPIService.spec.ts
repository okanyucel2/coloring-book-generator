import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { ComparisonAPIService } from '../ComparisonAPIService'

describe('ComparisonAPIService - RED PHASE', () => {
  let service: ComparisonAPIService
  let fetchMock: any

  beforeEach(() => {
    service = new ComparisonAPIService()
    fetchMock = vi.fn()
    global.fetch = fetchMock
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Service Initialization', () => {
    it('initializes with default API base URL', () => {
      expect(service).toBeInstanceOf(ComparisonAPIService)
      expect(service.baseURL).toBeDefined()
    })

    it('sets up abort controller for request cancellation', () => {
      expect(service.abortController).toBeInstanceOf(AbortController)
    })

    it('initializes cache object', () => {
      expect(service.cache).toBeDefined()
      expect(typeof service.cache).toBe('object')
    })

    it('initializes request queue', () => {
      expect(service.requestQueue).toBeDefined()
      expect(Array.isArray(service.requestQueue)).toBe(true)
    })
  })

  describe('Concurrent API Calls', () => {
    it('calls all three models simultaneously', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const prompt = 'A dog outline'
      const seed = 12345

      const startTime = Date.now()
      await service.compareModels(prompt, seed)
      const duration = Date.now() - startTime

      // Should call fetch 3 times (one per model)
      expect(fetchMock).toHaveBeenCalledTimes(3)

      // All calls should happen concurrently (total time < sum of individual times)
      // If sequential, would be ~300ms; concurrent should be ~100ms
      expect(duration).toBeLessThan(500)
    })

    it('makes requests with correct model names', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.9, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      await service.compareModels('cat drawing', 999)

      const calls = fetchMock.mock.calls
      const urlsUsed = calls.map((call: any[]) => call[0])

      expect(urlsUsed.some((url: string) => url.includes('gemini'))).toBe(true)
      expect(urlsUsed.some((url: string) => url.includes('imagen'))).toBe(true)
      expect(urlsUsed.some((url: string) => url.includes('ultra'))).toBe(true)
    })

    it('includes prompt and seed in all requests', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.85, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const prompt = 'Tiger in jungle'
      const seed = 54321

      await service.compareModels(prompt, seed)

      const calls = fetchMock.mock.calls
      calls.forEach((call: any[]) => {
        const url = call[0]
        // URLSearchParams encodes spaces as '+', not '%20'
        expect(url).toContain('Tiger+in+jungle')
        expect(url).toContain(`seed=${seed}`)
      })
    })
  })

  describe('Response Parsing', () => {
    it('returns results from all three models', async () => {
      const mockGemini = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/gemini.png', quality: 0.95, time: 2.1 }),
      }
      const mockImagen = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/imagen.png', quality: 0.90, time: 2.5 }),
      }
      const mockUltra = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/ultra.png', quality: 0.93, time: 3.2 }),
      }

      fetchMock
        .mockResolvedValueOnce(mockGemini)
        .mockResolvedValueOnce(mockImagen)
        .mockResolvedValueOnce(mockUltra)

      const result = await service.compareModels('elephant', 111)

      expect(result).toHaveProperty('gemini')
      expect(result).toHaveProperty('imagen')
      expect(result).toHaveProperty('ultra')

      expect(result.gemini.imageUrl).toBe('https://example.com/gemini.png')
      expect(result.imagen.quality).toBe(0.90)
      expect(result.ultra.time).toBe(3.2)
    })

    it('includes generation metadata in results', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({
          imageUrl: 'https://example.com/image.png',
          quality: 0.88,
          time: 2.3,
          modelVersion: 'gemini-2.0',
          tokens: 150,
        }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const result = await service.compareModels('bird', 222)

      expect(result.gemini.time).toBeGreaterThan(0)
      expect(result.gemini.modelVersion).toBeDefined()
    })

    it('handles image URLs correctly', async () => {
      const imageUrl = 'https://api.example.com/images/abc123.png'
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl, quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const result = await service.compareModels('snake', 333)

      expect(result.gemini.imageUrl).toBe(imageUrl)
      expect(result.gemini.imageUrl).toMatch(/^https:\/\//)
    })
  })

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      fetchMock.mockRejectedValue(new Error('Network timeout'))

      await expect(service.compareModels('horse', 444)).rejects.toThrow()
    })

    it('handles HTTP error responses', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      }
      fetchMock.mockResolvedValue(mockResponse)

      await expect(service.compareModels('zebra', 555)).rejects.toThrow()
    })

    it('handles partial failures (one model fails)', async () => {
      const mockSuccess = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.90, time: 2.0 }),
      }
      const mockError = {
        ok: false,
        status: 503,
      }

      fetchMock
        .mockResolvedValueOnce(mockSuccess)
        .mockResolvedValueOnce(mockError)
        .mockResolvedValueOnce(mockSuccess)

      await expect(service.compareModels('lion', 666)).rejects.toThrow()
    })

    it('provides meaningful error messages', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: async () => ({ error: 'Invalid prompt' }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      try {
        await service.compareModels('', 777)
      } catch (err: any) {
        expect(err.message).toBeTruthy()
      }
    })
  })

  describe('Caching System', () => {
    it('caches results by prompt+seed combination', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const prompt = 'Cached dog'
      const seed = 888

      // First call - should fetch
      await service.compareModels(prompt, seed)
      const firstCallCount = fetchMock.mock.calls.length

      // Second call - should use cache
      await service.compareModels(prompt, seed)
      const secondCallCount = fetchMock.mock.calls.length

      // No additional calls should be made
      expect(secondCallCount).toBe(firstCallCount)
    })

    it('cache key includes prompt and seed', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      // Different seeds = different cache entries
      await service.compareModels('dog', 111)
      const afterFirst = fetchMock.mock.calls.length

      await service.compareModels('dog', 222)
      const afterSecond = fetchMock.mock.calls.length

      // Second call should NOT use cache (different seed)
      expect(afterSecond).toBeGreaterThan(afterFirst)
    })

    it('clears cache on demand', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const prompt = 'Cache test'
      const seed = 999

      // Cache the result
      await service.compareModels(prompt, seed)
      const beforeClear = fetchMock.mock.calls.length

      // Clear cache
      service.clearCache()

      // Fetch again - should make new requests
      await service.compareModels(prompt, seed)
      const afterClear = fetchMock.mock.calls.length

      expect(afterClear).toBeGreaterThan(beforeClear)
    })

    it('respects cache TTL (time to live)', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const prompt = 'TTL test'
      const seed = 1111

      // Cache with short TTL
      service.cacheTTL = 100 // 100ms

      await service.compareModels(prompt, seed)
      const initialCount = fetchMock.mock.calls.length

      // Wait for cache to expire
      await new Promise((resolve) => setTimeout(resolve, 150))

      // Fetch again - should make new requests (cache expired)
      await service.compareModels(prompt, seed)
      const finalCount = fetchMock.mock.calls.length

      expect(finalCount).toBeGreaterThan(initialCount)
    })
  })

  describe('Request Management', () => {
    it('cancels pending requests on demand', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const oldController = service.abortController
      service.cancelRequests()

      // After cancel, should have a new controller
      expect(service.abortController).not.toBe(oldController)
      // Old controller should be aborted
      expect(oldController.signal.aborted).toBe(true)
    })

    it('maintains request queue', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const initialQueueLength = service.requestQueue.length

      const promise = service.compareModels('queued request', 3333)

      expect(service.requestQueue.length).toBeGreaterThanOrEqual(initialQueueLength)
    })
  })

  describe('Quality Metrics', () => {
    it('includes quality scores in results', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.87, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const result = await service.compareModels('quality test', 5555)

      expect(result.gemini.quality).toBe(0.87)
      expect(result.imagen.quality).toBe(0.87)
      expect(result.ultra.quality).toBe(0.87)
    })

    it('calculates quality differences between models', async () => {
      const mockGemini = {
        ok: true,
        json: async () => ({ imageUrl: 'url1', quality: 0.95, time: 2.0 }),
      }
      const mockImagen = {
        ok: true,
        json: async () => ({ imageUrl: 'url2', quality: 0.85, time: 2.0 }),
      }
      const mockUltra = {
        ok: true,
        json: async () => ({ imageUrl: 'url3', quality: 0.90, time: 2.0 }),
      }

      fetchMock
        .mockResolvedValueOnce(mockGemini)
        .mockResolvedValueOnce(mockImagen)
        .mockResolvedValueOnce(mockUltra)

      const result = await service.compareModels('comparison', 6666)

      const qualityDiff = result.gemini.quality - result.imagen.quality
      expect(qualityDiff).toBeCloseTo(0.1, 5)
    })

    it('identifies best performing model', async () => {
      const mockGemini = {
        ok: true,
        json: async () => ({ imageUrl: 'url1', quality: 0.88, time: 2.0 }),
      }
      const mockImagen = {
        ok: true,
        json: async () => ({ imageUrl: 'url2', quality: 0.92, time: 2.0 }),
      }
      const mockUltra = {
        ok: true,
        json: async () => ({ imageUrl: 'url3', quality: 0.90, time: 2.0 }),
      }

      fetchMock
        .mockResolvedValueOnce(mockGemini)
        .mockResolvedValueOnce(mockImagen)
        .mockResolvedValueOnce(mockUltra)

      const result = await service.compareModels('best model', 7777)
      const best = service.getBestModel(result)

      expect(best).toBe('imagen')
    })
  })

  describe('Real-time Progress Tracking', () => {
    it('tracks progress of ongoing requests', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const progressUpdates: any[] = []
      service.onProgress = (progress) => {
        progressUpdates.push(progress)
      }

      await service.compareModels('progress test', 8888)

      expect(progressUpdates.length).toBeGreaterThan(0)
    })

    it('provides progress percentage', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const progressUpdates: any[] = []
      service.onProgress = (progress) => {
        progressUpdates.push(progress)
      }

      await service.compareModels('percentage test', 9999)

      const finalProgress = progressUpdates[progressUpdates.length - 1]
      expect(finalProgress.percentage).toBeLessThanOrEqual(100)
      expect(finalProgress.percentage).toBeGreaterThanOrEqual(0)
    })

    it('indicates completed models in progress', async () => {
      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      const progressUpdates: any[] = []
      service.onProgress = (progress) => {
        progressUpdates.push(progress)
      }

      await service.compareModels('completed models', 10000)

      const finalProgress = progressUpdates[progressUpdates.length - 1]
      expect(finalProgress.completed).toContain('gemini')
      expect(finalProgress.completed).toContain('imagen')
      expect(finalProgress.completed).toContain('ultra')
    })
  })

  describe('API Configuration', () => {
    it('accepts custom API base URL', () => {
      const customURL = 'https://custom-api.example.com'
      service.setBaseURL(customURL)

      expect(service.baseURL).toBe(customURL)
    })

    it('includes authentication headers if provided', async () => {
      const token = 'test-token-123'
      service.setAuthToken(token)

      const mockResponse = {
        ok: true,
        json: async () => ({ imageUrl: 'https://example.com/image.png', quality: 0.92, time: 2.0 }),
      }
      fetchMock.mockResolvedValue(mockResponse)

      await service.compareModels('auth test', 11111)

      const calls = fetchMock.mock.calls
      calls.forEach((call: any[]) => {
        const options = call[1]
        expect(options.headers?.Authorization).toBe(`Bearer ${token}`)
      })
    })

    it('allows custom timeout configuration', () => {
      const customTimeout = 5000
      service.setTimeout(customTimeout)

      expect(service.timeout).toBe(customTimeout)
    })
  })
})
