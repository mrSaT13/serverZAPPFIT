<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Ban, Plus, Trash2 } from '@lucide/vue'

import type { ApiKey, ApiKeyCreateInput } from '@/features/security/types'

import ApiKeyCreateDialog from '@/features/security/components/ApiKeyCreateDialog.vue'
import ApiKeyRevealDialog from '@/features/security/components/ApiKeyRevealDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { HttpError } from '@/services/http'
import { useToasts } from '@/composables/useToasts'
import { formatMediumDate } from '@/utils/datetime'
import {
  useApiKeysQuery,
  useCreateApiKeyMutation,
  useDeleteApiKeyMutation,
  useRevokeApiKeyMutation,
} from '@/features/security/composables/useSecurity'

defineProps<{
  /** Whether the account has a local password (gates the step-up password field). */
  hasLocalPassword: boolean
  /** Whether MFA is enabled (gates the step-up MFA-code field). */
  mfaEnabled: boolean
}>()

const { t, locale } = useI18n()
const toasts = useToasts()

const { data, isPending, isError, refetch } = useApiKeysQuery()
const apiKeys = computed(() => data.value ?? [])

const createMutation = useCreateApiKeyMutation()
const revokeMutation = useRevokeApiKeyMutation()
const deleteMutation = useDeleteApiKeyMutation()

const isCreateOpen = ref(false)
const isRevealOpen = ref(false)
const newApiKey = ref('')

// One shared confirm dialog per action drives every row (the pending target is
// held in a ref), mirroring SessionsCard.
const keyToRevoke = ref<ApiKey | null>(null)
const isRevokeOpen = ref(false)
const keyToDelete = ref<ApiKey | null>(null)
const isDeleteOpen = ref(false)

/** Formats an ISO date in the active locale, or `''` when unparseable. */
function formatDate(iso: string): string {
  return formatMediumDate(iso, locale.value)
}

/** Creates the key, then opens the one-time reveal dialog with the raw key. */
function onCreate(input: ApiKeyCreateInput): void {
  createMutation.mutate(input, {
    onSuccess: (rawKey) => {
      isCreateOpen.value = false
      newApiKey.value = rawKey
      isRevealOpen.value = true
      toasts.success(t('settings.security.apiKeys.createSuccess'))
    },
    onError: (error) => {
      if (error instanceof HttpError && error.status === 401) {
        toasts.error(t('settings.security.apiKeys.invalidCredentials'))
      } else if (error instanceof HttpError && error.status === 400) {
        toasts.error(t('settings.security.apiKeys.invalidScopes'))
      } else {
        toasts.error(t('settings.security.apiKeys.createError'))
      }
    },
  })
}

function openRevoke(key: ApiKey): void {
  keyToRevoke.value = key
  isRevokeOpen.value = true
}

function confirmRevoke(): void {
  const key = keyToRevoke.value
  if (!key) {
    return
  }
  revokeMutation.mutate(key.id, {
    onSuccess: () => {
      isRevokeOpen.value = false
      toasts.success(t('settings.security.apiKeys.revokeSuccess'))
    },
    onError: () => toasts.error(t('settings.security.apiKeys.revokeError')),
  })
}

function openDelete(key: ApiKey): void {
  keyToDelete.value = key
  isDeleteOpen.value = true
}

function confirmDelete(): void {
  const key = keyToDelete.value
  if (!key) {
    return
  }
  deleteMutation.mutate(key.id, {
    onSuccess: () => {
      isDeleteOpen.value = false
      toasts.success(t('settings.security.apiKeys.deleteSuccess'))
    },
    onError: () => toasts.error(t('settings.security.apiKeys.deleteError')),
  })
}
</script>

<template>
  <Card class="flex flex-col gap-3">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="flex flex-col gap-1">
        <h2 class="text-card-heading">{{ t('settings.security.apiKeys.title') }}</h2>
        <p class="text-hint">{{ t('settings.security.apiKeys.subtitle') }}</p>
      </div>
      <Button variant="outline" size="sm" @click="isCreateOpen = true">
        <Plus class="size-4" aria-hidden="true" />
        {{ t('settings.security.apiKeys.create') }}
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="isPending" class="flex flex-col gap-2" aria-busy="true">
      <Skeleton v-for="n in 2" :key="n" class="h-16 w-full rounded-input" />
    </div>

    <!-- Error -->
    <div v-else-if="isError" class="flex flex-col items-start gap-2">
      <p class="text-hint">{{ t('settings.security.apiKeys.error') }}</p>
      <Button variant="outline" size="sm" @click="() => refetch()">
        {{ t('settings.security.retry') }}
      </Button>
    </div>

    <!-- Empty -->
    <p v-else-if="apiKeys.length === 0" class="text-hint">
      {{ t('settings.security.apiKeys.empty') }}
    </p>

    <!-- List -->
    <ul v-else class="divide-y divide-border overflow-hidden rounded-card border border-border">
      <li
        v-for="key in apiKeys"
        :key="key.id"
        class="flex items-start justify-between gap-3 px-4 py-3"
      >
        <div class="flex min-w-0 flex-col gap-1.5">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-body font-medium">{{ key.name }}</span>
            <code class="rounded bg-muted-foreground/15 px-1.5 py-0.5 font-mono text-xs">
              {{ key.keyPrefix }}…
            </code>
            <Badge :variant="key.isActive ? 'secondary' : 'destructive'">
              {{
                key.isActive
                  ? t('settings.security.apiKeys.statusActive')
                  : t('settings.security.apiKeys.statusRevoked')
              }}
            </Badge>
          </div>
          <div v-if="key.scopes.length > 0" class="flex flex-wrap gap-1">
            <Badge v-for="scope in key.scopes" :key="scope" variant="outline" class="font-mono">
              {{ scope }}
            </Badge>
          </div>
          <p class="text-hint">
            {{ t('settings.security.apiKeys.created', { date: formatDate(key.createdAt) }) }} ·
            {{
              key.lastUsedAt
                ? t('settings.security.apiKeys.lastUsed', { date: formatDate(key.lastUsedAt) })
                : t('settings.security.apiKeys.neverUsed')
            }}
            ·
            {{
              key.expiresAt
                ? t('settings.security.apiKeys.expires', { date: formatDate(key.expiresAt) })
                : t('settings.security.apiKeys.neverExpires')
            }}
          </p>
        </div>
        <div class="flex shrink-0 gap-1">
          <Button
            v-if="key.isActive"
            variant="ghost"
            size="icon-sm"
            :aria-label="t('settings.security.apiKeys.revoke')"
            @click="openRevoke(key)"
          >
            <Ban class="size-4" aria-hidden="true" />
          </Button>
          <Button
            variant="ghostDestructive"
            size="icon-sm"
            :aria-label="t('settings.security.apiKeys.delete')"
            @click="openDelete(key)"
          >
            <Trash2 class="size-4" aria-hidden="true" />
          </Button>
        </div>
      </li>
    </ul>

    <ApiKeyCreateDialog
      v-model:open="isCreateOpen"
      :require-password="hasLocalPassword"
      :require-mfa="mfaEnabled"
      :pending="createMutation.isPending.value"
      @submit="onCreate"
    />

    <ApiKeyRevealDialog v-model:open="isRevealOpen" :api-key="newApiKey" />

    <ConfirmDialog
      v-model:open="isRevokeOpen"
      :title="t('settings.security.apiKeys.revokeTitle')"
      :description="t('settings.security.apiKeys.revokeBody', { name: keyToRevoke?.name ?? '' })"
      :confirm-label="t('settings.security.apiKeys.revoke')"
      :cancel-label="t('settings.security.cancel')"
      :close-label="t('settings.security.close')"
      :pending="revokeMutation.isPending.value"
      confirm-variant="default"
      @confirm="confirmRevoke"
    />

    <ConfirmDialog
      v-model:open="isDeleteOpen"
      :title="t('settings.security.apiKeys.deleteTitle')"
      :description="t('settings.security.apiKeys.deleteBody', { name: keyToDelete?.name ?? '' })"
      :confirm-label="t('settings.security.apiKeys.delete')"
      :cancel-label="t('settings.security.cancel')"
      :close-label="t('settings.security.close')"
      :pending="deleteMutation.isPending.value"
      @confirm="confirmDelete"
    />
  </Card>
</template>
