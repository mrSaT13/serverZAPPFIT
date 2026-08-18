import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      exclude: [...configDefaults.exclude, 'e2e/**'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      coverage: {
        provider: 'v8',
        reporter: ['text-summary', 'html', 'lcov'],
        // Vitest v4 measures only files in the test import graph by default;
        // presentational components/views are validated separately and would
        // skew the floor, so they are intentionally not forced in.
        exclude: [
          'src/main.ts',
          'src/types/**',
          'src/**/*.generated.ts',
          'src/i18n/locales/**',
          'src/plugins/**',
        ],
        // Ratchet floor: set just below current so regressions fail CI while
        // minor refactors don't. Raise as coverage grows; never lower.
        thresholds: {
          statements: 60,
          branches: 60,
          functions: 50,
          lines: 60,
        },
      },
    },
  }),
)
