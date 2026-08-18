<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown } from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { INTEGRATION_LOGOS } from '@/constants/integrationLogos'
import { useToasts } from '@/composables/useToasts'
import {
  useImportStravaActivitiesMutation,
  useImportStravaBikesMutation,
  useImportStravaShoesMutation,
} from '@/features/import/composables/useImport'

const { t } = useI18n()
const toasts = useToasts()

const activitiesMutation = useImportStravaActivitiesMutation()
const bikesMutation = useImportStravaBikesMutation()
const shoesMutation = useImportStravaShoesMutation()

const isPending = computed(
  () =>
    activitiesMutation.isPending.value ||
    bikesMutation.isPending.value ||
    shoesMutation.isPending.value,
)

function importActivities(): void {
  activitiesMutation.mutate(undefined, {
    onSuccess: () => toasts.info(t('settings.import.strava.activitiesQueued')),
    onError: () => toasts.error(t('settings.import.strava.activitiesError')),
  })
}

function importBikes(): void {
  bikesMutation.mutate(undefined, {
    onSuccess: () => toasts.success(t('settings.import.strava.bikesSuccess')),
    onError: () => toasts.error(t('settings.import.strava.bikesError')),
  })
}

function importShoes(): void {
  shoesMutation.mutate(undefined, {
    onSuccess: () => toasts.success(t('settings.import.strava.shoesSuccess')),
    onError: () => toasts.error(t('settings.import.strava.shoesError')),
  })
}
</script>

<template>
  <Card class="flex flex-wrap items-center justify-between gap-3">
    <div class="flex min-w-0 items-center gap-3">
      <img
        :src="INTEGRATION_LOGOS.stravaMark"
        :alt="t('settings.import.strava.title')"
        class="size-10 shrink-0 object-contain rounded"
      />
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <h2 class="text-card-heading">{{ t('settings.import.strava.title') }}</h2>
          <Badge variant="secondary">{{ t('settings.import.beta') }}</Badge>
        </div>
        <p class="text-hint">{{ t('settings.import.strava.subtitle') }}</p>
      </div>
    </div>

    <DropdownMenu>
      <DropdownMenuTrigger as-child>
        <Button variant="outline" size="sm" :disabled="isPending">
          {{ t('settings.import.strava.import') }}
          <ChevronDown class="size-4" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" class="w-56">
        <DropdownMenuItem @select="importActivities">
          {{ t('settings.import.strava.activities') }}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem @select="importBikes">
          {{ t('settings.import.strava.bikes') }}
        </DropdownMenuItem>
        <DropdownMenuItem @select="importShoes">
          {{ t('settings.import.strava.shoes') }}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </Card>
</template>
