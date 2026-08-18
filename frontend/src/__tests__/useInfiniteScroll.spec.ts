import { effectScope, nextTick, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useInfiniteScroll } from '@/composables/useInfiniteScroll'

/**
 * Minimal `IntersectionObserver` stand-in: jsdom doesn't provide one, so the
 * composable is exercised by capturing the instance and driving its callback
 * by hand.
 */
class MockIntersectionObserver {
  static instances: MockIntersectionObserver[] = []

  readonly callback: IntersectionObserverCallback
  readonly options?: IntersectionObserverInit
  observe = vi.fn<(element: Element) => void>()
  unobserve = vi.fn<(element: Element) => void>()
  disconnect = vi.fn<() => void>()

  constructor(callback: IntersectionObserverCallback, options?: IntersectionObserverInit) {
    this.callback = callback
    this.options = options
    MockIntersectionObserver.instances.push(this)
  }

  /** Simulates the sentinel entering or leaving the viewport. */
  trigger(isIntersecting: boolean): void {
    this.callback(
      [{ isIntersecting } as IntersectionObserverEntry],
      this as unknown as IntersectionObserver,
    )
  }
}

describe('useInfiniteScroll', () => {
  beforeEach(() => {
    MockIntersectionObserver.instances = []
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('observes the target and fires onIntersect when it scrolls into view', async () => {
    const target = ref<HTMLElement | null>(document.createElement('div'))
    const onIntersect = vi.fn<() => void>()
    const scope = effectScope()
    scope.run(() => useInfiniteScroll(target, onIntersect))
    await nextTick()

    const observer = MockIntersectionObserver.instances[0]
    expect(observer).toBeDefined()
    expect(observer?.observe).toHaveBeenCalledWith(target.value)

    observer?.trigger(true)
    expect(onIntersect).toHaveBeenCalledTimes(1)

    scope.stop()
  })

  it('ignores intersections that are not actually visible', async () => {
    const target = ref<HTMLElement | null>(document.createElement('div'))
    const onIntersect = vi.fn<() => void>()
    const scope = effectScope()
    scope.run(() => useInfiniteScroll(target, onIntersect))
    await nextTick()

    MockIntersectionObserver.instances[0]?.trigger(false)
    expect(onIntersect).not.toHaveBeenCalled()

    scope.stop()
  })

  it('skips onIntersect while the enabled gate is closed', async () => {
    const target = ref<HTMLElement | null>(document.createElement('div'))
    const onIntersect = vi.fn<() => void>()
    const scope = effectScope()
    scope.run(() => useInfiniteScroll(target, onIntersect, { enabled: () => false }))
    await nextTick()

    MockIntersectionObserver.instances[0]?.trigger(true)
    expect(onIntersect).not.toHaveBeenCalled()

    scope.stop()
  })

  it('disconnects the observer when the scope is disposed', async () => {
    const target = ref<HTMLElement | null>(document.createElement('div'))
    const scope = effectScope()
    scope.run(() => useInfiniteScroll(target, vi.fn<() => void>()))
    await nextTick()

    const observer = MockIntersectionObserver.instances[0]
    scope.stop()
    expect(observer?.disconnect).toHaveBeenCalled()
  })
})
