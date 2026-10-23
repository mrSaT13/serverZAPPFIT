<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Languages, LoaderCircle } from '@lucide/vue'

import type { ProfileDetails, ProfileEditInput } from '@/features/profile/types'
import type { Schemas } from '@/types'

import { Card } from '@/components/ui/card'
import { FormField } from '@/components/ui/form-field'
import { Select } from '@/components/ui/select'
import { useLocale } from '@/composables/useLocale'
import { useToasts } from '@/composables/useToasts'
import { useUpdateProfileMutation } from '@/features/profile/composables/useProfile'
import { sortLanguageCodes } from '@/features/users/utils/userFieldOptions'

const props = defineProps<{
  /** The loaded profile; seeds the selector (mounted only after load). */
  profile: ProfileDetails
}>()

const { t, locale } = useI18n()
const { setLocale } = useLocale()
const toasts = useToasts()
const updateMutation = useUpdateProfileMutation()

const languageCodes = computed(() =>
  sortLanguageCodes((code) => t(`settings.users.form.languages.${code}`), locale.value),
)

const selected = ref<Schemas['Language']>(props.profile.preferredLanguage)

/**
 * Persists the language to the profile and applies it locally. The locale
 * is applied optimistically so the UI (including these very labels)
 * switches immediately; a server failure rolls the selector back.
 */
async function onChange(next: Schemas['Language']): Promise<void> {
  const previous = selected.value
  selected.value = next
  const input: ProfileEditInput = {
    name: props.profile.name,
    username: props.profile.username,
    email: props.profile.email,
    city: props.profile.city,
    birthdate: props.profile.birthdate,
    gender: props.profile.gender,
    units: props.profile.units,
    currency: props.profile.currency,
    height: props.profile.height,
    maxHeartRate: props.profile.maxHeartRate,
    preferredLanguage: next,
    firstDayOfWeek: props.profile.firstDayOfWeek,
  }
  try {
    await updateMutation.mutateAsync(input)
    await setLocale(next)
    toasts.success(t('settings.profile.language.updated'))
  } catch {
    selected.value = previous
    toasts.error(t('settings.profile.language.updateError'))
  }
}
</script>

<template>
  <Card class="flex flex-col gap-3">
    <div class="flex items-start gap-3">
      <Languages class="mt-0.5 size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div class="flex flex-col gap-1">
        <h2 class="text-card-heading">{{ t('settings.profile.language.title') }}</h2>
        <p class="text-body">{{ t('settings.profile.language.subtitle') }}</p>
      </div>
    </div>

    <FormField :label="t('settings.users.form.preferredLanguage')">
      <template #default="{ fieldId }">
        <div class="flex items-center gap-2">
          <Select
            :id="fieldId"
            :model-value="selected"
            :disabled="updateMutation.isPending.value"
            @update:model-value="onChange($event as Schemas['Language'])"
          >
            <option v-for="code in languageCodes" :key="code" :value="code">
              {{ t(`settings.users.form.languages.${code}`) }}
            </option>
          </Select>
          <LoaderCircle
            v-if="updateMutation.isPending.value"
            class="size-4 shrink-0 animate-spin text-muted-foreground"
            aria-hidden="true"
          />
        </div>
      </template>
    </FormField>
  </Card>
</template>
