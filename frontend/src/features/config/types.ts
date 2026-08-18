import type { LocaleCode } from '@/i18n'
import type { Schemas } from '@/types'

/**
 * Instance-level feature flags. Drive conditional UI from these instead of
 * hard-coded `import.meta.env` checks so one bundle serves every deployment.
 *
 * @property signUp - Whether self-service sign-up is enabled.
 * @property strava - Whether the Strava integration is available.
 * @property garmin - Whether the Garmin integration is available.
 * @property federation - Whether federated (multi-instance) features are on.
 */
export interface FeatureFlags {
  signUp: boolean
  strava: boolean
  garmin: boolean
  federation: boolean
}

/**
 * Per-instance branding, overridable by hosted/private deployments.
 *
 * @property appName - Display name shown in the UI shell.
 */
export interface BrandingConfig {
  appName: string
}

/**
 * Runtime application configuration resolved at boot from the public server
 * settings. Never read deployment-specific values from `import.meta.env` in
 * views.
 *
 * @property features - Enabled feature flags.
 * @property branding - Branding overrides.
 * @property enabledLocales - Locales the instance exposes, or `null` for all
 *   compiled-in locales.
 */
export interface AppConfig {
  features: FeatureFlags
  branding: BrandingConfig
  enabledLocales: LocaleCode[] | null
}

/**
 * Public settings used by unauthenticated auth screens. Narrowed from the
 * backend's `ServerSettingsReadPublic` to only the fields these screens use,
 * so the field names/types track the backend contract while the default stays
 * small. Widen the `Pick` as more public settings are consumed.
 *
 * @property login_photo_set - Whether the instance has a custom login image.
 * @property signup_enabled - Whether sign-up should be offered.
 * @property sso_enabled - Whether SSO login is enabled.
 * @property local_login_enabled - Whether username/password login is enabled.
 * @property sso_auto_redirect - Whether to redirect automatically when a single SSO provider exists.
 * @property units - Default unit system used to seed the sign-up form.
 * @property currency - Default currency used to seed the sign-up form.
 * @property password_type - Password policy enforcement level for client-side hints.
 * @property password_length_regular_users - Minimum password length for regular users.
 * @property password_length_admin_users - Minimum password length for admin users.
 * @property num_records_per_page - Page size the server enforces for paginated lists.
 */
export type PublicServerSettings = Pick<
  Schemas['ServerSettingsReadPublic'],
  | 'login_photo_set'
  | 'signup_enabled'
  | 'sso_enabled'
  | 'local_login_enabled'
  | 'sso_auto_redirect'
  | 'units'
  | 'currency'
  | 'password_type'
  | 'password_length_regular_users'
  | 'password_length_admin_users'
  | 'num_records_per_page'
>
