/// <reference types="vite/client" />

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
    ENDURAIN_HOST?: string
  }
}

declare module '@fontsource-variable/inter'
