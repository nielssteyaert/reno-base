// Light/dark handling. Inside Home Assistant the ingress iframe is same-origin with the HA
// frontend, so we can follow HA's own dark-mode setting; otherwise fall back to the OS.

export type ThemeChoice = 'auto' | 'light' | 'dark'
const STORAGE_KEY = 'reno-theme'

function haDarkMode(): boolean | null {
  try {
    const root = window.parent?.document?.querySelector('home-assistant') as
      | (Element & { hass?: { themes?: { darkMode?: boolean } } })
      | null
    const dark = root?.hass?.themes?.darkMode
    return typeof dark === 'boolean' ? dark : null
  } catch {
    return null
  }
}

export function storedTheme(): ThemeChoice {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (value === 'light' || value === 'dark' || value === 'auto') return value
  } catch {
    // storage unavailable
  }
  return 'auto'
}

export function isDark(choice: ThemeChoice): boolean {
  if (choice !== 'auto') return choice === 'dark'
  return haDarkMode() ?? window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function applyTheme(choice: ThemeChoice) {
  try {
    localStorage.setItem(STORAGE_KEY, choice)
  } catch {
    // storage unavailable
  }
  document.documentElement.classList.toggle('app-dark', isDark(choice))
  window.dispatchEvent(new Event('reno-theme'))
}

export function watchSystemTheme(getChoice: () => ThemeChoice) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => applyTheme(getChoice()))
}
