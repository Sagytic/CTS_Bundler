import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';

/** 자동 갱신 켰을 때 간격(ms). 너무 짧으면 백엔드 로그·부하가 잦아짐. */
const AUTO_REFRESH_MS = 60_000;

function formatNum(n) {
  if (n == null || Number.isNaN(n)) return '0';
  return Number(n).toLocaleString();
}

/** 표시용: Asia/Seoul (UTC+9) */
function formatKSTFromRow(row) {
  if (row?.ts_kst) return row.ts_kst;
  if (row?.ts != null) {
    const d = new Date(row.ts * 1000);
    if (!Number.isNaN(d.getTime())) {
      return new Intl.DateTimeFormat('sv-SE', {
        timeZone: 'Asia/Seoul',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      })
        .format(d)
        .replace(',', '');
    }
  }
  return '—';
}

export default function UsageDashboardTab() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  /** 기본 off: 대시보드 탭을 켜 둔 채로 두어도 API가 연속 호출되지 않음 */
  const [autoRefresh, setAutoRefresh] = useState(false);

  const load = useCallback(async () => {
    try {
      setError('');
      const res = await api.get('/api/usage-stats/');
      setData(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '불러오기 실패');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!autoRefresh) return undefined;

    const tick = () => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
        return;
      }
      load();
    };

    const id = setInterval(tick, AUTO_REFRESH_MS);
    const onVisibility = () => {
      if (document.visibilityState === 'visible') load();
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [autoRefresh, load]);

  const summary = data?.summary;
  const byOp = data?.by_operation || {};
  const recent = data?.recent || [];
  const opRows = Object.entries(byOp).sort((a, b) => (b[1].total_tokens || 0) - (a[1].total_tokens || 0));

  return (
    <div className="usage-dashboard">
      <div className="usage-dashboard-header">
        <div>
          <h1 className="usage-dashboard-title">Token Dashboard</h1>
          <p className="usage-dashboard-sub">
            사용량은 DB에 누적됩니다(서버 재시작 후에도 유지). 정확한 청구는 Azure Portal을 확인하세요.
            {' '}
            표시 시각은 모두 <strong>UTC+9 (KST)</strong> 기준입니다.
            {(data?.server_started_at_iso || data?.server_started_at_kst) && (
              <>
                {' '}
                · 최초 기록: {data.server_started_at_iso || `${data.server_started_at_kst} (UTC+9)`}
              </>
            )}
          </p>
        </div>
        <div className="usage-dashboard-actions">
          <label className="usage-dashboard-check">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            60초마다 자동 갱신(탭이 보일 때만)
          </label>
          <button type="button" className="usage-dashboard-btn" onClick={() => load()} disabled={loading}>
            새로고침
          </button>
        </div>
      </div>

      {error && <div className="usage-dashboard-error">{error}</div>}

      {loading && !data && <div className="usage-dashboard-muted">불러오는 중…</div>}

      {summary && (
        <div className="usage-dashboard-cards">
          <div className="usage-card">
            <div className="usage-card-label">총 호출</div>
            <div className="usage-card-value">{formatNum(summary.total_calls)}</div>
          </div>
          <div className="usage-card">
            <div className="usage-card-label">Prompt 토큰</div>
            <div className="usage-card-value">{formatNum(summary.total_prompt_tokens)}</div>
          </div>
          <div className="usage-card">
            <div className="usage-card-label">Completion 토큰</div>
            <div className="usage-card-value">{formatNum(summary.total_completion_tokens)}</div>
          </div>
          <div className="usage-card usage-card-accent">
            <div className="usage-card-label">합계 (추정)</div>
            <div className="usage-card-value">{formatNum(summary.total_tokens)}</div>
          </div>
        </div>
      )}

      {opRows.length > 0 && (
        <section className="usage-section">
          <h2>기능별 누적</h2>
          <div className="usage-table-wrap">
            <table className="usage-table">
              <thead>
                <tr>
                  <th>operation</th>
                  <th>호출</th>
                  <th>prompt</th>
                  <th>completion</th>
                  <th>합계</th>
                </tr>
              </thead>
              <tbody>
                {opRows.map(([name, v]) => (
                  <tr key={name}>
                    <td><code>{name}</code></td>
                    <td>{formatNum(v.calls)}</td>
                    <td>{formatNum(v.prompt_tokens)}</td>
                    <td>{formatNum(v.completion_tokens)}</td>
                    <td>{formatNum(v.total_tokens)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {recent.length > 0 && (
        <section className="usage-section">
          <h2>최근 호출 (최신 순)</h2>
          <div className="usage-table-wrap usage-table-recent">
            <table className="usage-table">
              <thead>
                <tr>
                  <th>시각 (UTC+9)</th>
                  <th>operation</th>
                  <th>prompt</th>
                  <th>comp</th>
                  <th>합계</th>
                  <th>ms</th>
                  <th>ok</th>
                </tr>
              </thead>
              <tbody>
                {recent.slice(0, 40).map((row, i) => (
                  <tr key={`${row.ts}-${row.operation}-${i}`}>
                    <td className="usage-td-mono">{formatKSTFromRow(row)}</td>
                    <td><code>{row.operation}</code></td>
                    <td>{formatNum(row.prompt_tokens)}</td>
                    <td>{formatNum(row.completion_tokens)}</td>
                    <td>{formatNum(row.total_tokens)}</td>
                    <td>{formatNum(row.duration_ms)}</td>
                    <td>{row.ok ? '✓' : '✗'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {!loading && summary?.total_calls === 0 && (
        <p className="usage-dashboard-muted">
          아직 기록된 LLM 호출이 없습니다. 채팅·에이전트·분석 등을 한 번 실행해 보세요.
        </p>
      )}
    </div>
  );
}
