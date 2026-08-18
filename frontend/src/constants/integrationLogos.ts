import stravaLight from '@/assets/strava/api_logo_cptblWith_strava_horiz_light.png'
import stravaMark from '@/assets/strava/stravaLogo.jpeg'
import garminConnectBadge from '@/assets/garminconnect/Garmin_connect_badge_print_RESOURCE_FILE-01.png'
import garminConnectApp from '@/assets/garminconnect/Garmin_Connect_app_1024x1024-02.png'

/**
 * Brand logos for third-party fitness integrations, resolved to hashed asset
 * URLs by Vite. Lucide ships no brand icons, so these are bundled as images.
 *
 * @property strava - "Compatible with Strava" horizontal logo (light bg).
 * @property stravaMark - The Strava "S" mark (square icon use).
 * @property garmin - "Works with Garmin Connect" badge.
 * @property garminApp - The Garmin Connect app icon (square icon use).
 */
export const INTEGRATION_LOGOS = {
  strava: stravaLight,
  stravaMark,
  garmin: garminConnectBadge,
  garminApp: garminConnectApp,
} as const
