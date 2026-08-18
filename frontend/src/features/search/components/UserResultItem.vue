<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import type { ManagedUser } from '@/features/users/types'

import UserAvatar from '@/components/UserAvatar.vue'
import { Badge } from '@/components/ui/badge'

/**
 * One user row in the search results: avatar, name, and `@username`, linking to
 * the public profile. An "inactive" badge marks deactivated accounts (parity
 * with v1's search list).
 */
defineProps<{ user: ManagedUser }>()

const { t } = useI18n()
</script>

<template>
  <RouterLink
    :to="{ name: 'user', params: { id: user.id } }"
    class="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/50"
  >
    <span
      class="flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-muted text-muted-foreground"
    >
      <UserAvatar :src="user.avatarUrl" :alt="user.name" size-class="size-10" icon-class="size-5" />
    </span>
    <div class="min-w-0 flex-1">
      <p class="truncate font-medium text-foreground">{{ user.name }}</p>
      <p class="truncate text-hint">@{{ user.username }}</p>
    </div>
    <Badge v-if="!user.active" variant="destructive">{{ t('search.results.inactive') }}</Badge>
  </RouterLink>
</template>
