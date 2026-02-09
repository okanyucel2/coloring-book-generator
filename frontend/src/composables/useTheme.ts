import { ref, computed } from 'vue'

export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'theme'

// Module-level shared state — same ref across all useTheme() calls
const theme = ref<Theme>(getInitialTheme())

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // localStorage unavailable (SSR, private browsing)
  }
  return 'dark'
}

function applyTheme(t: Theme) {
  if (t === 'light') {
    document.documentElement.setAttribute('data-theme', 'light')
  } else {
    document.documentElement.removeAttribute('data-theme')
  }
}

// Apply on module load
applyTheme(theme.value)

export function useTheme() {
  const isDark = computed(() => theme.value === 'dark')

  function setTheme(t: Theme) {
    if (t !== 'dark' && t !== 'light') return
    theme.value = t
    applyTheme(t)
    try {
      localStorage.setItem(STORAGE_KEY, t)
    } catch {
      // localStorage unavailable
    }
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  return { theme, isDark, toggleTheme, setTheme }
}
