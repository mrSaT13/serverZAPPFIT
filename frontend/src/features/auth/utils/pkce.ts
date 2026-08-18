/**
 * Generates a cryptographically random PKCE code verifier.
 *
 * @returns Base64url-encoded verifier.
 */
export function generateCodeVerifier(): string {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  return base64UrlEncode(bytes)
}

/**
 * Generates a PKCE S256 code challenge.
 *
 * @param verifier - PKCE code verifier.
 * @returns Base64url-encoded SHA-256 challenge.
 */
export async function generateCodeChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return base64UrlEncode(new Uint8Array(hash))
}

/**
 * Encodes bytes as base64url.
 *
 * @param bytes - Bytes to encode.
 * @returns Base64url string.
 */
function base64UrlEncode(bytes: Uint8Array): string {
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}
