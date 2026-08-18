import { PROVIDER_CUSTOM_LOGO_MAP } from '@/constants/ssoLogos'

/** Provider icon keys that ship with a bundled logo asset. */
export const BUILTIN_PROVIDER_ICONS = [
  'authelia',
  'authentik',
  'casdoor',
  'keycloak',
  'pocketid',
] as const

export type BuiltinProviderIcon = (typeof BUILTIN_PROVIDER_ICONS)[number]

/** The sentinel icon option meaning "supply a custom icon URL". */
export const CUSTOM_ICON = 'custom'

/**
 * Narrows an icon value to one of the built-in keys.
 *
 * @param icon - The provider's stored icon value.
 * @returns Whether the icon is a known built-in key.
 */
export function isBuiltinProviderIcon(
  icon: string | null | undefined,
): icon is BuiltinProviderIcon {
  return Boolean(icon) && (BUILTIN_PROVIDER_ICONS as readonly string[]).includes(icon as string)
}

/**
 * Resolves a displayable logo source for a provider icon: the bundled asset for
 * a built-in key, the raw URL for a custom icon, or `null` when none is set.
 *
 * @param icon - The provider's stored icon value (key or URL).
 * @returns A logo `src`, or `null` to fall back to a generic icon.
 */
export function resolveProviderLogo(icon: string | null | undefined): string | null {
  if (!icon) {
    return null
  }
  if (isBuiltinProviderIcon(icon)) {
    return PROVIDER_CUSTOM_LOGO_MAP[icon] ?? null
  }
  return icon
}
