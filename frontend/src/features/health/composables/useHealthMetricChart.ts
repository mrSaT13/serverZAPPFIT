/**
 * Feature-local alias of the shared {@link useMetricChart} lifecycle. Kept so
 * the six health metric charts' imports stay untouched; new features should
 * import the shared composable directly.
 */

export { useMetricChart as useHealthMetricChart } from '@/composables/useMetricChart'
