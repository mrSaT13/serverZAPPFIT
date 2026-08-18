import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Card } from './Card.vue'

/**
 * The single source of truth for card surfaces. The `padding` scale is the
 * canonical set of card paddings — prefer a named step over a hand-rolled
 * `p-*` so spacing can't drift across views:
 * - `none` — the card owns its inner spacing (e.g. list groups, split panels).
 * - `sm` — compact cards (`p-3`).
 * - `default` — the standard content card (`p-4`).
 * - `lg` — prominent surfaces such as auth screens (`p-6 sm:p-8`).
 */
export const cardVariants = cva('rounded-card border border-border bg-card', {
  variants: {
    padding: {
      none: '',
      sm: 'p-3',
      default: 'p-4',
      lg: 'p-6 sm:p-8',
    },
  },
  defaultVariants: {
    padding: 'default',
  },
})
export type CardVariants = VariantProps<typeof cardVariants>
