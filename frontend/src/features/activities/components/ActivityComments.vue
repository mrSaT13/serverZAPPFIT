<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, ChevronUp, MessageCircle } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import ActivityCommentItem from '@/features/activities/components/ActivityCommentItem.vue'
import {
  useActivityCommentCountQuery,
  useActivityCommentsQuery,
  useCreateActivityComment,
} from '@/features/activities/composables/useActivityComments'

const props = defineProps<{
  /** Id of the commented activity. */
  activityId: number
  /** Id of the activity owner (may delete foreign comments). */
  activityOwnerId: number | null
}>()

const { t } = useI18n()

const expanded = ref(false)
const draft = ref('')

const commentsQuery = useActivityCommentsQuery(
  () => props.activityId,
  () => expanded.value,
)
const countQuery = useActivityCommentCountQuery(() => props.activityId)
const createMutation = useCreateActivityComment()

const comments = computed(() => commentsQuery.data.value ?? [])
const failed = computed(() => commentsQuery.isError.value)
// Badge count: server COUNT(*) when available, else loaded thread length.
const badgeCount = computed(
  () => countQuery.data.value ?? (expanded.value ? comments.value.length : 0),
)

async function send() {
  const content = draft.value.trim()
  if (!content || createMutation.isPending.value) {
    return
  }
  await createMutation.mutateAsync({ activityId: props.activityId, content })
  draft.value = ''
}

function toggle() {
  expanded.value = !expanded.value
}
</script>

<template>
  <div class="border-t pt-2" @click.stop>
    <Button variant="ghost" size="sm" class="gap-1 px-1" @click="toggle">
      <MessageCircle class="size-4" />
      <span v-if="badgeCount > 0">
        {{ t('activities.comments.count', badgeCount) }}
      </span>
      <span v-else>{{ t('activities.comments.toggle') }}</span>
      <component :is="expanded ? ChevronUp : ChevronDown" class="size-4" />
    </Button>

    <template v-if="expanded">
      <div v-if="commentsQuery.isPending.value" class="mt-2 flex flex-col gap-2">
        <Skeleton class="h-8 w-full" />
        <Skeleton class="h-8 w-full" />
      </div>
      <p v-else-if="failed" class="text-caption mt-2 text-red-500">
        {{ t('activities.comments.loadFailed') }}
      </p>
      <template v-else>
        <p v-if="comments.length === 0" class="text-caption mt-2">
          {{ t('activities.comments.empty') }}
        </p>
        <div v-else class="mt-2 flex flex-col gap-3">
          <ActivityCommentItem
            v-for="comment in comments"
            :key="comment.id"
            :comment="comment"
            :activity-id="props.activityId"
            :activity-owner-id="props.activityOwnerId"
          />
        </div>
        <div class="mt-2 flex gap-2">
          <Input
            v-model="draft"
            :placeholder="t('activities.comments.placeholder')"
            maxlength="2000"
            @keydown.enter="send"
          />
          <Button
            size="sm"
            :disabled="!draft.trim() || createMutation.isPending.value"
            @click="send"
          >
            {{ t('activities.comments.send') }}
          </Button>
        </div>
      </template>
    </template>
  </div>
</template>
