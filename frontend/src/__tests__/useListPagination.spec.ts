import { describe, expect, it } from 'vitest'
import { nextTick, ref } from 'vue'

import { useListPagination } from '@/composables/useListPagination'

describe('useListPagination', () => {
  it('derives the total page count, rounding up and never below one', () => {
    const total = ref(0)
    const { totalPages } = useListPagination(ref(1), total, ref(25))

    expect(totalPages.value).toBe(1)
    total.value = 25
    expect(totalPages.value).toBe(1)
    total.value = 26
    expect(totalPages.value).toBe(2)
    total.value = 75
    expect(totalPages.value).toBe(3)
  })

  it('reset returns to the first page', () => {
    const page = ref(4)
    const { reset } = useListPagination(page, ref(100), ref(25))

    reset()
    expect(page.value).toBe(1)
  })

  it('clamps the current page when the total shrinks below it', async () => {
    const page = ref(4)
    const total = ref(100)
    useListPagination(page, total, ref(25))
    expect(page.value).toBe(4)

    total.value = 25
    await nextTick()
    expect(page.value).toBe(1)
  })

  it('guards against a zero page size', () => {
    const { totalPages } = useListPagination(ref(1), ref(50), ref(0))
    expect(totalPages.value).toBe(50)
  })
})
