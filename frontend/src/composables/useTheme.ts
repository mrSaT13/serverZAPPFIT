import { readonly, ref } from 'vue'

import { getStorageItem, setStorageItem } from '@/lib/storage'

const THEME_STORAGE_KEY = 'theme'
const ACCENT_STORAGE_KEY = 'accentColor'

export type Theme = 'light' | 'dark' | 'system'

/**
 * Predefined accent colour palettes.
 * Each preset defines the full set of CSS custom properties that override the
 * base palette in `main.css` at runtime.
 */
export interface AccentPreset {
  id: string
  label: string
  /** Light-mode values */
  light: {
    brand: string
    brandLight: string
    brandMid: string
    brandDark: string
    primary: string
    primaryFg: string
    secondary: string
    secondaryFg: string
    accent: string
    accentFg: string
    ring: string
  }
  /** Dark-mode values */
  dark: {
    primary: string
    primaryFg: string
    secondary: string
    secondaryFg: string
    accent: string
    accentFg: string
    ring: string
    brandDarkFg: string
    brandDarkSurface: string
  }
}

function h(hex: string, alpha: number): string {
  const n = hex.replace('#', '')
  const r = Number.parseInt(n.slice(0, 2), 16)
  const g = Number.parseInt(n.slice(2, 4), 16)
  const b = Number.parseInt(n.slice(4, 6), 16)
  return `${r} ${g} ${b}`
}

function derivePreset(id: string, label: string, base: string, darkPrimary: string, darkSurface: string): AccentPreset {
  return {
    id,
    label,
    light: {
      brand: base,
      brandLight: `color-mix(in srgb, ${base} 15%, white)`,
      brandMid: `color-mix(in srgb, ${base} 80%, black)`,
      brandDark: `color-mix(in srgb, ${base} 60%, black)`,
      primary: base,
      primaryFg: '#ffffff',
      secondary: `color-mix(in srgb, ${base} 15%, white)`,
      secondaryFg: `color-mix(in srgb, ${base} 80%, black)`,
      accent: `color-mix(in srgb, ${base} 15%, white)`,
      accentFg: `color-mix(in srgb, ${base} 80%, black)`,
      ring: base,
    },
    dark: {
      primary: darkPrimary,
      primaryFg: darkSurface,
      secondary: darkSurface,
      secondaryFg: darkPrimary,
      accent: darkSurface,
      accentFg: darkPrimary,
      ring: darkPrimary,
      brandDarkFg: darkPrimary,
      brandDarkSurface: darkSurface,
    },
  }
}

/** Built-in accent colour presets. */
export const ACCENT_PRESETS: AccentPreset[] = [
  derivePreset('blue', 'Blue', '#2563eb', '#60a5fa', '#172554'),
  derivePreset('green', 'Green', '#16a34a', '#4ade80', '#052e16'),
  derivePreset('purple', 'Purple', '#7c3aed', '#a78bfa', '#2e1065'),
  derivePreset('orange', 'Orange', '#ea580c', '#fb923c', '#431407'),
  derivePreset('red', 'Red', '#dc2626', '#f87171', '#450a0a'),
  derivePreset('teal', 'Teal', '#0d9488', '#2dd4bf', '#042f2e'),
  derivePreset('pink', 'Pink', '#db2777', '#f472b6', '#500724'),
  derivePreset('indigo', 'Indigo', '#4f46e5', '#818cf8', '#1e1b4b'),
  derivePreset('amber', 'Amber', '#d97706', '#fbbf24', '#451a03'),
]

/**
 * Applies a full accent preset to `<html>` element as inline CSS variables.
 */
function applyAccent(preset: AccentPreset, effectiveTheme: 'light' | 'dark'): void {
  const vars = effectiveTheme === 'dark' ? preset.dark : preset.light
  const el = document.documentElement

  el.style.setProperty('--brand', vars.brand)
  el.style.setProperty('--primary', vars.primary)
  el.style.setProperty('--primary-foreground', vars.primaryFg)
  el.style.setProperty('--secondary', vars.secondary)
  el.style.setProperty('--secondary-foreground', vars.secondaryFg)
  el.style.setProperty('--accent', vars.accent)
  el.style.setProperty('--accent-foreground', vars.accentFg)
  el.style.setProperty('--ring', vars.ring)

  // @theme block tokens (used by bg-brand / text-brand classes)
  el.style.setProperty('--color-brand', vars.brand)
  el.style.setProperty('--color-brand-light', vars.brandLight)
  el.style.setProperty('--color-brand-mid', vars.brandMid)
  el.style.setProperty('--color-brand-dark', vars.brandDark)

  if (effectiveTheme === 'dark') {
    el.style.setProperty('--color-brand-dark-foreground', vars.brandDarkFg)
    el.style.setProperty('--color-brand-dark-surface', vars.brandDarkSurface)
  }
}

/**
 * Clears all runtime accent overrides so the CSS default (from `main.css`) applies.
 */
function clearAccentOverrides(): void {
  const el = document.documentElement
  for (const prop of [
    '--brand', '--primary', '--primary-foreground',
    '--secondary', '--secondary-foreground',
    '--accent', '--accent-foreground', '--ring',
    '--color-brand', '--color-brand-light', '--color-brand-mid', '--color-brand-dark',
    '--color-brand-dark-foreground', '--color-brand-dark-surface',
  ]) {
    el.style.removeProperty(prop)
  }
}

const theme = ref<Theme>('system')
const accentId = ref<string>('blue')
let initialized = false

/** Resolves a theme preference (including ``system``) to an effective value. */
function resolveEffective(value: Theme): 'light' | 'dark' {
  if (value === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return value
}

/**
 * Applies the given theme preference to the document root and re-applies
 * the current accent colour preset for the new effective theme.
 */
function applyTheme(value: Theme): void {
  theme.value = value
  const effective = resolveEffective(value)
  document.documentElement.classList.toggle('dark', effective === 'dark')

  const preset = ACCENT_PRESETS.find((p) => p.id === accentId.value)
  if (preset) {
    applyAccent(preset, effective)
  }
}

/**
 * Resolves and applies the initial theme + accent synchronously. Call once,
 * as early as possible during bootstrap, so the correct theme is set before
 * first paint (no flash of the wrong color scheme).
 */
export function initTheme(): void {
  if (initialized) {
    return
  }
  initialized = true

  const storedTheme = getStorageItem<Theme>(THEME_STORAGE_KEY)
  const storedAccent = getStorageItem<string>(ACCENT_STORAGE_KEY)
  const media = window.matchMedia('(prefers-color-scheme: dark)')

  if (storedAccent) {
    accentId.value = storedAccent
  }

  applyTheme(storedTheme ?? 'system')

  // Follow OS changes when the user preference is `system` (the default).
  media.addEventListener('change', (event) => {
    if (theme.value === 'system') {
      document.documentElement.classList.toggle('dark', event.matches)
      const preset = ACCENT_PRESETS.find((p) => p.id === accentId.value)
      if (preset) {
        applyAccent(preset, event.matches ? 'dark' : 'light')
      }
    }
  })
}

/**
 * Theme controller backed by the `dark` class on `<html>`, supporting
 * ``light``, ``dark`` and ``system`` preferences, plus accent colour.
 *
 * @returns Read-only reactive state and setters.
 */
export function useTheme() {
  function setTheme(value: Theme): void {
    applyTheme(value)
    setStorageItem(THEME_STORAGE_KEY, value)
  }

  function toggle(): void {
    setTheme(resolveEffective(theme.value) === 'dark' ? 'light' : 'dark')
  }

  function setAccentColor(presetId: string): void {
    const preset = ACCENT_PRESETS.find((p) => p.id === presetId)
    if (!preset) return
    accentId.value = presetId
    setStorageItem(ACCENT_STORAGE_KEY, presetId)
    applyAccent(preset, resolveEffective(theme.value))
  }

  return {
    theme: readonly(theme),
    accentId: readonly(accentId),
    toggle,
    setTheme,
    setAccentColor,
    accentPresets: ACCENT_PRESETS,
  }
}
