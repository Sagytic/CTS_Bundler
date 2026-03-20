/**
 * Stable key for a set of TRs (order-independent).
 * @param {string[]} trkorrs
 */
export function deployBatchKey(trkorrs) {
  if (!trkorrs?.length) return '';
  return [...new Set(trkorrs.map(String))].sort().join('|');
}

/**
 * @typedef {{ markdown: string, updatedAt: number, trkorrs: string[] }} DeployReportEntry
 * @param {string} trkorr
 * @param {Record<string, DeployReportEntry>} reportsMap
 * @returns {DeployReportEntry | null}
 */
export function findLatestDeployReportForTr(trkorr, reportsMap) {
  const id = String(trkorr || '').trim();
  if (!id || !reportsMap || typeof reportsMap !== 'object') return null;
  const candidates = Object.values(reportsMap).filter(
    (e) => e && Array.isArray(e.trkorrs) && e.trkorrs.includes(id) && e.markdown,
  );
  if (candidates.length === 0) return null;
  candidates.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  return candidates[0];
}
