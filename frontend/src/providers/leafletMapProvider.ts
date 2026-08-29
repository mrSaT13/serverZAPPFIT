/**
 * Concrete Leaflet implementation of the {@link MapProvider} seam. Registered
 * during bootstrap so Activity and Home surfaces can render GPS tracks. Kept
 * behind the seam so minimal builds can omit Leaflet entirely.
 *
 * The pure {@link toLatLngs} and {@link boundsOf} helpers are exported so the
 * seam → Leaflet data translation can be unit-tested without a real map.
 */
import { control, circleMarker, map as createMap, polyline, tileLayer, type Layer } from 'leaflet'
import 'leaflet/dist/leaflet.css'

import type {
  GeoPoint,
  MapInstance,
  MapProvider,
  MapRenderOptions,
  MapTrack,
} from '@/composables/useMapProvider'

import { themeColor } from '@/lib/themeColor'

/** A latitude/longitude pair in Leaflet's expected `[lat, lng]` order. */
export type LatLngTuple = [number, number]

/** Tile-server configuration for the Leaflet provider. */
export interface LeafletMapProviderConfig {
  /** Tile URL template (supports Leaflet's `{s}`, `{z}`, `{x}`, `{y}`). */
  tileUrl?: string
  /** Attribution HTML shown in the map corner. */
  attribution?: string
  /** Maximum zoom level offered by the tile server. */
  maxZoom?: number
  /** Polyline colour for the rendered track. */
  trackColor?: string
}

/** OpenStreetMap defaults, matching the backend's self-hosted server settings. */
const DEFAULT_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const DEFAULT_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
const DEFAULT_MAX_ZOOM = 19

/** Esri World Imagery — satellite layer, same as in mobile app (“Спутник”). */
const ESRI_SATELLITE_URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
const ESRI_ATTRIBUTION =
  'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community'
/** Brand teal track colour, from the `--color-brand` design token. */
const DEFAULT_TRACK_COLOR = themeColor('--color-brand')
/** Start-marker fill — the `--color-goal` design token (green). */
const START_MARKER_COLOR = themeColor('--color-goal')
/** Finish-marker fill — the `--color-hr` design token (red). */
const FINISH_MARKER_COLOR = themeColor('--color-hr')

/**
 * Converts seam {@link GeoPoint}s to Leaflet `[lat, lng]` tuples.
 *
 * @param points - Coordinates to convert.
 * @returns Tuples in Leaflet order.
 */
export function toLatLngs(points: readonly GeoPoint[]): LatLngTuple[] {
  return points.map((point) => [point.lat, point.lng])
}

/**
 * Computes the bounding box covering a track's points and markers.
 *
 * @param track - The track to bound.
 * @returns `[[south, west], [north, east]]`, or `null` when the track is empty.
 */
export function boundsOf(track: MapTrack): [LatLngTuple, LatLngTuple] | null {
  const points = [...track.points]
  if (track.start) {
    points.push(track.start)
  }
  if (track.finish) {
    points.push(track.finish)
  }
  const first = points[0]
  if (!first) {
    return null
  }

  let south = first.lat
  let north = first.lat
  let west = first.lng
  let east = first.lng
  for (const point of points) {
    south = Math.min(south, point.lat)
    north = Math.max(north, point.lat)
    west = Math.min(west, point.lng)
    east = Math.max(east, point.lng)
  }

  return [
    [south, west],
    [north, east],
  ]
}

/**
 * Builds a circular emphasis marker with a white border and coloured fill,
 * used for the start (green) and finish (red) points.
 *
 * @param point - The marker location.
 * @param color - The fill colour.
 * @returns A Leaflet circle-marker layer.
 */
function emphasisMarker(point: GeoPoint, color: string): Layer {
  return circleMarker([point.lat, point.lng], {
    radius: 7,
    color: '#ffffff',
    weight: 3,
    fillColor: color,
    fillOpacity: 1,
  })
}

/**
 * Creates a Leaflet-backed map provider.
 *
 * @param config - Optional tile-server overrides; defaults to OpenStreetMap.
 * @returns A {@link MapProvider} ready to register via `setMapProvider`.
 */
export function createLeafletMapProvider(config: LeafletMapProviderConfig = {}): MapProvider {
  const tileUrl = config.tileUrl ?? DEFAULT_TILE_URL
  const attribution = config.attribution ?? DEFAULT_ATTRIBUTION
  const maxZoom = config.maxZoom ?? DEFAULT_MAX_ZOOM
  const trackColor = config.trackColor ?? DEFAULT_TRACK_COLOR

  return {
    name: 'leaflet',
    mount(target: HTMLElement, options: MapRenderOptions): MapInstance {
      const interactive = options.interactive ?? true
      const map = createMap(target, {
        attributionControl: true,
        zoomControl: interactive,
        dragging: interactive,
        scrollWheelZoom: interactive,
        keyboard: interactive,
      })

      // Two base layers: OSM (default/configured) + Esri satellite.
      // Stored preference mirrors mobile app behaviour.
      const STORAGE_KEY = 'zapfit:mapLayer'
      let storedLayer: string | null = null
      try {
        storedLayer = localStorage.getItem(STORAGE_KEY)
      } catch {
        storedLayer = null
      }

      const isCustom = tileUrl !== DEFAULT_TILE_URL
      const osmLayer = tileLayer(tileUrl, { attribution, maxZoom })
      const satelliteLayer = tileLayer(ESRI_SATELLITE_URL, {
        attribution: ESRI_ATTRIBUTION,
        maxZoom: 19,
      })

      // Choose initial base layer (satellite if user picked it before and no custom tileserver).
      const initialIsSatellite = !isCustom && storedLayer === 'satellite'
      if (initialIsSatellite) {
        satelliteLayer.addTo(map)
      } else {
        osmLayer.addTo(map)
      }

      // Layer switcher control (only when interactive). Labels match mobile app.
      if (interactive) {
        const baseMaps: Record<string, Layer> = isCustom
          ? { 'Спутник (Esri)': satelliteLayer }
          : {
              'Карта': osmLayer,
              'Спутник (Esri)': satelliteLayer,
            }
        // When custom tileserver is set, keep it as default but still allow satellite.
        if (isCustom) {
          baseMaps['Карта (настроена)'] = osmLayer
        }
        control.layers(baseMaps, {}, { position: 'topleft', collapsed: true }).addTo(map)

        // Remember choice.
        map.on('baselayerchange', (e: { name: string }) => {
          try {
            if (e.name.includes('Спутник')) {
              localStorage.setItem(STORAGE_KEY, 'satellite')
            } else {
              localStorage.setItem(STORAGE_KEY, 'osm')
            }
          } catch {
            // ignore
          }
        })
      }

      let overlays: Layer[] = []
      let currentTrack: MapTrack = options.track

      /** Re-fits the viewport to a track's bounds (or the world when empty). */
      const fit = (track: MapTrack): void => {
        const bounds = boundsOf(track)
        if (bounds) {
          map.fitBounds(bounds, { padding: [24, 24] })
        } else {
          map.setView([0, 0], 2)
        }
      }

      const draw = (track: MapTrack): void => {
        currentTrack = track
        for (const layer of overlays) {
          map.removeLayer(layer)
        }
        overlays = []

        const linePoints = toLatLngs(track.points)
        if (linePoints.length > 0) {
          overlays.push(polyline(linePoints, { color: trackColor, weight: 4 }).addTo(map))
        }
        if (track.start) {
          overlays.push(emphasisMarker(track.start, START_MARKER_COLOR).addTo(map))
        }
        if (track.finish) {
          overlays.push(emphasisMarker(track.finish, FINISH_MARKER_COLOR).addTo(map))
        }

        fit(track)
      }

      draw(options.track)

      return {
        update(next: MapRenderOptions): void {
          draw(next.track)
        },
        recenter(): void {
          fit(currentTrack)
        },
        destroy(): void {
          map.remove()
        },
      }
    },
  }
}
