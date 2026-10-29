import { describe, expect, it } from 'vitest'

import type { CatalogExercise } from '@/features/strength/services/workouts'
import { catalogDescriptionText, catalogTextToPlain } from '@/features/strength/services/workouts'

function exercise(
  translations: Record<string, { name: string; description: string }>,
): CatalogExercise {
  return {
    wger_id: 1,
    uuid: 'u',
    name: 'Test',
    translations,
    category: { id: 1, name: 'Arms' },
    muscles: [],
    muscles_secondary: [],
    equipment: [],
  }
}

describe('catalogTextToPlain', () => {
  it('strips wger HTML paragraphs into readable text', () => {
    const input = '<p>Grab a barbell shoulder-width apart.</p>\n<p>Pause at the top.</p>\n'
    expect(catalogTextToPlain(input)).toBe(
      'Grab a barbell shoulder-width apart.\n\nPause at the top.',
    )
  })

  it('decodes common entities and normalizes br tags', () => {
    expect(catalogTextToPlain('<p>Push &amp; pull, 3&nbsp;sets<br>then rest</p>')).toBe(
      'Push & pull, 3 sets\nthen rest',
    )
  })
})

describe('catalogDescriptionText', () => {
  it('returns the requested language when available', () => {
    const ex = exercise({
      ru: { name: 'Сгибания', description: '<p>Сидя на скамье.</p>' },
      en: { name: 'Curl', description: '<p>Sit on a bench.</p>' },
    })
    expect(catalogDescriptionText(ex, 'ru')).toEqual({
      text: 'Сидя на скамье.',
      fellBackToEnglish: false,
    })
  })

  it('falls back to English (and flags it) when the UI language has no description', () => {
    const ex = exercise({
      ru: { name: 'Сгибания', description: '' },
      en: { name: 'Curl', description: '<p>Sit on a bench.</p>' },
    })
    expect(catalogDescriptionText(ex, 'ru')).toEqual({
      text: 'Sit on a bench.',
      fellBackToEnglish: true,
    })
  })

  it('returns null when neither language has a description', () => {
    const ex = exercise({ en: { name: 'Curl', description: '' } })
    expect(catalogDescriptionText(ex, 'ru')).toBeNull()
  })

  it('falls back to English even without any requested-language entry', () => {
    const ex = exercise({ en: { name: 'Curl', description: 'Plain text.' } })
    expect(catalogDescriptionText(ex, 'ru')).toEqual({
      text: 'Plain text.',
      fellBackToEnglish: true,
    })
  })
})
