import React, { useState } from 'react';
import { api } from '../api/client';

const RAG_INGEST_DEFAULT = 3000;

export default function SettingsModal({
  isOpen,
  onClose,
  settingUserId,
  setSettingUserId,
  settingLlmModel,
  setSettingLlmModel,
  onSave,
}) {
  const [ragMaxDocs, setRagMaxDocs] = useState(() => {
    const saved = localStorage.getItem('ragMaxDocs');
    return saved ? parseInt(saved, 10) : RAG_INGEST_DEFAULT;
  });
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestResult, setIngestResult] = useState(null); // { ok, ingested } or { error }

  const handleRunIngest = async () => {
    const max = Math.max(1, parseInt(ragMaxDocs, 10) || RAG_INGEST_DEFAULT);
    setRagMaxDocs(max);
    localStorage.setItem('ragMaxDocs', String(max));
    setIngestResult(null);
    setIngestLoading(true);
    try {
      const res = await api.post('/api/rag/ingest/', { max_docs: max });
      setIngestResult(res.data?.ok ? { ok: true, ingested: res.data.ingested } : { error: res.data?.error || '알 수 없는 응답' });
    } catch (err) {
      setIngestResult({ error: err.response?.data?.error || err.message || '요청 실패' });
    } finally {
      setIngestLoading(false);
    }
  };

  if (!isOpen) return null;

  const inputStyle = {
    width: '100%',
    padding: '10px',
    borderRadius: '6px',
    backgroundColor: 'var(--bg-sidebar)',
    border: '1px solid var(--border-color)',
    color: '#fff',
    boxSizing: 'border-box',
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.7)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-main)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          width: '400px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '30px',
          color: '#fff',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '20px' }}>환경 설정 (Settings)</h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', fontSize: '20px' }}
          >
            ✕
          </button>
        </div>
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '14px' }}>
            SAP 접속 ID (사번)
          </label>
          <input type="text" value={settingUserId} onChange={(e) => setSettingUserId(e.target.value)} style={inputStyle} />
        </div>
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '14px' }}>
            AI 분석 모델 (LLM)
          </label>
          <select
            value={settingLlmModel}
            onChange={(e) => setSettingLlmModel(e.target.value)}
            style={inputStyle}
          >
            <option value="gpt-4o">GPT-4o (정밀 분석용)</option>
            <option value="gpt-4o-mini">GPT-4o Mini (빠른 응답용)</option>
          </select>
        </div>

        <div style={{ marginBottom: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
          <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '14px' }}>
            RAG 인덱싱 (Embedding)
          </label>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
            종속성·티켓 DB를 벡터 DB에 넣어 RAG 챗/에이전트에서 검색되게 합니다. 건수가 크면 수 분 걸릴 수 있습니다.
          </p>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
            <input
              type="number"
              min={1}
              max={200000}
              value={ragMaxDocs}
              onChange={(e) => setRagMaxDocs(parseInt(e.target.value, 10) || RAG_INGEST_DEFAULT)}
              style={{ ...inputStyle, width: '120px' }}
            />
            <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>건</span>
            <button
              onClick={handleRunIngest}
              disabled={ingestLoading}
              style={{
                padding: '10px 14px',
                borderRadius: '6px',
                background: ingestLoading ? '#555' : 'var(--accent-color)',
                border: 'none',
                color: '#000',
                fontWeight: 'bold',
                cursor: ingestLoading ? 'not-allowed' : 'pointer',
              }}
            >
              {ingestLoading ? '진행 중…' : '인덱싱 실행'}
            </button>
          </div>
          {ingestResult && (
            <div
              style={{
                fontSize: '13px',
                padding: '8px 10px',
                borderRadius: '6px',
                backgroundColor: ingestResult.ok ? 'rgba(0,128,0,0.2)' : 'rgba(200,0,0,0.2)',
                color: ingestResult.ok ? '#8bc34a' : '#f48fb1',
              }}
            >
              {ingestResult.ok ? `완료: ${ingestResult.ingested}건 인덱싱됨` : `오류: ${ingestResult.error}`}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 15px',
              borderRadius: '6px',
              background: 'transparent',
              border: '1px solid var(--border-color)',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            취소
          </button>
          <button
            onClick={onSave}
            style={{
              padding: '10px 15px',
              borderRadius: '6px',
              background: 'var(--accent-color)',
              border: 'none',
              color: '#000',
              fontWeight: 'bold',
              cursor: 'pointer',
            }}
          >
            저장
          </button>
        </div>
      </div>
    </div>
  );
}
