<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { useQueryClient } from '@tanstack/vue-query'
import { Plus, Unlink } from '@lucide/vue'

import type { AvailableProvider, LinkedProvider, StepUpInput } from '@/features/security/types'

import ProviderLogo from '@/features/identityProviders/components/ProviderLogo.vue'
import StepUpDialog from '@/features/security/components/StepUpDialog.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useToasts } from '@/composables/useToasts'
import { queryKeys } from '@/services/queryKeys'
import { HttpError } from '@/services/http'
import { buildLinkStartUrl } from '@/features/security/services/linkedAccounts'
import {
  useAvailableProvidersQuery,
  useGenerateLinkTokenMutation,
  useLinkedProvidersQuery,
  useUnlinkProviderMutation,
} from '@/features/security/composables/useLinkedAccounts'

defineProps<{
  /** Whether the account has a local password (gates the step-up password field). */
  hasLocalPassword: boolean
  /** Whether MFA is enabled (gates the step-up MFA-code field). */
  mfaEnabled: boolean
}>()

const { t } = useI18n()
const toasts = useToasts()
const route = useRoute()
const router = useRouter()
const client = useQueryClient()

const linkedQuery = useLinkedProvidersQuery()
const availableQuery = useAvailableProvidersQuery()
const unlinkMutation = useUnlinkProviderMutation()
const linkTokenMutation = useGenerateLinkTokenMutation()

const linked = computed(() => linkedQuery.data.value ?? [])
const linkedIdpIds = computed(() => new Set(linked.value.map((item) => item.idpId)))
// Only offer providers the user hasn't already linked.
const available = computed(() =>
  (availableQuery.data.value ?? []).filter((provider) => !linkedIdpIds.value.has(provider.id)),
)

// One step-up dialog drives both link and unlink; the pending action decides
// which mutation runs on confirm.
type PendingAction = { type: 'link' | 'unlink'; idpId: number; name: string }
const pendingAction = ref<PendingAction | null>(null)
const isStepUpOpen = ref(false)

const isActionPending = computed(
  () => unlinkMutation.isPending.value || linkTokenMutation.isPending.value,
)

const stepUpTitle = computed(() =>
  pendingAction.value?.type === 'unlink'
    ? t('settings.security.linked.unlinkTitle')
    : t('settings.security.linked.linkTitle'),
)
const stepUpDescription = computed(() =>
  pendingAction.value?.type === 'unlink'
    ? t('settings.security.linked.unlinkDescription', { name: pendingAction.value?.name ?? '' })
    : t('settings.security.linked.linkDescription', { name: pendingAction.value?.name ?? '' }),
)
const stepUpConfirmLabel = computed(() =>
  pendingAction.value?.type === 'unlink'
    ? t('settings.security.linked.unlink')
    : t('settings.security.linked.link'),
)

/** Opens the step-up dialog to link the given available provider. */
function openLink(provider: AvailableProvider): void {
  pendingAction.value = { type: 'link', idpId: provider.id, name: provider.name }
  isStepUpOpen.value = true
}

/** Opens the step-up dialog to unlink the given linked provider. */
function openUnlink(item: LinkedProvider): void {
  pendingAction.value = {
    type: 'unlink',
    idpId: item.idpId,
    name: item.name ?? item.slug ?? `#${item.idpId}`,
  }
  isStepUpOpen.value = true
}

/** Begins the OAuth link: generates a token, then navigates to the backend. */
function confirmLink(idpId: number, input: StepUpInput): void {
  linkTokenMutation.mutate(
    { idpId, input },
    {
      onSuccess: (token) => {
        // Full-page navigation: the backend 307-redirects on to the provider,
        // then back to this page with an `idp_link` result handled on mount.
        window.location.assign(buildLinkStartUrl(idpId, token))
      },
      onError: (error) => {
        if (error instanceof HttpError && error.status === 409) {
          toasts.error(t('settings.security.linked.alreadyLinked'))
        } else if (error instanceof HttpError && error.status === 401) {
          toasts.error(t('settings.security.linked.invalidCredentials'))
        } else {
          toasts.error(t('settings.security.linked.linkError'))
        }
      },
    },
  )
}

/** Unlinks the pending provider after step-up. */
function confirmUnlink(idpId: number, input: StepUpInput): void {
  unlinkMutation.mutate(
    { idpId, input },
    {
      onSuccess: () => {
        isStepUpOpen.value = false
        toasts.success(t('settings.security.linked.unlinkSuccess'))
      },
      onError: (error) => {
        if (error instanceof HttpError && error.status === 400) {
          toasts.error(t('settings.security.linked.lastMethodError'))
        } else if (error instanceof HttpError && error.status === 401) {
          toasts.error(t('settings.security.linked.invalidCredentials'))
        } else {
          toasts.error(t('settings.security.linked.unlinkError'))
        }
      },
    },
  )
}

/** Dispatches the confirmed step-up to the link or unlink flow. */
function onStepUpConfirm(input: StepUpInput): void {
  const action = pendingAction.value
  if (!action) {
    return
  }
  if (action.type === 'link') {
    confirmLink(action.idpId, input)
  } else {
    confirmUnlink(action.idpId, input)
  }
}

/**
 * Handles the OAuth link round-trip result. The backend returns the browser to
 * `?idp_link=success|error` (with `idp_name`); surface it as a toast, refresh
 * the list, and strip the one-time params so a refresh doesn't re-toast.
 */
onMounted(() => {
  const status = route.query.idp_link
  if (typeof status !== 'string') {
    return
  }
  if (status === 'success') {
    const name = typeof route.query.idp_name === 'string' ? route.query.idp_name : ''
    toasts.success(
      name
        ? t('settings.security.linked.linkSuccess', { name })
        : t('settings.security.linked.linkSuccessGeneric'),
    )
    void client.invalidateQueries({ queryKey: queryKeys.security.linkedProviders() })
    void client.invalidateQueries({ queryKey: queryKeys.public.identityProviders() })
  } else if (status === 'error') {
    toasts.error(t('settings.security.linked.linkError'))
  }
  const nextQuery: LocationQueryRaw = {}
  for (const [key, value] of Object.entries(route.query)) {
    if (key !== 'idp_link' && key !== 'idp_name') {
      nextQuery[key] = value
    }
  }
  void router.replace({ query: nextQuery })
})
</script>

<template>
  <Card class="flex flex-col gap-3">
    <div class="flex flex-col gap-1">
      <h2 class="text-card-heading">{{ t('settings.security.linked.title') }}</h2>
      <p class="text-hint">{{ t('settings.security.linked.subtitle') }}</p>
    </div>

    <!-- Loading -->
    <div v-if="linkedQuery.isPending.value" class="flex flex-col gap-2" aria-busy="true">
      <Skeleton v-for="n in 2" :key="n" class="h-14 w-full rounded-input" />
    </div>

    <!-- Error -->
    <div v-else-if="linkedQuery.isError.value" class="flex flex-col items-start gap-2">
      <p class="text-hint">{{ t('settings.security.linked.error') }}</p>
      <Button variant="outline" size="sm" @click="() => linkedQuery.refetch()">
        {{ t('settings.security.retry') }}
      </Button>
    </div>

    <template v-else>
      <!-- Linked providers -->
      <ul
        v-if="linked.length > 0"
        class="divide-y divide-border overflow-hidden rounded-card border border-border"
      >
        <li
          v-for="item in linked"
          :key="item.id"
          class="flex items-center justify-between gap-3 px-4 py-3"
        >
          <div class="flex min-w-0 items-center gap-3">
            <ProviderLogo :icon="item.icon" :name="item.name ?? item.slug ?? ''" />
            <div class="min-w-0">
              <p class="text-body">{{ item.name ?? item.slug ?? `#${item.idpId}` }}</p>
              <p class="text-hint">{{ item.subject }}</p>
            </div>
          </div>
          <Button
            variant="ghostDestructive"
            size="sm"
            :aria-label="t('settings.security.linked.unlinkAria', { name: item.name ?? '' })"
            @click="openUnlink(item)"
          >
            <Unlink class="size-4" aria-hidden="true" />
            {{ t('settings.security.linked.unlink') }}
          </Button>
        </li>
      </ul>
      <p v-else class="text-hint">{{ t('settings.security.linked.empty') }}</p>

      <!-- Available providers to link -->
      <div v-if="available.length > 0" class="flex flex-col gap-2">
        <p class="text-caption">{{ t('settings.security.linked.available') }}</p>
        <div class="flex flex-wrap gap-2">
          <Button
            v-for="provider in available"
            :key="provider.id"
            variant="outline"
            size="sm"
            :disabled="isActionPending"
            @click="openLink(provider)"
          >
            <Plus class="size-4" aria-hidden="true" />
            {{ provider.name }}
          </Button>
        </div>
      </div>
    </template>

    <StepUpDialog
      v-model:open="isStepUpOpen"
      :title="stepUpTitle"
      :description="stepUpDescription"
      :confirm-label="stepUpConfirmLabel"
      :require-password="hasLocalPassword"
      :require-mfa="mfaEnabled"
      :pending="isActionPending"
      @confirm="onStepUpConfirm"
    />
  </Card>
</template>
