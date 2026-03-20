import { describe, it, expect } from 'vitest'
import { deployBatchKey, findLatestDeployReportForTr } from './deployReportStorage'

describe('deployReportStorage', () => {
  it('deployBatchKey is order-independent', () => {
    expect(deployBatchKey(['B', 'A', 'B'])).toBe('A|B')
  })

  it('findLatestDeployReportForTr picks newest by updatedAt', () => {
    const map = {
      'A|B': { markdown: 'old', updatedAt: 100, trkorrs: ['A', 'B'] },
      B: { markdown: 'new', updatedAt: 200, trkorrs: ['B'] },
    }
    expect(findLatestDeployReportForTr('B', map).markdown).toBe('new')
    expect(findLatestDeployReportForTr('A', map).markdown).toBe('old')
  })

  it('returns null when no match', () => {
    expect(findLatestDeployReportForTr('Z', { x: { markdown: 'm', updatedAt: 1, trkorrs: ['A'] } })).toBeNull()
  })
})
