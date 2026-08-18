/**
 * Pragmatic email shape check: a non-empty local part, an `@`, and a dotted
 * domain. This is intentionally lenient — final validation is always the
 * backend's responsibility. Use it to gate UI affordances (e.g. enabling a
 * submit button), not as a security boundary.
 */
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * Returns whether the given value looks like a valid email address.
 *
 * @param value - Raw user input; surrounding whitespace is ignored.
 * @returns `true` when the trimmed value matches {@link EMAIL_PATTERN}.
 */
export function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim())
}

/**
 * Client-side password requirements used to gate the sign-up affordance. The
 * backend remains the authoritative validator; these checks only mirror the
 * server policy so the UI can give immediate feedback.
 *
 * @property minLength - Minimum password length.
 * @property requireUppercase - Whether an uppercase letter is required.
 * @property requireLowercase - Whether a lowercase letter is required.
 * @property requireDigit - Whether a digit is required.
 * @property requireSpecialChar - Whether a special character is required.
 */
export interface PasswordRequirements {
  minLength: number
  requireUppercase: boolean
  requireLowercase: boolean
  requireDigit: boolean
  requireSpecialChar: boolean
}

/** Special characters accepted by the backend password policy. */
const SPECIAL_CHAR_PATTERN = /[ !"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]/

/**
 * Translates the server's password policy into concrete client-side
 * requirements. The `strict` policy enforces character-class diversity; the
 * `length_only` policy enforces length alone.
 *
 * @param passwordType - Server password policy (`strict` or `length_only`).
 * @param minLength - Minimum password length from server settings.
 * @returns The resolved password requirements.
 */
export function buildPasswordRequirements(
  passwordType: string,
  minLength: number,
): PasswordRequirements {
  const strict = passwordType !== 'length_only'
  return {
    minLength,
    requireUppercase: strict,
    requireLowercase: strict,
    requireDigit: strict,
    requireSpecialChar: strict,
  }
}

/**
 * Returns whether a password meets the given requirements. Use it to gate the
 * sign-up submit affordance, not as a security boundary.
 *
 * @param password - Raw password input.
 * @param requirements - Requirements derived from the server policy.
 * @returns `true` when the password satisfies every requirement.
 */
export function isValidPassword(password: string, requirements: PasswordRequirements): boolean {
  if (password.length < requirements.minLength) {
    return false
  }
  if (requirements.requireUppercase && !/[A-Z]/.test(password)) {
    return false
  }
  if (requirements.requireLowercase && !/[a-z]/.test(password)) {
    return false
  }
  if (requirements.requireDigit && !/\d/.test(password)) {
    return false
  }
  return !(requirements.requireSpecialChar && !SPECIAL_CHAR_PATTERN.test(password))
}

/**
 * Picks the minimum password length for an account's access tier, mirroring
 * the backend's `resolve_password_min_length` (`auth/password_policy.py`) so
 * client-side hints/validation match what the server will actually enforce.
 *
 * @param regularLength - Minimum length configured for regular users.
 * @param adminLength - Minimum length configured for admin users.
 * @param accessType - The account's access type (`'admin'` or anything else).
 * @returns The minimum length that applies to `accessType`.
 */
export function resolvePasswordMinLength(
  regularLength: number,
  adminLength: number,
  accessType: string,
): number {
  return accessType === 'admin' ? adminLength : regularLength
}
