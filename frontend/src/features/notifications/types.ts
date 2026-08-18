import type { Schemas } from '@/types'

/**
 * Raw `NotificationRead` payload from the backend. Snake-cased and nullable
 * fields mirror the API exactly; never consume this shape in components — map
 * it to {@link Notification} at the service boundary.
 */
export type NotificationDto = Schemas['NotificationRead']

/**
 * A notification as consumed by the app: a clean, camel-cased model decoupled
 * from the backend wire format so an API change is absorbed by the mapper
 * instead of rippling across the UI.
 *
 * @property id - Stable unique identifier.
 * @property type - Numeric notification type, or `null` when untyped.
 * @property read - Whether the notification has been read.
 * @property options - Arbitrary per-type metadata bag, or `null`.
 * @property createdAt - ISO creation timestamp, or `null` when absent.
 * @property userId - Owning user's id.
 */
export interface Notification {
  id: number
  type: number | null
  read: boolean
  options: Record<string, unknown> | null
  createdAt: string | null
  userId: number
}
