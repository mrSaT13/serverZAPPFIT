import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as MetricPill } from './MetricPill.vue'

export const metricPillValueVariants = cva('text-metric font-medium leading-tight', {
  variants: {
    accent: {
      ink: 'text-foreground',
      hr: 'text-hr',
      effort: 'text-effort',
      info: 'text-info',
      goal: 'text-goal',
      brand: 'text-brand',
    },
  },
  defaultVariants: {
    accent: 'ink',
  },
})
export type MetricPillVariants = VariantProps<typeof metricPillValueVariants>
