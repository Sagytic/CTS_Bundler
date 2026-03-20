import { describe, it, expect } from 'vitest'
import { extractRefactoredCode } from './markdownUtils'

describe('markdownUtils', () => {
  describe('extractRefactoredCode', () => {
    it('returns last fenced code block', () => {
      const md = '```\nfirst\n```\n```abap\nREPORT z.\n```'
      expect(extractRefactoredCode(md)).toBe('REPORT z.')
    })
    it('returns empty for non-string', () => {
      expect(extractRefactoredCode(null)).toBe('')
      expect(extractRefactoredCode(undefined)).toBe('')
    })
  })
})
