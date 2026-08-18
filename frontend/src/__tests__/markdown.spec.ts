import { describe, expect, it } from 'vitest'

import { renderMarkdown } from '@/utils/markdown'

describe('renderMarkdown', () => {
  it('renders common markdown to HTML', () => {
    const html = renderMarkdown('# Title\n\n**bold** and *italic*\n\n- one\n- two')
    expect(html).toContain('<h1>Title</h1>')
    expect(html).toContain('<strong>bold</strong>')
    expect(html).toContain('<em>italic</em>')
    expect(html).toContain('<li>one</li>')
    expect(html).toContain('<li>two</li>')
  })

  it('strips script tags and event handlers (XSS-safe)', () => {
    const html = renderMarkdown('hello <script>alert(1)</script> <img src=x onerror=alert(1)>')
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('onerror')
    expect(html).toContain('hello')
  })

  it('forces links to open safely in a new tab', () => {
    const html = renderMarkdown('[endurain](https://example.com)')
    expect(html).toContain('href="https://example.com"')
    expect(html).toContain('target="_blank"')
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('returns an empty string for nullish or empty input', () => {
    expect(renderMarkdown('')).toBe('')
    expect(renderMarkdown(null)).toBe('')
    expect(renderMarkdown(undefined)).toBe('')
  })
})
