import type { FormattedMetric } from './format'

/** The four headline metric columns shown in the activities list. */
export type ActivityMetricKey = 'distance' | 'duration' | 'paceSpeed' | 'elevation'

/** A headline metric column definition for the activities list. */
export interface ActivityMetricColumn {
  /** Stable key, used to look up the row's formatted value. */
  key: ActivityMetricKey
  /** i18n key for the column header label. */
  labelKey: string
  /**
   * Shared width + alignment + responsive-visibility classes. The SAME class
   * string is applied to the column header cell (in `ActivitiesView`) and to
   * every row's value cell (in `ActivityListItem`) so the columns line up
   * exactly; keep the two call sites in sync via this single source.
   */
  cellClass: string
}

/**
 * The activities-list metric columns, in display order. Distance and duration
 * are always visible (from the `sm` breakpoint up); pace/speed appears from
 * `md` and elevation from `lg`, so narrower panels progressively drop the
 * least-critical columns without shifting the rest.
 */
export const ACTIVITY_METRIC_COLUMNS: readonly ActivityMetricColumn[] = [
  { key: 'distance', labelKey: 'activities.list.columns.distance', cellClass: 'w-24 text-right' },
  { key: 'duration', labelKey: 'activities.list.columns.duration', cellClass: 'w-20 text-right' },
  {
    key: 'paceSpeed',
    labelKey: 'activities.list.columns.paceSpeed',
    cellClass: 'hidden w-32 text-right md:block',
  },
  {
    key: 'elevation',
    labelKey: 'activities.list.columns.elevation',
    cellClass: 'hidden w-16 text-right lg:block',
  },
]

/** Placeholder metric for a column that does not apply to an activity. */
export const NA_METRIC: FormattedMetric = { value: '--', unit: '' }
