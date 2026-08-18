/**
 * Versioned API path prefix shared by every backend HTTP and WebSocket route.
 * Single source of truth consumed by the runtime URL resolvers in
 * `@/services/runtime`; mirrors the backend `core_config.ROOT_PATH`.
 */
export const API_PATH = '/api/v1'
