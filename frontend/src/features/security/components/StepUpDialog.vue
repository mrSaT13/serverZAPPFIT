<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { StepUpInput } from '@/features/security/types'

import PasswordInput from '@/features/security/components/PasswordInput.vue'
import { FormDialog } from '@/components/ui/form-dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const open = defineModel<boolean>('open', { required: true })

const props = withDefaults(
  defineProps<{
    /** Dialog heading. */
    title: string
    /** Supporting copy below the title. */
    description: string
    /** Label for the confirm button. */
    confirmLabel: string
    /** Whether a password is required (the account has a local password). */
    requirePassword: boolean
    /** Whether an MFA/backup code is required (MFA is enabled). */
    requireMfa?: boolean
    /** Whether the confirming action is in flight. */
    pending: boolean
  }>(),
  { requireMfa: true },
)

const emit = defineEmits<{
  confirm: [input: StepUpInput]
}>()

const { t } = useI18n()

const password = ref('')
const mfaCode = ref('')

const canSubmit = computed(
  () =>
    (!props.requirePassword || password.value.length > 0) &&
    (!props.requireMfa || mfaCode.value.trim().length > 0),
)

// Clear the fields each time the dialog opens.
watch(open, (isOpen) => {
  if (isOpen) {
    password.value = ''
    mfaCode.value = ''
  }
})

/** Emits the collected step-up credentials; the parent runs the action. */
function onSubmit(): void {
  emit('confirm', {
    currentPassword: props.requirePassword ? password.value : null,
    mfaCode: props.requireMfa ? mfaCode.value.trim() : null,
  })
}
</script>

<template>
  <FormDialog
    v-model:open="open"
    :title="title"
    :description="description"
    :submit-label="confirmLabel"
    :cancel-label="t('settings.security.cancel')"
    :close-label="t('settings.security.close')"
    :submitting="pending"
    :can-submit="canSubmit"
    @submit="onSubmit"
  >
    <div class="flex flex-col gap-3">
      <div v-if="requirePassword" class="flex flex-col gap-1.5">
        <Label for="stepup-password">{{ t('settings.security.password.current') }}</Label>
        <PasswordInput
          id="stepup-password"
          v-model="password"
          autocomplete="current-password"
          :disabled="pending"
        />
      </div>
      <div v-if="requireMfa" class="flex flex-col gap-1.5">
        <Label for="stepup-mfa">{{ t('settings.security.mfaCode') }}</Label>
        <Input
          id="stepup-mfa"
          v-model="mfaCode"
          inputmode="numeric"
          autocomplete="one-time-code"
          :placeholder="t('settings.security.mfaCodePlaceholder')"
          :disabled="pending"
          class="w-full"
        />
      </div>
    </div>
  </FormDialog>
</template>
