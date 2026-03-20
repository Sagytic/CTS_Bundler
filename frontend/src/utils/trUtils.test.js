import { describe, it, expect } from 'vitest'
import { formatTime, filterMainTransports, getTrObjectsTree } from './trUtils'

describe('trUtils', () => {
  describe('formatTime', () => {
    it('formats 6-char time string to HH:MM:SS', () => {
      expect(formatTime('123456')).toBe('12:34:56')
    })
    it('returns original if not 6 chars', () => {
      expect(formatTime('12345')).toBe('12345')
      expect(formatTime('')).toBe('')
    })
    it('returns original if null/undefined', () => {
      expect(formatTime(null)).toBeNull()
      expect(formatTime(undefined)).toBeUndefined()
    })
  })

  describe('filterMainTransports', () => {
    it('keeps only K and W trfunction', () => {
      const transports = [
        { TRFUNCTION: 'K', TRKORR: 'N1' },
        { trfunction: 'w', trkorr: 'N2' },
        { TRFUNCTION: 'T', TRKORR: 'N3' },
        { trfunction: 'k', trkorr: 'N4' },
      ]
      expect(filterMainTransports(transports)).toHaveLength(3)
      expect(filterMainTransports(transports).map((t) => t.TRKORR || t.trkorr)).toEqual(['N1', 'N2', 'N4'])
    })
    it('returns empty array for empty input', () => {
      expect(filterMainTransports([])).toEqual([])
    })
  })

  describe('getTrObjectsTree', () => {
    it('groups objects by type for parent + children TRs', () => {
      const rawTrData = [
        { TRKORR: 'N1', objects: [{ object: 'PROG', obj_name: 'ZP1' }, { object: 'TABL', obj_name: 'ZT1' }] },
        { STRKORR: 'N1', objects: [{ object: 'PROG', obj_name: 'ZP2' }] },
      ]
      const tree = getTrObjectsTree('N1', rawTrData)
      expect(tree.PROG).toEqual(new Set(['ZP1', 'ZP2']))
      expect(tree.TABL).toEqual(new Set(['ZT1']))
    })
    it('handles OBJECT/OBJ_NAME casing', () => {
      const rawTrData = [{ TRKORR: 'N1', OBJECTS: [{ OBJECT: 'CLAS', OBJ_NAME: 'ZC1' }] }]
      const tree = getTrObjectsTree('N1', rawTrData)
      expect(tree.CLAS).toEqual(new Set(['ZC1']))
    })
    it('returns empty grouped object when parent not found', () => {
      const tree = getTrObjectsTree('NONE', [{ TRKORR: 'N1' }])
      expect(tree).toEqual({})
    })
  })
})
