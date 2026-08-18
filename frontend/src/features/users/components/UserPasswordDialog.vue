<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { FormDialog } from '@/components/ui/form-dialog'
import { FormField } from '@/components/ui/form-field'
import { useForm } from '@/composables/useForm'
import { usePublicServerSettings } from '@/features/config/composables/usePublicServerSettings'
import PasswordInput from '@/features/security/components/PasswordInput.vue'
import { HttpError } from '@/services/http'
import {
  buildPasswordRequirements,
  isValidPassword,
  resolvePasswordMinLength,
} from '@/utils/validation'
import { compose, required } from '@/utils/validators'
import { useChangeUserPasswordMutation } from '@/features/users/composables/useUsers'

const open = defineModel<boolean>('open', { required: true })

const props = defineProps<{
  /** The target user's id. */
  userId: number
  /** The target user's username, shown in the dialog copy. */
  username: string
  /** The target user's access type, so the right length policy is enforced. */
  accessType: string
}>()

const emit = defineEmits<{
  success: [message: string]
  error: [message: string]
}>()

const { t } = useI18n()

const mutation = useChangeUserPasswordMutation()
const { serverSettings } = usePublicServerSettings()

/** Password policy mirrored from the server (length-only or strict), scoped
 * to the target user's access tier. */
const passwordRequirements = computed(() =>
  buildPasswordRequirements(
    serverSettings.value.password_type,
    resolvePasswordMinLength(
      serverSettings.value.password_length_regular_users,
      serverSettings.value.password_length_admin_users,
      props.accessType,
    ),
  ),
)
/** Human-readable hint describing the active password policy. */
const passwordHint = computed(() =>
  serverSettings.value.password_type === 'length_only'
    ? t('settings.users.password.hintLength', { min: passwordRequirements.value.minLength })
    : t('settings.users.password.hintStrict', { min: passwordRequirements.value.minLength }),
)

/** Form shape: the new password plus its confirmation. */
interface PasswordFormValues {
  password: string
  confirm: string
}

/**
 * Sets the new password via the admin endpoint, emitting the outcome and
 * closing on success. The confirm field is validated reactively (see
 * `passwordsMatch`); this also guards against an Enter-key submit slipping
 * through on a mismatch.
 *
 * @param formValues - The validated form values.
 */
async function submitForm(formValues: PasswordFormValues): Promise<void> {
  if (formValues.password !== formValues.confirm) {
    return
  }
  try {
    await mutation.mutateAsync({ userId: props.userId, password: formValues.password })
    emit('success', t('settings.users.password.success'))
    open.value = false
  } catch (error) {
    if (error instanceof HttpError && (error.status === 400 || error.status === 422)) {
      emit('error', t('settings.users.password.invalid'))
    } else {
      emit('error', t('settings.users.password.error'))
    }
  }
}

const { values, errors, isValid, isSubmitting, handleSubmit, handleBlur, reset } =
  useForm<PasswordFormValues>({
    initialValues: { password: '', confirm: '' },
    validators: {
      password: compose(required<string>(t('settings.users.password.required')), (value) =>
        isValidPassword(value, passwordRequirements.value)
          ? null
          : t('settings.users.password.invalid'),
      ),
    },
    onSubmit: submitForm,
  })

/** Whether the confirmation matches a non-empty new password. */
const passwordsMatch = computed(
  () => values.confirm.length > 0 && values.confirm === values.password,
)
/** Inline confirmation error, shown once the user has typed a mismatch. */
const confirmError = computed(() =>
  values.confirm.length > 0 && values.confirm !== values.password
    ? t('settings.users.password.mismatch')
    : undefined,
)

// Reset to a clean form each time the dialog opens.
watch(open, (isOpen) => {
  if (isOpen) {
    reset()
  }
})
</script>

<template>
  <FormDialog
    v-model:open="open"
    :title="t('settings.users.password.title')"
    :description="t('settings.users.password.description', { username })"
    :submit-label="t('settings.users.password.submit')"
    :cancel-label="t('settings.users.password.cancel')"
    :close-label="t('settings.users.password.close')"
    :submitting="isSubmitting"
    :can-submit="isValid && passwordsMatch"
    @submit="handleSubmit"
  >
    <div class="flex flex-col gap-3">
      <FormField
        :label="t('settings.users.password.newLabel')"
        :placeholder="t('settings.users.password.newLabel')"
        :error="errors.password"
        :hint="passwordHint"
        required
      >
        <template #default="{ fieldId, describedBy, invalid, placeholder }">
          <PasswordInput
            :id="fieldId"
            v-model="values.password"
            :aria-describedby="describedBy"
            :aria-invalid="invalid"
            :placeholder="placeholder"
            name="new-password"
            autocomplete="new-password"
            :disabled="isSubmitting"
            @blur="handleBlur('password')"
          />
        </template>
      </FormField>

      <FormField
        :label="t('settings.users.password.confirmLabel')"
        :placeholder="t('settings.users.password.confirmLabel')"
        :error="confirmError"
        required
      >
        <template #default="{ fieldId, describedBy, invalid, placeholder }">
          <PasswordInput
            :id="fieldId"
            v-model="values.confirm"
            :aria-describedby="describedBy"
            :aria-invalid="invalid"
            :placeholder="placeholder"
            name="confirm-password"
            autocomplete="new-password"
            :disabled="isSubmitting"
          />
        </template>
      </FormField>
    </div>
  </FormDialog>
</template>
