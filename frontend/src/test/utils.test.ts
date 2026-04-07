import { describe, it, expect } from 'vitest'
import { cn, formatDate, healthBadgeClass } from '@/lib/utils'

describe('cn()', () => {
  it('joins class names', () => {
    expect(cn('a', 'b')).toBe('a b')
  })
  it('filters falsy values', () => {
    expect(cn('a', false && 'b', undefined, 'c')).toBe('a c')
  })
  it('handles empty call', () => {
    expect(cn()).toBe('')
  })
})

describe('formatDate()', () => {
  it('returns readable date string for ISO input', () => {
    const result = formatDate('2024-01-15T10:00:00Z')
    expect(result).toBeTruthy()
    expect(typeof result).toBe('string')
  })
  it('returns em-dash for empty input', () => {
    expect(formatDate('')).toBe('—')
  })
  it('handles invalid date gracefully', () => {
    const result = formatDate('not-a-date')
    expect(typeof result).toBe('string')
  })
})

describe('healthBadgeClass()', () => {
  it('returns green class for healthy', () => {
    expect(healthBadgeClass('healthy')).toContain('green')
  })
  it('returns yellow class for warning', () => {
    expect(healthBadgeClass('warning')).toContain('yellow')
  })
  it('returns red class for error', () => {
    expect(healthBadgeClass('error')).toContain('red')
  })
  it('returns gray for unknown status', () => {
    expect(healthBadgeClass('unknown')).toContain('gray')
  })
})
