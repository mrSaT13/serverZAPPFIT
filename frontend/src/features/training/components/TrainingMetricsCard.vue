<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchTrainingMetrics, formLabel, type TrainingMetrics } from '@/features/training/services/pmc'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const metrics = ref<TrainingMetrics | null>(null)
const loading = ref(true)

onMounted(async () => {
  try { metrics.value = await fetchTrainingMetrics() } finally { loading.value = false }
})

function ctlLabel(v:number){ if(v<30) return 'База'; if(v<60) return 'Строит.'; if(v<100) return 'На пик'; return 'Высокая' }
</script>

<template>
  <Card class="flex flex-col gap-3">
    <h3 class="text-card-heading">Форма (PMC)</h3>
    <div v-if="loading" class="flex flex-col gap-2">
      <Skeleton class="h-6 w-32" />
      <Skeleton class="h-20 w-full" />
    </div>
    <template v-else-if="metrics">
      <div class="grid grid-cols-3 gap-2 text-center">
        <div class="rounded-input border p-2">
          <div class="text-hint">CTL (42д)</div>
          <div class="text-metric font-medium">{{ metrics.ctl.toFixed(1) }}</div>
          <div class="text-hint">{{ ctlLabel(metrics.ctl) }}</div>
        </div>
        <div class="rounded-input border p-2">
          <div class="text-hint">ATL (7д)</div>
          <div class="text-metric font-medium">{{ metrics.atl.toFixed(1) }}</div>
        </div>
        <div class="rounded-input border p-2" :class="formLabel(metrics.tsb).color">
          <div class="text-hint">TSB</div>
          <div class="text-metric font-medium">{{ metrics.tsb.toFixed(1) }}</div>
          <div class="text-hint">{{ formLabel(metrics.tsb).label }}</div>
        </div>
      </div>
      <div class="text-hint">TSS сегодня: {{ metrics.tssToday.toFixed(0) }}</div>
      <div class="flex gap-1 items-end h-12">
        <div v-for="p in metrics.points.slice(-30)" :key="p.date" class="flex-1 bg-primary/70 rounded-t" :style="{ height: (Math.min(p.tss,100)/100*48)+'px' }" :title="p.date + ': ' + p.tss" />
      </div>
      <div class="text-hint">30 дней TSS — высота до 100. CTL/ATL — экспоненциальное сглаживание.</div>
    </template>
  </Card>
</template>
