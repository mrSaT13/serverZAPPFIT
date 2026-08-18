/**
 * Numeric form-field helpers — pure, framework-free, and shared by every form
 * that edits optional numeric fields (gear distance/value, component wear
 * thresholds, future health/goal forms). Centralised so the `<input
 * type="number">` coercion quirk is handled in exactly one tested place.
 */

/**
 * Parses an optional numeric field value, treating blank or invalid input as
 * `null`.
 *
 * A `<input type="number">` bound with `v-model` yields a `number` for valid
 * entries (and `''` when blank), while a plain text field yields a `string`, so
 * both shapes are accepted. Non-finite results (`NaN`, `Infinity`) collapse to
 * `null` rather than reaching the backend.
 *
 * @param value - The raw field value, as a `string` or `number`.
 * @returns The finite parsed number, or `null` when blank or unparseable.
 */
export function toNumberOrNull(value: string | number): number | null {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return null
  }
  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : null
}
