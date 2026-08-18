import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Badge } from './Badge.vue'

export const badgeVariants = cva(
  'inline-flex items-center rounded border px-2 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        destructive: 'border-destructive/20 bg-destructive/10 text-destructive',
        warning: 'border-effort/40 bg-effort/10 text-effort',
        info: 'border-info/40 bg-info/10 text-info',
        outline: 'border-input bg-transparent text-foreground',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)
export type BadgeVariants = VariantProps<typeof badgeVariants>
