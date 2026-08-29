import type { Severity } from '@/types'

/**
 * Maps a {@link Severity} to its token-based border/background/text classes.
 * Shared by the inline `Alert` component and the toast host so both render
 * severities from one source of truth.
 */
export const severityClasses: Record<Severity, string> = {
  info: 'border-info/50 bg-info/20 text-info',
  success: 'border-goal/50 bg-goal/20 text-goal',
  warning: 'border-effort/50 bg-effort/20 text-effort',
  error: 'border-hr/50 bg-hr/20 text-hr',
}

/**
 * Toast-specific classes — less transparent and tinted with the user's
 * chosen accent theme (`--accent` / `--primary`). The background is the
 * accent colour so every toast visibly follows the theme picker, while a
 * coloured left border preserves the severity semantics.
 */
export const toastAccentClasses: Record<Severity, string> = {
  info: 'border-primary/30 bg-accent/95 text-accent-foreground border-l-4 border-l-info shadow-xl backdrop-blur-md',
  success: 'border-primary/30 bg-accent/95 text-accent-foreground border-l-4 border-l-goal shadow-xl backdrop-blur-md',
  warning: 'border-primary/30 bg-accent/95 text-accent-foreground border-l-4 border-l-effort shadow-xl backdrop-blur-md',
  error: 'border-primary/30 bg-accent/95 text-accent-foreground border-l-4 border-l-hr shadow-xl backdrop-blur-md',
}
