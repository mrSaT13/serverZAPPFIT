<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RefreshCw, ShieldCheck, Smartphone } from '@lucide/vue'

import type { StepUpInput } from '@/features/security/types'

import BackupCodesDialog from '@/features/security/components/BackupCodesDialog.vue'
import MfaSetupDialog from '@/features/security/components/MfaSetupDialog.vue'
import StepUpDialog from '@/features/security/components/StepUpDialog.vue'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useToasts } from '@/composables/useToasts'
import {
  useBackupCodeStatusQuery,
  useDisableMfaMutation,
  useMfaStatusQuery,
  useRegenerateBackupCodesMutation,
} from '@/features/security/composables/useSecurity'

defineProps<{
  /** Whether the account has a local password (gates step-up password fields). */
  hasLocalPassword: boolean
}>()

const { t } = useI18n()
const toasts = useToasts()

const statusQuery = useMfaStatusQuery()
const enabled = computed(() => statusQuery.data.value?.enabled ?? false)
const backupStatusQuery = useBackupCodeStatusQuery(enabled)

const disableMutation = useDisableMfaMutation()
const regenerateMutation = useRegenerateBackupCodesMutation()

const setupOpen = ref(false)
const disableOpen = ref(false)
const regenerateOpen = ref(false)
const backupCodesOpen = ref(false)
const backupCodes = ref<string[]>([])

/** Shows the freshly issued codes once enrolment completes. */
function onEnabled(codes: string[]): void {
  backupCodes.value = codes
  backupCodesOpen.value = true
  toasts.success(t('settings.security.mfa.enableSuccess'))
}

/** Disables MFA with the collected step-up credentials. */
function confirmDisable(input: StepUpInput): void {
  disableMutation.mutate(input, {
    onSuccess: () => {
      disableOpen.value = false
      toasts.success(t('settings.security.mfa.disableSuccess'))
    },
    onError: () => toasts.error(t('settings.security.mfa.disableError')),
  })
}

/** Regenerates the backup codes, then shows the new set. */
function confirmRegenerate(input: StepUpInput): void {
  regenerateMutation.mutate(input, {
    onSuccess: (result) => {
      regenerateOpen.value = false
      backupCodes.value = result.codes
      backupCodesOpen.value = true
      toasts.success(t('settings.security.mfa.regenerateSuccess'))
    },
    onError: () => toasts.error(t('settings.security.mfa.regenerateError')),
  })
}
</script>

<template>
  <Card class="flex flex-col gap-3">
    <div class="flex flex-col gap-1">
      <h2 class="text-card-heading">{{ t('settings.security.mfa.title') }}</h2>
      <p class="text-hint">{{ t('settings.security.mfa.subtitle') }}</p>
    </div>

    <!-- Loading -->
    <div v-if="statusQuery.isPending.value" class="flex flex-col gap-2" aria-busy="true">
      <Skeleton class="h-5 w-48" />
      <Skeleton class="h-9 w-36" />
    </div>

    <!-- Error -->
    <div v-else-if="statusQuery.isError.value" class="flex flex-col items-start gap-2">
      <p class="text-hint">{{ t('settings.security.mfa.loadError') }}</p>
      <Button variant="outline" size="sm" @click="() => statusQuery.refetch()">
        {{ t('settings.security.retry') }}
      </Button>
    </div>

    <template v-else>
      <!-- Disabled -->
      <div v-if="!enabled" class="flex flex-col items-start gap-3">
        <p class="text-body">{{ t('settings.security.mfa.disabledDescription') }}</p>
        <Button @click="setupOpen = true">
          <Smartphone class="size-4" aria-hidden="true" />
          {{ t('settings.security.mfa.enable') }}
        </Button>
      </div>

      <!-- Enabled -->
      <div v-else class="flex flex-col gap-3">
        <Alert kind="success">
          <span class="inline-flex items-center gap-2">
            <ShieldCheck class="size-4 shrink-0" aria-hidden="true" />
            {{ t('settings.security.mfa.enabledDescription') }}
          </span>
        </Alert>
        <p v-if="backupStatusQuery.data.value" class="text-hint">
          {{
            t('settings.security.mfa.backupRemaining', {
              unused: backupStatusQuery.data.value.unused,
              total: backupStatusQuery.data.value.total,
            })
          }}
        </p>
        <div class="flex flex-wrap gap-2">
          <Button variant="outline" @click="regenerateOpen = true">
            <RefreshCw class="size-4" aria-hidden="true" />
            {{ t('settings.security.mfa.regenerate') }}
          </Button>
          <Button variant="destructive" @click="disableOpen = true">
            {{ t('settings.security.mfa.disable') }}
          </Button>
        </div>
      </div>
    </template>

    <MfaSetupDialog
      v-model:open="setupOpen"
      :require-password="hasLocalPassword"
      @enabled="onEnabled"
      @error="(message) => toasts.error(message)"
    />
    <StepUpDialog
      v-model:open="disableOpen"
      :title="t('settings.security.mfa.disableTitle')"
      :description="t('settings.security.mfa.disableDescription')"
      :confirm-label="t('settings.security.mfa.disable')"
      :require-password="hasLocalPassword"
      :pending="disableMutation.isPending.value"
      @confirm="confirmDisable"
    />
    <StepUpDialog
      v-model:open="regenerateOpen"
      :title="t('settings.security.mfa.regenerateTitle')"
      :description="t('settings.security.mfa.regenerateDescription')"
      :confirm-label="t('settings.security.mfa.regenerate')"
      :require-password="hasLocalPassword"
      :pending="regenerateMutation.isPending.value"
      @confirm="confirmRegenerate"
    />
    <BackupCodesDialog v-model:open="backupCodesOpen" :codes="backupCodes" />
  </Card>
</template>
