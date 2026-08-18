import { isValidEmail } from './validation'

/**
 * A field validator: returns an error message when the value is invalid, or
 * `null` when it passes. Validators receive caller-supplied messages so the
 * framework stays i18n-agnostic — pass `t('...')` from the call site.
 *
 * @typeParam T - The field value type.
 */
export type Validator<T> = (value: T) => string | null

/**
 * Requires a non-empty value: rejects `null`/`undefined`, blank/whitespace
 * strings, and empty arrays.
 *
 * @typeParam T - The field value type.
 * @param message - Error message when the value is empty.
 * @returns A validator enforcing presence.
 */
export function required<T>(message: string): Validator<T> {
  return (value) => {
    if (value === null || value === undefined) {
      return message
    }
    if (typeof value === 'string' && value.trim().length === 0) {
      return message
    }
    if (Array.isArray(value) && value.length === 0) {
      return message
    }
    return null
  }
}

/**
 * Requires a string of at least `min` characters (after trimming).
 *
 * @param min - Minimum length.
 * @param message - Error message when too short.
 * @returns A string validator enforcing a minimum length.
 */
export function minLength(min: number, message: string): Validator<string> {
  return (value) => (value.trim().length < min ? message : null)
}

/**
 * Requires a string no longer than `max` characters (after trimming).
 *
 * @param max - Maximum length.
 * @param message - Error message when too long.
 * @returns A string validator enforcing a maximum length.
 */
export function maxLength(max: number, message: string): Validator<string> {
  return (value) => (value.trim().length > max ? message : null)
}

/**
 * Requires a syntactically valid email address. Empty values pass so this can
 * be combined with {@link required} when the field is mandatory.
 *
 * @param message - Error message when the value is not a valid email.
 * @returns A string validator enforcing email shape.
 */
export function email(message: string): Validator<string> {
  return (value) => (value.trim().length === 0 || isValidEmail(value) ? null : message)
}

/**
 * Requires the value to match a regular expression. Empty values pass so this
 * can be combined with {@link required}.
 *
 * @param regex - Pattern the value must match.
 * @param message - Error message when the value does not match.
 * @returns A string validator enforcing the pattern.
 */
export function pattern(regex: RegExp, message: string): Validator<string> {
  return (value) => (value.length === 0 || regex.test(value) ? null : message)
}

/**
 * Combines validators, returning the first failure (or `null` when all pass).
 * Order matters: list cheaper/foundational checks (e.g. `required`) first.
 *
 * @typeParam T - The field value type.
 * @param validators - Validators applied in order.
 * @returns A validator that short-circuits on the first error.
 */
export function compose<T>(...validators: Validator<T>[]): Validator<T> {
  return (value) => {
    for (const validate of validators) {
      const error = validate(value)
      if (error) {
        return error
      }
    }
    return null
  }
}
