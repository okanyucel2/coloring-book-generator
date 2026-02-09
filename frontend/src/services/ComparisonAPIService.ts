export interface ModelResult {
  imageUrl: string
  quality: number
  time: number
  modelVersion?: string
  tokens?: number
}

export interface ComparisonResults {
  gemini: ModelResult
  imagen: ModelResult
  ultra: ModelResult
  timestamp: number
}

export interface ProgressUpdate {
  percentage: number
  completed: string[]
  pending: string[]
}

export class ComparisonAPIService {
  baseURL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1'
  abortController: AbortController
  cache: Map<string, { data: ComparisonResults; timestamp: number }> = new Map()
  requestQueue: Promise<any>[] = []
  cacheTTL: number = 24 * 60 * 60 * 1000 // 24 hours
  timeout: number = 30000 // 30 seconds
  authToken: string | null = null
  onProgress: ((progress: ProgressUpdate) => void) | null = null

  constructor() {
    this.abortController = new AbortController()
  }

  /**
   * Compare outputs from all three models concurrently
   */
  async compareModels(prompt: string, seed: number): Promise<ComparisonResults> {
    // Check cache first
    const cacheKey = this.getCacheKey(prompt, seed)
    const cached = this.getFromCache(cacheKey)
    if (cached) {
      this.emitProgress(['gemini', 'imagen', 'ultra'], [])
      return cached
    }

    // Emit initial progress
    this.emitProgress([], ['gemini', 'imagen', 'ultra'])

    try {
      // Make concurrent requests to all three models
      const [geminiResult, imagenResult, ultraResult] = await Promise.all([
        this.callModel('gemini', prompt, seed),
        this.callModel('imagen', prompt, seed),
        this.callModel('ultra', prompt, seed),
      ])

      // Emit progress after all complete
      this.emitProgress(['gemini', 'imagen', 'ultra'], [])

      // Combine results
      const result: ComparisonResults = {
        gemini: geminiResult,
        imagen: imagenResult,
        ultra: ultraResult,
        timestamp: Date.now(),
      }

      // Cache the result
      this.cache.set(cacheKey, {
        data: result,
        timestamp: Date.now(),
      })

      return result
    } catch (error) {
      console.error('Error comparing models:', error)
      throw error
    }
  }

  /**
   * Call a single model API
   */
  private async callModel(model: string, prompt: string, seed: number): Promise<ModelResult> {
    const url = this.buildURL(model, prompt, seed)

    const fetchPromise = fetch(url, {
      signal: this.abortController.signal,
      headers: this.buildHeaders(),
    })

    try {
      const response = await fetchPromise

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()

      return {
        imageUrl: data.imageUrl,
        quality: data.quality,
        time: data.time || 0,
        modelVersion: data.modelVersion,
        tokens: data.tokens,
      }
    } catch (error) {
      throw new Error(`Failed to fetch from ${model}: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  /**
   * Build API URL for a specific model
   */
  private buildURL(model: string, prompt: string, seed: number): string {
    const params = new URLSearchParams({
      prompt: prompt,
      seed: seed.toString(),
    })
    return `${this.baseURL}/compare/${model}?${params.toString()}`
  }

  /**
   * Build request headers
   */
  private buildHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`
    }

    return headers
  }

  /**
   * Generate cache key from prompt and seed
   */
  private getCacheKey(prompt: string, seed: number): string {
    return `${prompt}::${seed}`
  }

  /**
   * Get result from cache if not expired
   */
  private getFromCache(key: string): ComparisonResults | null {
    const cached = this.cache.get(key)
    if (!cached) return null

    // Check TTL
    if (Date.now() - cached.timestamp > this.cacheTTL) {
      this.cache.delete(key)
      return null
    }

    return cached.data
  }

  /**
   * Clear entire cache
   */
  clearCache(): void {
    this.cache.clear()
  }

  /**
   * Cancel all pending requests
   */
  cancelRequests(): void {
    this.abortController.abort()
    this.abortController = new AbortController()
  }

  /**
   * Identify best performing model by quality score
   */
  getBestModel(results: ComparisonResults): string {
    const scores = {
      gemini: results.gemini.quality,
      imagen: results.imagen.quality,
      ultra: results.ultra.quality,
    }

    let bestModel = 'gemini'
    let bestScore = scores.gemini

    for (const [model, score] of Object.entries(scores)) {
      if (score > bestScore) {
        bestModel = model
        bestScore = score
      }
    }

    return bestModel
  }

  /**
   * Set custom API base URL
   */
  setBaseURL(url: string): void {
    this.baseURL = url
  }

  /**
   * Set authentication token
   */
  setAuthToken(token: string): void {
    this.authToken = token
  }

  /**
   * Set request timeout
   */
  setTimeout(ms: number): void {
    this.timeout = ms
  }

  /**
   * Emit progress updates
   */
  private emitProgress(completed: string[], pending: string[]): void {
    if (!this.onProgress) return

    const total = 3
    const completedCount = completed.length
    const percentage = Math.round((completedCount / total) * 100)

    this.onProgress({
      percentage,
      completed,
      pending,
    })
  }
}
