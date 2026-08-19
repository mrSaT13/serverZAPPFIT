<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQueryClient } from '@tanstack/vue-query'
import { LoaderCircle } from '@lucide/vue'

import type {
  Currency,
  ServerSettings,
  ThemePreference,
  Units,
} from '@/features/serverSettings/types'

import AppLogo from '@/components/AppLogo.vue'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { FormField } from '@/components/ui/form-field'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useSafeRedirect } from '@/composables/useSafeRedirect'
import { useTheme } from '@/composables/useTheme'
import { getInitialLocale, isSupportedLocale, loadLocaleMessages, setI18nLocale } from '@/i18n'
import { queryKeys } from '@/services/queryKeys'
import {
  useCompleteSetupMutation,
  useServerSettingsQuery,
  useSetupOptionsQuery,
} from '@/features/serverSettings/composables/useServerSettings'

const { t } = useI18n()
const { setTheme } = useTheme()
const { navigateAfterLogin } = useSafeRedirect()
const queryClient = useQueryClient()

const optionsQuery = useSetupOptionsQuery()
const settingsQuery = useServerSettingsQuery()
const completeMutation = useCompleteSetupMutation()

const language = ref<string>('')
const theme = ref<ThemePreference>('system')
const brandName = ref('')
const units = ref<Units>('metric')
const currency = ref<Currency>('euro')
const recordsPerPage = ref(25)
const signupEnabled = ref(false)
const submitError = ref(false)

const RECORDS_PER_PAGE_OPTIONS = [5, 10, 25, 50, 100] as const

/** Language choices from the backend, narrowed to locales the app supports. */
const languageOptions = computed(() =>
  (optionsQuery.data.value?.languages ?? []).filter((item) => isSupportedLocale(item.code)),
)

/** Brand shown in the hero; prefers the public option, falls back to settings. */
const brandNameDisplay = computed(
  () => optionsQuery.data.value?.brandName ?? settingsQuery.data.value?.brandName ?? 'ZAPFIT',
)

const isLoading = computed(
  () =>
    optionsQuery.isPending.value ||
    settingsQuery.isPending.value ||
    settingsQuery.data.value === undefined,
)

const isReady = computed(() => !isLoading.value && !settingsQuery.isError.value)

const canSubmit = computed(
  () => !completeMutation.isPending.value && brandName.value.trim().length > 0,
)

/**
 * Seeds the wizard from the loaded server settings on first resolution and
 * immediately applies the saved theme + language so the wizard renders in the
 * configured appearance. The `language`/`theme` watchers below re-apply on any
 * later change.
 */
watch(
  settingsQuery.data,
  (settings) => {
    if (!settings) {
      return
    }
    language.value = isSupportedLocale(settings.defaultLanguage)
      ? settings.defaultLanguage
      : getInitialLocale()
    theme.value = settings.defaultTheme
    brandName.value = settings.brandName
    units.value = settings.units
    currency.value = settings.currency
    recordsPerPage.value = settings.numRecordsPerPage
    signupEnabled.value = settings.signupEnabled
  },
  { immediate: true },
)

/** Live-preview the chosen interface language. */
watch(language, (value) => {
  if (isSupportedLocale(value)) {
    void loadLocaleMessages(value).then(() => setI18nLocale(value))
  }
})

/** Live-preview the chosen theme before it is saved as the server default. */
watch(theme, (value) => setTheme(value))

/**
 * Persists the wizard choices: every editable server setting round-trips from
 * the loaded record (the backend replaces the whole row), with the wizard
 * fields overlaid on top. On success the chosen theme is applied and the user
 * is sent to the post-login destination.
 */
async function submit(): Promise<void> {
  const settings = settingsQuery.data.value
  if (!settings || completeMutation.isPending.value) {
    return
  }

  const payload: ServerSettings = {
    ...settings,
    defaultLanguage: language.value,
    defaultTheme: theme.value,
    brandName: brandName.value.trim() || 'ZAPFIT',
    units: units.value,
    currency: currency.value,
    numRecordsPerPage: recordsPerPage.value,
    signupEnabled: signupEnabled.value,
  }

  submitError.value = false
  try {
    await completeMutation.mutateAsync(payload)
    setTheme(theme.value)
    // Ensure the locale is explicitly applied and persisted so the chosen
    // language survives a page reload even if applyPreferredLocale runs.
    if (isSupportedLocale(language.value)) {
      await loadLocaleMessages(language.value)
      setI18nLocale(language.value)
    }
    await queryClient.invalidateQueries({ queryKey: queryKeys.serverSettings.setupStatus() })
    await navigateAfterLogin()
  } catch {
    submitError.value = true
  }
}
</script>

<template>
  <div class="mx-auto flex min-h-dvh w-full max-w-2xl flex-col justify-center px-4 py-8">
    <Card padding="lg" class="flex flex-col gap-6">
      <header class="flex flex-col items-center gap-3 text-center">
        <AppLogo alt="" class="h-10 w-auto" />
        <div class="flex flex-col gap-1">
          <h1 class="text-page-title">{{ t('setup.title', { brand: brandNameDisplay }) }}</h1>
          <p class="text-body">{{ t('setup.subtitle') }}</p>
        </div>
      </header>

      <Alert v-if="settingsQuery.isError.value" kind="error">
        <div class="flex items-center justify-between gap-3">
          <span>{{ t('setup.loadError.title') }}</span>
          <Button variant="outline" size="sm" @click="settingsQuery.refetch()">
            {{ t('setup.loadError.retry') }}
          </Button>
        </div>
      </Alert>

      <Alert v-if="submitError" kind="error">
        <div class="flex items-center justify-between gap-3">
          <span>{{ t('setup.submitError.title') }}</span>
          <Button
            variant="outline"
            size="sm"
            :disabled="completeMutation.isPending.value"
            @click="submit"
          >
            {{ t('setup.submitError.retry') }}
          </Button>
        </div>
      </Alert>

      <div v-if="isLoading" class="flex items-center justify-center gap-2 py-10" aria-busy="true">
        <LoaderCircle class="animate-spin text-muted-foreground" />
        <span class="text-meta">{{ t('setup.loading') }}</span>
      </div>

      <form v-else-if="isReady" class="flex flex-col gap-5" @submit.prevent="submit">
        <section class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <h2 class="text-body font-semibold text-foreground">{{ t('setup.identity.title') }}</h2>
            <p class="text-hint">{{ t('setup.identity.description') }}</p>
          </div>

          <FormField
            :label="t('setup.language.label')"
            :hint="t('setup.language.description')"
            required
          >
            <template #default="{ fieldId, describedBy }">
              <Select v-model="language" :id="fieldId" :aria-describedby="describedBy">
                <option v-for="option in languageOptions" :key="option.code" :value="option.code">
                  {{ option.label }}
                </option>
              </Select>
            </template>
          </FormField>

          <FormField :label="t('setup.theme.label')" :hint="t('setup.theme.description')" required>
            <template #default="{ fieldId, describedBy }">
              <Select v-model="theme" :id="fieldId" :aria-describedby="describedBy">
                <option
                  v-for="option in optionsQuery.data.value?.themes ?? []"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </Select>
            </template>
          </FormField>

          <FormField :label="t('setup.brand.label')" :hint="t('setup.brand.description')" required>
            <template #default="{ fieldId, describedBy, invalid }">
              <Input
                :id="fieldId"
                v-model="brandName"
                :aria-describedby="describedBy"
                :aria-invalid="invalid"
                :maxlength="64"
              />
            </template>
          </FormField>
        </section>

        <section class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <h2 class="text-body font-semibold text-foreground">
              {{ t('setup.preferences.title') }}
            </h2>
            <p class="text-hint">{{ t('setup.preferences.description') }}</p>
          </div>

          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <FormField :label="t('setup.preferences.units')">
              <template #default="{ fieldId }">
                <Select v-model="units" :id="fieldId">
                  <option value="metric">{{ t('setup.preferences.unitsMetric') }}</option>
                  <option value="imperial">{{ t('setup.preferences.unitsImperial') }}</option>
                </Select>
              </template>
            </FormField>

            <FormField :label="t('setup.preferences.currency')">
              <template #default="{ fieldId }">
                <Select v-model="currency" :id="fieldId">
              <option value="euro">{{ t('setup.preferences.currencyEuro') }}</option>
              <option value="dollar">{{ t('setup.preferences.currencyDollar') }}</option>
              <option value="pound">{{ t('setup.preferences.currencyPound') }}</option>
              <option value="ruble">{{ t('setup.preferences.currencyRuble') }}</option>
                </Select>
              </template>
            </FormField>
          </div>

          <FormField :label="t('setup.preferences.recordsPerPage')">
            <template #default="{ fieldId }">
              <Select v-model="recordsPerPage" :id="fieldId">
                <option v-for="value in RECORDS_PER_PAGE_OPTIONS" :key="value" :value="value">
                  {{ value }}
                </option>
              </Select>
            </template>
          </FormField>

          <Switch v-model="signupEnabled">
            {{ t('setup.preferences.signup') }}
          </Switch>
        </section>

        <Button type="submit" size="lg" :disabled="!canSubmit">
          <LoaderCircle v-if="completeMutation.isPending.value" class="animate-spin" />
          {{ completeMutation.isPending.value ? t('setup.submitting') : t('setup.submit') }}
        </Button>
      </form>
    </Card>
  </div>
</template>
