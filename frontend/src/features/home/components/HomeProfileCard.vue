<script setup lang="ts">
import { Card } from '@/components/ui/card'
import UserAvatar from '@/components/UserAvatar.vue'

defineProps<{
  /** Display name shown beneath the avatar. */
  name: string
  /** Login handle, shown as `@username`. */
  username: string
  /** Absolute avatar URL, or `null` when unset. */
  avatarUrl: string | null
}>()
</script>

<template>
  <Card class="flex flex-col items-center gap-3 text-center">
    <UserAvatar :src="avatarUrl" :alt="name" size-class="size-20" icon-class="size-10" />
    <div class="min-w-0">
      <p class="truncate text-card-heading">{{ name }}</p>
      <p class="truncate text-caption">@{{ username }}</p>
    </div>
  </Card>
</template>
