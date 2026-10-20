import { describe, expect, it } from 'vitest'
import { localDateString, mondayFor, shiftDate } from './date'

describe('localDateString', () => {
  it('formats a local calendar date without converting through UTC', () => {
    expect(localDateString(new Date(2026, 9, 19, 0, 5))).toBe('2026-10-19')
  })
})

describe('mondayFor', () => {
  it('returns the Monday for dates from Monday through Sunday', () => {
    expect(mondayFor('2026-10-19')).toBe('2026-10-19')
    expect(mondayFor('2026-10-25')).toBe('2026-10-19')
  })
})

describe('shiftDate', () => {
  it('shifts local calendar dates across month and year boundaries', () => {
    expect(shiftDate('2026-10-31', 1)).toBe('2026-11-01')
    expect(shiftDate('2026-01-01', -1)).toBe('2025-12-31')
  })
})
