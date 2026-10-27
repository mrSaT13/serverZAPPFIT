/// <reference types="vite/client" />

/** App version injected at build time from package.json (see vite.config.ts define). */
declare const __APP_VERSION__: string

interface ImportMetaEnv {
  /** Bootstrap origin for API calls (e.g. `/api/v1`). Defaults same-origin. */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  env?: {
    /** Runtime backend host injected by `/env.js`. */
    ZAPFIT_HOST?: string
    /** Legacy alias for backwards compatibility. */
    ENDURAIN_HOST?: string
  }
}

declare module '@fontsource-variable/inter'
