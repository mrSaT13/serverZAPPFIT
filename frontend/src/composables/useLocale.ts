import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { SUPPORTED_LOCALES, loadLocaleMessages, setI18nLocale, type LocaleCode } from '@/i18n'
import { useAppConfig } from '@/features/config/composables/useAppConfig'

/**
 * Locale controller exposing the active locale, the translator, and a
 * lazy-loading setter that persists the user's choice. The exposed locale
 * list honours the instance's `enabledLocales` runtime config, so a hosted
 * deployment can restrict which languages it offers from one bundle.
 *
 * @returns The reactive `locale`, the `t` translator, the `availableLocales`
 *   list, and an async `setLocale` action.
 */
export function useLocale() {
  const { t, locale } = useI18n()
  const { config } = useAppConfig()

  const availableLocales = computed(() => {
    const enabled = config.value.enabledLocales
    const allowed =
      !enabled || enabled.length === 0
        ? SUPPORTED_LOCALES
        : SUPPORTED_LOCALES.filter((entry) => new Set<LocaleCode>(enabled).has(entry.code))
    // Never hide every option: fall back to all locales on a misconfiguration.
    const locales = allowed.length > 0 ? allowed : SUPPORTED_LOCALES
    // Display locales alphabetically by their native label.
    return [...locales].sort((a, b) => a.label.localeCompare(b.label))
  })

  /**
   * Switches the active locale, lazy-loading its messages first.
   *
   * @param next - The locale to activate.
   */
  async function setLocale(next: LocaleCode): Promise<void> {
    await loadLocaleMessages(next)
    setI18nLocale(next)
  }

  return { t, locale, availableLocales, setLocale }
}
