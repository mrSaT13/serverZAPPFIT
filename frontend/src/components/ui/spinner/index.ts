import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Spinner } from './Spinner.vue'

/** Size scale for the {@link Spinner} glyph. */
export const spinnerVariants = cva('animate-spin text-current', {
  variants: {
    size: {
      sm: 'size-4',
      md: 'size-6',
      lg: 'size-8',
    },
  },
  defaultVariants: {
    size: 'md',
  },
})

export type SpinnerVariants = VariantProps<typeof spinnerVariants>
