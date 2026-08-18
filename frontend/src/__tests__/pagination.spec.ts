import { describe, expect, it } from 'vitest'

import { PAGINATION_ELLIPSIS, paginationItems } from '@/components/ui/pagination/pages'

describe('paginationItems', () => {
  it('lists every page without ellipsis when there are five or fewer', () => {
    expect(paginationItems(1, 1)).toEqual([1])
    expect(paginationItems(3, 5)).toEqual([1, 2, 3, 4, 5])
  })

  it('keeps the leading window near the start', () => {
    expect(paginationItems(1, 10)).toEqual([1, 2, 3, PAGINATION_ELLIPSIS, 10])
    expect(paginationItems(2, 10)).toEqual([1, 2, 3, PAGINATION_ELLIPSIS, 10])
  })

  it('keeps the trailing window near the end', () => {
    expect(paginationItems(10, 10)).toEqual([1, PAGINATION_ELLIPSIS, 8, 9, 10])
    expect(paginationItems(9, 10)).toEqual([1, PAGINATION_ELLIPSIS, 8, 9, 10])
  })

  it('brackets the current page with ellipses in the middle', () => {
    expect(paginationItems(5, 10)).toEqual([
      1,
      PAGINATION_ELLIPSIS,
      4,
      5,
      6,
      PAGINATION_ELLIPSIS,
      10,
    ])
  })
})
