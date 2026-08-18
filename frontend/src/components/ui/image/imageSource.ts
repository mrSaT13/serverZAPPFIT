/**
 * Image source seam. Every {@link Image} renders its `src`/`srcset` URLs
 * through this resolver so the way media is served can change per deployment
 * without touching any view: self-hosted instances serve activity media and
 * avatars directly (the default identity resolver), while hosted/SaaS
 * deployments register a resolver that rewrites URLs to a CDN, an image
 * transform proxy (resize/format), or a signed-URL issuer.
 *
 * This module ships no networking or transform logic — only the contract and
 * registration seam, matching the map/chart/telemetry provider seams.
 */
import { createProviderSeam } from '@/composables/createProviderSeam'

/**
 * Rewrites an image URL for the active deployment.
 *
 * @param src - The original image URL (absolute or app-relative).
 * @returns The URL to actually request.
 */
export type ImageSourceResolver = (src: string) => string

/** Default resolver: returns the URL unchanged (self-hosted, direct serving). */
const identityResolver: ImageSourceResolver = (src) => src

const seam = createProviderSeam<ImageSourceResolver>(identityResolver)

/**
 * Registers the active image source resolver. Call once during bootstrap on
 * deployments that serve media through a CDN or transform proxy.
 *
 * @param next - The resolver to install.
 */
export function setImageSourceResolver(next: ImageSourceResolver): void {
  seam.set(next)
}

/**
 * Resolves a single image URL through the active resolver.
 *
 * @param src - The original image URL.
 * @returns The rewritten URL (unchanged under the default resolver).
 */
export function resolveImageSource(src: string): string {
  return seam.get()(src)
}

/**
 * Resolves a `srcset` string, rewriting each candidate URL while preserving its
 * width/density descriptor (e.g. `"avatar.png 1x, avatar@2x.png 2x"`).
 *
 * @param srcset - The original `srcset` value.
 * @returns The `srcset` with every candidate URL resolved.
 */
export function resolveImageSrcset(srcset: string): string {
  return srcset
    .split(',')
    .map((candidate) => {
      const [url, ...descriptors] = candidate.trim().split(/\s+/)
      if (!url) {
        return ''
      }
      return [resolveImageSource(url), ...descriptors].join(' ')
    })
    .filter((candidate) => candidate.length > 0)
    .join(', ')
}
