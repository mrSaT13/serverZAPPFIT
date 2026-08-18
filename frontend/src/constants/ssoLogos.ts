import autheliaLogo from '@/assets/sso/authelia.svg'
import authentikLogo from '@/assets/sso/authentik.svg'
import casdoorLogo from '@/assets/sso/casdoor.svg'
import keycloakLogo from '@/assets/sso/keycloak.svg'
import pocketidLogo from '@/assets/sso/pocketid.svg'

/** Known SSO provider logos bundled with the app. */
export const PROVIDER_CUSTOM_LOGO_MAP: Record<string, string> = {
  authelia: autheliaLogo,
  authentik: authentikLogo,
  casdoor: casdoorLogo,
  keycloak: keycloakLogo,
  pocketid: pocketidLogo,
}
