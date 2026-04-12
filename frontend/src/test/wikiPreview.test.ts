import { describe, expect, it } from 'vitest'
import { extractWikiPreview } from '@/lib/wikiPreview'

describe('extractWikiPreview', () => {
  it('strips frontmatter and markdown markers', () => {
    const raw = [
      '---',
      'topic: auth-design',
      '---',
      '',
      '# Auth Design',
      '',
      'Use `AuthService` with [[JWT Refresh]].',
    ].join('\n')

    expect(extractWikiPreview(raw)).toContain('Auth Design')
    expect(extractWikiPreview(raw)).toContain('AuthService')
    expect(extractWikiPreview(raw)).not.toContain('topic:')
    expect(extractWikiPreview(raw)).not.toContain('[[')
  })
})
