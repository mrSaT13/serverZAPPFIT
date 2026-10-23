<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuery } from '@tanstack/vue-query'
import { Pencil, Trash2 } from '@lucide/vue'

import type { ActivityComment } from '@/features/activities/types'

import { queryKeys } from '@/services/queryKeys'
import UserAvatar from '@/components/UserAvatar.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { fetchActivityOwner } from '@/features/activities/services/activityOwner'
import { useCurrentUser } from '@/features/auth/composables/useCurrentUser'
import { useAuthStore } from '@/features/auth/stores/auth'
import {
  useDeleteActivityComment,
  useUpdateActivityComment,
} from '@/features/activities/composables/useActivityComments'

const props = defineProps<{
  /** The comment to render. */
  comment: ActivityComment
  /** Id of the commented activity (for invalidation and delete rights). */
  activityId: number
  /** Id of the activity owner (may delete foreign comments). */
  activityOwnerId: number | null
}>()

const { t, locale } = useI18n()
const auth = useAuthStore()
const { data: currentUser } = useCurrentUser()

const updateMutation = useUpdateActivityComment()
const deleteMutation = useDeleteActivityComment()

/** The comment author's identity: self from cache, others via the user endpoint. */
const authorQuery = useQuery({
  queryKey: computed(() => queryKeys.activities.owner(props.comment.userId)),
  queryFn: ({ signal }) => fetchActivityOwner(props.comment.userId, auth.isAuthenticated, signal),
  enabled: computed(
    () => props.comment.userId > 0 && currentUser.value?.id !== props.comment.userId,
  ),
  staleTime: 5 * 60_000,
})

const authorName = computed(() => {
  if (currentUser.value && currentUser.value.id === props.comment.userId) {
    return currentUser.value.name
  }
  return authorQuery.data.value?.name ?? t('activities.athlete')
})
const authorAvatar = computed(() => {
  if (currentUser.value && currentUser.value.id === props.comment.userId) {
    return currentUser.value.avatarUrl
  }
  return authorQuery.data.value?.avatarUrl ?? undefined
})

const createdLabel = computed(() => {
  const date = new Date(props.comment.createdAt)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(
    date,
  )
})

const isAuthor = computed(
  () => currentUser.value != null && currentUser.value.id === props.comment.userId,
)
const canDelete = computed(
  () =>
    isAuthor.value ||
    (currentUser.value != null &&
      props.activityOwnerId != null &&
      currentUser.value.id === props.activityOwnerId),
)

const editing = ref(false)
const draft = ref('')

function startEdit() {
  draft.value = props.comment.content
  editing.value = true
}

async function saveEdit() {
  const content = draft.value.trim()
  if (!content || content === props.comment.content) {
    editing.value = false
    return
  }
  await updateMutation.mutateAsync({ commentId: props.comment.id, content })
  editing.value = false
}

async function remove() {
  if (!window.confirm(t('activities.comments.deleteConfirm'))) {
    return
  }
  await deleteMutation.mutateAsync({ activityId: props.activityId, commentId: props.comment.id })
}
</script>

<template>
  <div class="flex items-start gap-2">
    <UserAvatar :src="authorAvatar" :alt="authorName" size-class="size-8" icon-class="size-4" />
    <div class="min-w-0 flex-1">
      <p class="text-caption">
        <span class="font-medium">{{ authorName }}</span>
        <span v-if="createdLabel" class="text-hint"> · {{ createdLabel }}</span>
      </p>
      <template v-if="editing">
        <div class="mt-1 flex gap-2">
          <Input v-model="draft" maxlength="2000" @keydown.enter="saveEdit" />
          <Button size="sm" :disabled="updateMutation.isPending.value" @click="saveEdit">
            {{ t('activities.comments.save') }}
          </Button>
          <Button size="sm" variant="ghost" @click="editing = false">
            {{ t('activities.comments.cancel') }}
          </Button>
        </div>
      </template>
      <p v-else class="text-body break-words">{{ comment.content }}</p>
    </div>
    <div v-if="!editing" class="flex shrink-0 items-center">
      <Button
        v-if="isAuthor"
        size="icon"
        variant="ghost"
        :aria-label="t('activities.comments.edit')"
        @click="startEdit"
      >
        <Pencil class="size-4" />
      </Button>
      <Button
        v-if="canDelete"
        size="icon"
        variant="ghost"
        :aria-label="t('activities.comments.delete')"
        :disabled="deleteMutation.isPending.value"
        @click="remove"
      >
        <Trash2 class="size-4" />
      </Button>
    </div>
  </div>
</template>
