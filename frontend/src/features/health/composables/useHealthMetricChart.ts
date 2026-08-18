/**
 * Shared mount/update/teardown lifecycle for the health metric charts. Each
 * chart computes its own {@link ChartRenderOptions}; this composable owns the
 * container ref and drives the chart provider so the six metric charts collapse
 * to just their unique data shaping.
 */

import {
  onBeforeUnmount,
  onMounted,
  toValue,
  useTemplateRef,
  watch,
  type MaybeRefOrGetter,
} from 'vue'

import type { ChartInstance, ChartRenderOptions } from '@/composables/useChartProvider'

import { useChartProvider } from '@/composables/useChartProvider'
import { useRenderProvidersReady } from '@/providers'

/**
 * Drives a single metric chart's lifecycle: mounts it once the render provider
 * is ready and the container exists, re-renders on every render-option change,
 * and tears it down on unmount. The mount element is resolved from the
 * `chartContainer` template ref, so each chart only needs a single call plus a
 * `<div ref="chartContainer" />` in its template.
 *
 * @param render - The chart's reactive render options (a computed/getter).
 */
export function useHealthMetricChart(render: MaybeRefOrGetter<ChartRenderOptions>): void {
  const ready = useRenderProvidersReady()
  const container = useTemplateRef<HTMLElement>('chartContainer')
  let instance: ChartInstance | null = null

  /** Mounts the chart once the provider is ready and the container exists. */
  function mountChart(): void {
    if (instance || !container.value || !ready.value) {
      return
    }
    const { provider } = useChartProvider()
    instance = provider.mount(container.value, toValue(render))
  }

  onMounted(mountChart)
  watch(ready, mountChart)
  watch(
    () => toValue(render),
    (next) => {
      if (!instance) {
        mountChart()
        return
      }
      instance.update(next)
    },
  )

  onBeforeUnmount(() => {
    instance?.destroy()
    instance = null
  })
}
