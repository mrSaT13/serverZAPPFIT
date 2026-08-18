/**
 * Shared base styling for text-like and native form controls (text inputs,
 * selects, and native number inputs). Single source of truth so every field
 * renders with identical borders, padding, focus ring, and disabled states.
 */
export const inputFieldClass =
  'rounded-input border border-input bg-background px-3 py-2 text-body text-foreground outline-none transition-colors focus:border-ring focus:ring-3 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50'
