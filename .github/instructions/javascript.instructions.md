---
description: 'Vue.js 3 + TypeScript + Tailwind CSS v4 + shadcn-vue coding standards, architecture patterns, and pre-commit requirements for the Endurain frontend'
applyTo: '**/*.ts,**/*.js,**/*.vue'
---
# Project Context
- **Framework:** Vue.js 3 with TypeScript (`<script setup lang="ts">`)
- **Build Tool:** Vite (`vue-tsc` type-check + build)
- **UI Framework:** Tailwind CSS v4 (`@theme` tokens in `src/assets/main.css`) + shadcn-vue / reka-ui primitives
- **State:** Pinia (setup stores) for client state, TanStack Query (`@tanstack/vue-query`) for server state
- **Additional Libraries:** vue-router, vue-i18n (lazy locales), `@lucide/vue` icons, Chart.js (charts), Leaflet (maps), DOMPurify, marked
- **Testing:** Vitest + `@vue/test-utils`
- **Project Structure:** Feature-based modules under `frontend/src/features/<feature>/`; shared primitives in `frontend/src/components/`

# Development Setup
- **Navigate:** `cd frontend`
- **Install dependencies:** `npm install`
- **Dev server:** `npm run dev` (port 5173, or 5174 if occupied)
- **Build:** `npm run build` (runs `type-check` then production build)
- **Test:** `npm run test` (once) / `npm run test:unit` (watch) / `npm run test:coverage` (coverage gate)
- **Lint:** `npm run lint` (oxlint + ESLint, `--fix`) / `npm run lint:check`
- **Format:** `npm run format` (Prettier) / `npm run format:check`
- **Full gate:** `npm run check` (type-check + lint:check + format:check + test) — run before pushing
- **Regenerate typed API client:** `npm run gen:api` after backend API changes

# TypeScript Standards

## Modern Type Inference
- Always use `<script setup lang="ts">` syntax
- Use `ref<T>()` with generic parameter: 
  `const user = ref<User | null>(null)`
- **AVOID** redundant `Ref<T>` annotations: 
  ~~`const user: Ref<User | null> = ref(null)`~~
- Let TypeScript infer types when obvious: 
  `const count = ref(0)` (infers `Ref<number>`)
- Let `computed()` infer return types from callback
- **AVOID** redundant `ComputedRef<T>` annotations

## Type Safety
- Explicit typing for function parameters and return types
- Type imports for complex types: `Router`, 
  `RouteLocationNormalizedLoaded`
- No implicit `any` types
- Centralized imports from `/types/index.ts`

# Documentation Standards

## General Rules

- **Follow JSDoc format** — use standard `/** ... */` block comments.  
- **Always include `@param`, `@returns`, and `@throws`** sections — even when parameters or behavior seem obvious.  
- **Do not include examples** inside docstrings — keep them in external documentation or test cases.  
- **Avoid extended explanations** — use a single summary line followed by concise sections.  
- **Keep comments concise and descriptive** — explain *what* the code does, not *how* it does it.  
- **Use Markdown formatting** (`code`, *italic*, **bold**) inside comments for clarity.  

## Function Documentation

```ts
/**
 * Adds two numbers together.
 *
 * @param a - The first number.
 * @param b - The second number.
 * @returns The sum of `a` and `b`.
 */
function add(a: number, b: number): number {
  return a + b;
}
```

## Class Documentation

Guidelines:

- Document the class itself with a one-line summary.
- Each public method and property should have its own concise JSDoc block.
- Avoid documenting private members unless needed for internal tooling or generated docs.

```ts
/**
 * Represents a user in the system.
 *
 * @remarks
 * Keep descriptions brief; focus on what the class represents or provides.
 */
class User {
  /**
   * Creates a new user instance.
   *
   * @param name - The user’s display name.
   */
  constructor(public name: string) {}

  /**
   * Returns a greeting for the user.
   *
   * @returns A personalized greeting message.
   */
  greet(): string {
    return `Hello, ${this.name}`;
  }
}
```

## Interface / Type Documentation

Guidelines:

- Document each property using @property.
- Avoid repeating type information already in code.
- Keep to one concise sentence per property.

```ts
/**
 * Describes a basic user profile.
 *
 * @property id - Unique identifier for the user.
 * @property name - Full name of the user.
 * @property isAdmin - Whether the user has administrative privileges.
 */
interface UserProfile {
  id: string;
  name: string;
  isAdmin: boolean;
}
```

## Variable / Constant Documentation

Guidelines:

- Use single-line comments for constants or simple variables.
- If a variable is complex or derived, use a full JSDoc block with a one-line summary and @type if helpful.

```ts
/** The maximum number of users allowed in the system. */
const MAX_USERS = 100;
```

# Architecture

## Feature Modules (`src/features/<feature>/`)
- Self-contained modules (e.g. `activities`, `auth`, `health`, `profile`, `settings`)
- Each may contain `components/`, `composables/`, `services/`, `stores/`, `views/`, `utils/`, and `types.ts`
- Keep feature code inside its module; promote to shared `src/` folders only when reused across features

## Typed API Client (`src/types/api.generated.ts`)
- Generated from the backend OpenAPI schema and **committed**; never hand-edit
- Derive API-boundary DTOs via the `Schemas` helper in `src/types/index.ts` so backend contract changes surface as TypeScript errors
- Regenerate with `npm run gen:api` after backend API changes

## Server State (TanStack Query)
- Use `@tanstack/vue-query` composables for all server data — loading/error/success are handled by the query
- Query keys come from the central factories in `src/services/queryKeys.ts`
- HTTP goes through `src/services/http.ts` (timeouts, auth, CSRF); never call `fetch` directly in components
- Use `useInvalidatingMutation` for writes that must refresh cached queries

## Client State (Pinia)
- Setup-style stores for UI/client state only — never store tokens or server-owned data

## Shared UI (`src/components/`)
- shadcn-vue / reka-ui primitives live in `src/components/ui/`; layout in `src/components/layout/`
- Compose existing primitives; do not re-implement them

## Cross-cutting Composables (`src/composables/`)
- `useForm` (form state + validation), `useToasts` (notifications), `useTheme`, `useLocale`, `useNavigation`
- `useChartProvider` / `useMapProvider` wrap Chart.js / Leaflet behind a seam
- `useSafeRedirect` for validated redirects, `useTelemetry` for safe logging

## Config
- Read deployment config from the app config / public server settings, never from `import.meta.env` in views

# UI/UX Standards

## Styling (Tailwind CSS v4 + shadcn-vue)
- Build UI from shadcn-vue / reka-ui primitives in `src/components/ui/`; do not re-implement them
- Style with Tailwind utility classes; avoid scoped CSS for what a utility already covers
- Use the `cn()` helper (`src/lib/utils.ts`, clsx + tailwind-merge) for conditional/merged classes
- Use semantic design tokens, not raw colors: `text-muted-foreground` for muted text, `bg-muted` for surfaces, `bg-background`/`text-foreground`, `bg-primary`/`text-primary-foreground`
- Brand/design tokens live in `@theme` in `src/assets/main.css` — never hardcode hex values outside data-viz
- Avoid arbitrary values (`w-[123px]`) except genuine one-off dimensional layout

## Design System (brand, typography, primitives)
**Full guide:** [Brand & UX guidelines](../../docs/developer-guide/brand-and-ux-guidelines.md). `frontend/src/assets/main.css` is the single source of truth for tokens.
- **Philosophy:** data-dense, flat & calm (no card shadows — use `border border-border`; no gradients), dark-mode-first, numbers are the hero
- **Brand accents** (data-viz / semantic only): `text-hr`, `text-effort`, `text-info`, `text-goal`, `bg-brand`/`text-brand`; activity colors come from `ActivityTypeBadge`, never hand-rolled
- **Typography:** font is Inter (weights **400/500 only**, never 600/700). Apply type via the semantic utilities — `text-page-title`, `text-card-heading`, `text-section-heading`, `text-item-title`, `text-body`, `text-caption`, `text-hint`, `text-field-error`, and size-only `text-display`/`text-metric`/`text-meta`/`text-micro` — instead of ad-hoc `text-[..]`. Sentence case headings, never Title Case
- **Primitives:** compose the Endurain primitives (`MetricPill`, `ActivityTypeBadge`, `EmptyState`, …) from `src/components/ui/`; don't reinvent them
- **Dark mode:** driven by the `dark` class on `<html>` via `useTheme`. Prefer semantic tokens (they auto-flip — most components need no `dark:`); for teal on dark surfaces use `dark:text-brand-dark-foreground` / `dark:bg-brand-dark-surface`
- **Radii:** `rounded-card` (12px), `rounded-input` (8px), `rounded-badge` (20px)

## Accessibility Requirements
- **ARIA labels:** All interactive elements must have 
  `aria-label`
- **Live regions:** Use `aria-live="polite"` for validation 
  messages
- **Keyboard navigation:** Ensure full keyboard navigation
- **Focus management:** Visible and consistent focus outlines
- **Screen readers:** Test with NVDA/VoiceOver

## Responsive Design
- Support mobile, tablet, and desktop viewports
- Test across different screen sizes
- Use Tailwind responsive variants (`sm:`, `md:`, `lg:`, `xl:`)

## User Feedback
- Always include loading states for async operations
- Graceful error handling with user-friendly messages
- Clear validation feedback
- Surface notifications via `useToasts`; render rich/HTML content through `SafeHtml.vue` (DOMPurify)

# Composition API Patterns

- Create reusable composables for shared logic (e.g., `useForm`, `useToasts`, TanStack Query composables)
- Use `watch` and `watchEffect` with precise dependency lists
- Clean up side effects in `onUnmounted` or inside `watch` cleanup callbacks
- Use `provide`/`inject` sparingly — only for deep dependency injection where prop drilling is impractical
- Prefer `computed` over `watch` for derived state

# Performance

- Lazy-load components with dynamic imports and `defineAsyncComponent`
- Use `<Suspense>` for async component loading fallbacks
- Apply `v-once` for fully static content and `v-memo` for infrequently changing list items
- Avoid unnecessary watchers; prefer `computed` where possible

# Data Fetching

- Use TanStack Query (`@tanstack/vue-query`) for server state — it handles loading, error, success, caching, and cancellation
- Route requests through `src/services/http.ts`; key queries via `src/services/queryKeys.ts`
- Encapsulate query/mutation logic in feature composables to keep components clean
- Use `useInvalidatingMutation` so writes refresh the affected cached queries

# Routing

- Use `useRoute` and `useRouter` inside `<script setup>` for programmatic navigation
- Protect routes with navigation guards (`beforeEnter`, `beforeEach`)
- Use route meta fields for breadcrumbs, auth requirements, and similar cross-cutting data

# Error Handling

- Use the global error handler (`app.config.errorHandler`) for uncaught errors
- Use `errorCaptured` lifecycle hook in components to handle errors from child components locally
- Wrap risky async logic in `try/catch`; always display user-friendly messages
- Never expose raw error objects or stack traces in the UI

# Security (Frontend)

- **Never use `v-html`** with user-controlled data — render through `SafeHtml.vue` (`src/components/federation/SafeHtml.vue`, DOMPurify) instead
- Store sensitive tokens in HTTP-only cookies, not `localStorage` or `sessionStorage`
- Use HTTPS for all API requests
- Validate and escape data before rendering in templates or directives

# Reference Implementations

Study these as templates for new code:

- **`src/features/auth/`** — full feature module (views, composables, services, stores) covering login/MFA and password reset
- **`src/features/health/`** — large feature with TanStack Query CRUD composables and shadcn-vue dialogs
- **`src/components/ui/`** — shadcn-vue primitives to compose from
- **`src/composables/useForm.ts`** — form state and validation pattern
- **`src/components/federation/SafeHtml.vue`** — sanitized HTML rendering (DOMPurify)

# Pre-commit Checklist
- ✅ Run `npm run check` (type-check + lint:check + format:check + test) — the CI gate
- ✅ TypeScript types correct (no implicit `any`); typed API DTOs derived from `Schemas`
- ✅ Tests pass and cover new logic (Vitest)
- ✅ Accessibility attributes verified
- ✅ Uses feature modules, shared primitives, and central services (no duplicated utilities)
- ✅ Tailwind/shadcn-vue conventions followed (semantic tokens, `cn()`, no stray hex)
- ✅ Manual browser validation complete