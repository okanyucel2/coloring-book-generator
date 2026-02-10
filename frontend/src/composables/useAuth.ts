import { ref, computed } from 'vue'
import { apiService } from '@/services/api'

export interface User {
  id: string
  email: string
  name: string
  picture?: string
}

const STORAGE_KEYS = {
  accessToken: 'cb_access_token',
  refreshToken: 'cb_refresh_token',
  user: 'cb_user',
} as const

// Module-level shared state — same ref across all useAuth() calls
const user = ref<User | null>(null)
const accessToken = ref<string | null>(null)
const refreshToken = ref<string | null>(null)
const isAuthenticated = computed(() => !!accessToken.value)

export function useAuth() {
  function initAuth() {
    try {
      const savedToken = localStorage.getItem(STORAGE_KEYS.accessToken)
      const savedRefresh = localStorage.getItem(STORAGE_KEYS.refreshToken)
      const savedUser = localStorage.getItem(STORAGE_KEYS.user)

      if (savedToken) {
        accessToken.value = savedToken
        apiService.setAuthToken(savedToken)
      }
      if (savedRefresh) {
        refreshToken.value = savedRefresh
      }
      if (savedUser) {
        try {
          user.value = JSON.parse(savedUser)
        } catch {
          localStorage.removeItem(STORAGE_KEYS.user)
        }
      }
    } catch {
      // localStorage unavailable
    }
  }

  function handleOAuthCallback(): boolean {
    const hash = window.location.hash
    if (!hash.includes('oauth-callback')) return false

    const paramString = hash.substring(hash.indexOf('oauth-callback') + 'oauth-callback'.length)
    const params = new URLSearchParams(paramString.replace(/^&/, ''))

    const token = params.get('access_token')
    const refresh = params.get('refresh_token')
    const userJson = params.get('user')

    if (token) {
      accessToken.value = token
      apiService.setAuthToken(token)
      try { localStorage.setItem(STORAGE_KEYS.accessToken, token) } catch {}
    }

    if (refresh) {
      refreshToken.value = refresh
      try { localStorage.setItem(STORAGE_KEYS.refreshToken, refresh) } catch {}
    }

    if (userJson) {
      try {
        user.value = JSON.parse(userJson)
        localStorage.setItem(STORAGE_KEYS.user, userJson)
      } catch {
        // Invalid user JSON
      }
    }

    // Clean hash from URL
    window.history.replaceState(null, '', window.location.pathname + window.location.search)
    return true
  }

  function loginWithGoogle() {
    window.location.href = '/auth/login/google'
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    apiService.clearAuthToken()
    try {
      localStorage.removeItem(STORAGE_KEYS.accessToken)
      localStorage.removeItem(STORAGE_KEYS.refreshToken)
      localStorage.removeItem(STORAGE_KEYS.user)
    } catch {}
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) return false

    try {
      const response = await fetch('/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken.value }),
      })

      if (!response.ok) throw new Error('Refresh failed')

      const result = await response.json()
      accessToken.value = result.access_token
      apiService.setAuthToken(result.access_token)
      try { localStorage.setItem(STORAGE_KEYS.accessToken, result.access_token) } catch {}
      return true
    } catch {
      logout()
      return false
    }
  }

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    initAuth,
    handleOAuthCallback,
    loginWithGoogle,
    logout,
    refreshAccessToken,
  }
}
