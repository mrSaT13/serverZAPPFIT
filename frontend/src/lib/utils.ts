import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merges Tailwind utility classes, resolving conflicts deterministically.
 *
 * @param inputs - Class values to combine (strings, arrays, or conditionals).
 * @returns A single, de-duplicated class string.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
