import { readdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

/**
 * Guards against locale drift: every non-English locale folder must carry the
 * same set of namespace files as the English source of truth, so a new feature
 * namespace can't ship translated for some locales and missing for others.
 */
const localesDir = resolve(dirname(fileURLToPath(import.meta.url)), '../i18n/locales')

/**
 * Lists the JSON namespace files in a locale folder, sorted for a stable,
 * order-independent comparison.
 *
 * @param locale - Locale folder name.
 * @returns Sorted namespace file names.
 */
function namespaceFiles(locale: string): string[] {
  return readdirSync(resolve(localesDir, locale))
    .filter((file) => file.endsWith('.json'))
    .sort()
}

const englishFiles = namespaceFiles('en')
const otherLocales = readdirSync(localesDir, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && entry.name !== 'en')
  .map((entry) => entry.name)
  .sort()

describe('i18n locale parity', () => {
  it('has English namespace files and non-English locales to check', () => {
    expect(englishFiles.length).toBeGreaterThan(0)
    expect(otherLocales.length).toBeGreaterThan(0)
  })

  it.each(otherLocales)('locale "%s" carries every English namespace file', (locale) => {
    expect(namespaceFiles(locale)).toEqual(englishFiles)
  })
})
