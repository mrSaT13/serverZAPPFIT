/**
 * Module-level cache-busting token for avatar image URLs.
 *
 * Avatars are served from a stable path (e.g. `/user_images/1.png`), so a
 * freshly uploaded photo has the *same* URL as the old one and the browser
 * keeps showing the cached image until a full reload. Bumping this token after
 * a photo change makes {@link resolveAvatarUrl} append a new `?v=` query param,
 * which changes the `<img>` `src` and forces a re-fetch.
 */
let cacheToken = 0

/**
 * Invalidates cached avatar images so the next render re-fetches them. Call
 * after a profile photo is uploaded or replaced.
 */
export function bumpAvatarCacheToken(): void {
  cacheToken = Date.now()
}

/**
 * Returns the current avatar cache-busting token (`0` until the first photo
 * change, so initial URLs stay clean and cacheable).
 *
 * @returns The current token.
 */
export function getAvatarCacheToken(): number {
  return cacheToken
}
