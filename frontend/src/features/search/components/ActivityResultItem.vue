<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import type { Activity } from '@/features/activities/types'

import { ActivityTypeBadge } from '@/components/ui/activity-type-badge'
import { presentActivityType } from '@/features/activities/utils/activityType'

/**
 * One activity row in the search results: type icon, name, start date, and a
 * coloured type badge, linking to the activity detail view.
 */
const props = defineProps<{ activity: Activity }>()

const { t, locale } = useI18n()

const presentation = computed(() => presentActivityType(props.activity.activityType))

/** The localized start date, or `null` when the activity has no/invalid time. */
const dateLabel = computed(() => {
  if (!props.activity.startTime) {
    return null
  }
  const date = new Date(props.activity.startTime)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium' }).format(date)
})
</script>

<template>
  <RouterLink
    :to="{ name: 'activity', params: { id: activity.id } }"
    class="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/50"
  >
    <span
      class="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
    >
      <component :is="presentation.icon" class="size-5" aria-hidden="true" />
    </span>
    <div class="min-w-0 flex-1">
      <p class="truncate font-medium text-foreground">{{ activity.name }}</p>
      <p v-if="dateLabel" class="truncate text-hint">{{ dateLabel }}</p>
    </div>
    <ActivityTypeBadge :type="presentation.badge" :icon="presentation.icon" class="shrink-0">
      {{ t(presentation.labelKey) }}
    </ActivityTypeBadge>
  </RouterLink>
</template>
