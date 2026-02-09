/**
 * API Service for Coloring Book Generator
 * Handles all HTTP requests to the backend API
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1'

interface RequestOptions {
  headers?: Record<string, string>
  signal?: AbortSignal
}

interface ApiResponse<T = unknown> {
  data: T
  status: number
  message?: string
}

class ApiService {
  private baseURL: string
  private defaultHeaders: Record<string, string>

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  /**
   * Set authorization token for API requests
   */
  setAuthToken(token: string): void {
    this.defaultHeaders['Authorization'] = `Bearer ${token}`
  }

  /**
   * Clear authorization token
   */
  clearAuthToken(): void {
    delete this.defaultHeaders['Authorization']
  }

  /**
   * Perform a GET request
   */
  async get<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, options)
  }

  /**
   * Perform a POST request
   */
  async post<T = unknown>(endpoint: string, data?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('POST', endpoint, data, options)
  }

  /**
   * Perform a PUT request
   */
  async put<T = unknown>(endpoint: string, data?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('PUT', endpoint, data, options)
  }

  /**
   * Perform a PATCH request
   */
  async patch<T = unknown>(endpoint: string, data?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('PATCH', endpoint, data, options)
  }

  /**
   * Perform a DELETE request
   */
  async delete<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, options)
  }

  /**
   * Core request method
   */
  private async request<T>(
    method: string,
    endpoint: string,
    data?: unknown,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const headers = {
      ...this.defaultHeaders,
      ...options.headers,
    }

    const config: RequestInit = {
      method,
      headers,
      signal: options.signal,
    }

    if (data !== undefined) {
      config.body = JSON.stringify(data)
    }

    try {
      const response = await fetch(url, config)

      // Handle non-JSON responses
      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        return {} as T
      }

      const json = await response.json()

      if (!response.ok) {
        const errorMessage = json.message || json.error || `HTTP ${response.status}`
        throw new Error(errorMessage)
      }

      return json as T
    } catch (error) {
      if (error instanceof Error) {
        // Re-throw with more context
        if (error.name === 'AbortError') {
          throw new Error('Request was cancelled')
        }
        throw error
      }
      throw new Error('An unknown error occurred')
    }
  }

  /**
   * Upload a file
   */
  async uploadFile<T = unknown>(
    endpoint: string,
    file: File,
    additionalData?: Record<string, string>
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const formData = new FormData()
    formData.append('file', file)

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value)
      })
    }

    const headers = { ...this.defaultHeaders }
    // Remove Content-Type to let browser set it with boundary
    delete headers['Content-Type']

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || `HTTP ${response.status}`)
    }

    return response.json()
  }
}

// Export singleton instance
export const apiService = new ApiService()

// Export class for testing or custom instances
export { ApiService }
export type { RequestOptions, ApiResponse }
