import { readonly, ref } from 'vue'

import { getStorageItem, setStorageItem } from '@/lib/storage'

const STORAGE_KEY = 'theme'

export type Theme = 'light' | 'dark' | 'system'

const theme = ref<Theme>('system')
let initialized = false

/** Resolves a theme preference (including ``system``) to an effective value. */
function resolveEffective(value: Theme): 'light' | 'dark' {
  if (value === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return value
}

/**
 * Applies the given theme preference to the document root.
 *
 * ``system`` is resolved against the OS before toggling the `dark` class.
 *
 * @param value - The theme preference to apply.
 */
function applyTheme(value: Theme): void {
  theme.value = value
  document.documentElement.classList.toggle('dark', resolveEffective(value) === 'dark')
}

/**
 * Resolves and applies the initial theme synchronously. Call once, as early
 * as possible during bootstrap, so the correct theme is set before first
 * paint (no flash of the wrong color scheme).
 */
export function initTheme(): void {
  if (initialized) {
    return
  }
  initialized = true

  const stored = getStorageItem<Theme>(STORAGE_KEY)
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  applyTheme(stored ?? 'system')

  // Follow OS changes when the user preference is `system` (the default).
  media.addEventListener('change', (event) => {
    if (theme.value === 'system') {
      document.documentElement.classList.toggle('dark', event.matches)
    }
  })
}

/**
 * Theme controller backed by the `dark` class on `<html>`, supporting
 * ``light``, ``dark`` and ``system`` preferences.
 *
 * @returns The read-only reactive `theme` plus `toggle` and `setTheme`.
 */
export function useTheme() {
  /**
   * Sets and persists an explicit theme preference.
   *
   * @param value - The theme preference to activate.
   */
  function setTheme(value: Theme): void {
    applyTheme(value)
    setStorageItem(STORAGE_KEY, value)
  }

  /**
   * Toggles between light and dark themes, persisting the choice.
   *
   * A ``system`` preference is first resolved to its effective value, then
   * toggled — so toggling from "system (dark)" yields "light".
   */
  function toggle(): void {
    setTheme(resolveEffective(theme.value) === 'dark' ? 'light' : 'dark')
  }

  return { theme: readonly(theme), toggle, setTheme }
}