import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'

// useTheme composable will export:
// - theme: Ref<'dark' | 'light'>
// - isDark: ComputedRef<boolean>
// - toggleTheme: () => void
// - setTheme: (theme: 'dark' | 'light') => void

describe('useTheme composable', () => {
  let useTheme: any

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    // Reset document attribute
    document.documentElement.removeAttribute('data-theme')
    // Reset module cache so each test gets fresh state
    vi.resetModules()
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  async function loadUseTheme() {
    const mod = await import('../../composables/useTheme')
    return mod.useTheme
  }

  describe('Initial State', () => {
    it('defaults to dark theme when no preference is stored', async () => {
      useTheme = await loadUseTheme()
      const { theme, isDark } = useTheme()

      expect(theme.value).toBe('dark')
      expect(isDark.value).toBe(true)
    })

    it('reads stored theme from localStorage', async () => {
      localStorage.setItem('theme', 'light')
      useTheme = await loadUseTheme()
      const { theme, isDark } = useTheme()

      expect(theme.value).toBe('light')
      expect(isDark.value).toBe(false)
    })

    it('applies data-theme attribute on initialization', async () => {
      localStorage.setItem('theme', 'light')
      useTheme = await loadUseTheme()
      useTheme()

      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    })

    it('does not set data-theme attribute for dark (default)', async () => {
      useTheme = await loadUseTheme()
      useTheme()

      // Dark is default — no data-theme attribute needed (uses :root defaults)
      const attr = document.documentElement.getAttribute('data-theme')
      expect(attr === null || attr === 'dark').toBe(true)
    })
  })

  describe('toggleTheme', () => {
    it('switches from dark to light', async () => {
      useTheme = await loadUseTheme()
      const { theme, toggleTheme } = useTheme()

      expect(theme.value).toBe('dark')
      toggleTheme()
      expect(theme.value).toBe('light')
    })

    it('switches from light to dark', async () => {
      localStorage.setItem('theme', 'light')
      useTheme = await loadUseTheme()
      const { theme, toggleTheme } = useTheme()

      expect(theme.value).toBe('light')
      toggleTheme()
      expect(theme.value).toBe('dark')
    })

    it('persists theme to localStorage on toggle', async () => {
      useTheme = await loadUseTheme()
      const { toggleTheme } = useTheme()

      toggleTheme()
      expect(localStorage.getItem('theme')).toBe('light')

      toggleTheme()
      expect(localStorage.getItem('theme')).toBe('dark')
    })

    it('updates data-theme attribute on toggle', async () => {
      useTheme = await loadUseTheme()
      const { toggleTheme } = useTheme()

      toggleTheme()
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')

      toggleTheme()
      // Back to dark — either no attribute or 'dark'
      const attr = document.documentElement.getAttribute('data-theme')
      expect(attr === null || attr === 'dark').toBe(true)
    })
  })

  describe('setTheme', () => {
    it('sets theme to light', async () => {
      useTheme = await loadUseTheme()
      const { theme, setTheme } = useTheme()

      setTheme('light')
      expect(theme.value).toBe('light')
      expect(localStorage.getItem('theme')).toBe('light')
    })

    it('sets theme to dark', async () => {
      localStorage.setItem('theme', 'light')
      useTheme = await loadUseTheme()
      const { theme, setTheme } = useTheme()

      setTheme('dark')
      expect(theme.value).toBe('dark')
      expect(localStorage.getItem('theme')).toBe('dark')
    })

    it('ignores invalid theme values', async () => {
      useTheme = await loadUseTheme()
      const { theme, setTheme } = useTheme()

      setTheme('invalid' as any)
      expect(theme.value).toBe('dark')
    })
  })

  describe('Shared State', () => {
    it('returns same reactive state across multiple calls', async () => {
      useTheme = await loadUseTheme()
      const first = useTheme()
      const second = useTheme()

      first.toggleTheme()
      expect(second.theme.value).toBe('light')
    })
  })
})
