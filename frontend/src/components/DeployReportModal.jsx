import React from 'react';
import { ANALYZER_STEP_ORDER } from '../api/analyzeStream';
import MarkdownContent from './MarkdownContent';
import { renderMarkdownComponents } from './markdownComponents';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const STEP_ORDER = ANALYZER_STEP_ORDER;
const STEP_LABELS = {
  fetch_data: '1차 Rule-based 리스크 스코어링',
  bc: 'BC 인프라·DB Lock 검토',
  fi: 'FI 재무회계 검토',
  co: 'CO 관리회계 검토',
  mm: 'MM 자재·구매 검토',
  sd: 'SD 영업·판매 검토',
  pp: 'PP 생산 검토',
  architect: '수석 아키텍트 최종 보고서',
};

export default function DeployReportModal({
  isOpen,
  onClose,
  loadingAnalysis,
  elapsedTime,
  analyzeCompletedSteps,
  analyzeProgress,
  analyzerResponse,
  /** 모달에 표시할 대상 TR (저장된 배치 재조회 시 체크박스와 무관) */
  displayTrkorrs = [],
  onDownload,
  onApproveDeploy,
}) {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.85)',
        zIndex: 10000,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        animation: 'fadeIn 0.2s ease-out',
      }}
    >
      <div
        style={{
          width: '60vw',
          height: '85vh',
          backgroundColor: '#0d1117',
          borderRadius: '12px',
          border: '1px solid #30363d',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 20px 50px rgba(0,0,0,0.8)',
        }}
      >
        <div
          style={{
            padding: '15px 25px',
            backgroundColor: '#161b22',
            borderBottom: '1px solid #30363d',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h3 style={{ margin: 0, color: '#e6edf3', fontSize: '18px' }}>📄 통합 배포 심의 위원회 최종 레포트</h3>
          <button
            onClick={() => {
              onClose();
            }}
            style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '20px' }}
          >
            ✕
          </button>
        </div>

        <div style={{ flex: 1, padding: '30px', backgroundColor: '#0d1117', overflowY: 'auto' }}>
          {loadingAnalysis ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '25px' }}>
              <div style={{ position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <div className="spinner" style={{ width: '65px', height: '65px', borderWidth: '4px', borderColor: '#238636', borderTopColor: 'transparent' }}></div>
                <div style={{ position: 'absolute', fontSize: '14px', color: '#fff', fontWeight: 'bold' }}>{elapsedTime}s</div>
              </div>
              <div
                style={{
                  textAlign: 'left',
                  lineHeight: '2.4',
                  backgroundColor: '#161b22',
                  padding: '25px 40px',
                  borderRadius: '12px',
                  border: '1px solid #30363d',
                  minWidth: '500px',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
                }}
              >
                <h2 style={{ color: '#fff', marginBottom: '20px', textAlign: 'center', fontSize: '18px' }}>🤖 AI 전문가 위원회 토의 진행 중...</h2>
                {STEP_ORDER.map((key) => {
                  const done = analyzeCompletedSteps.includes(key);
                  const current = analyzeProgress.step === key;
                  const label = STEP_LABELS[key] || key;
                  return (
                    <div key={key} style={{ fontSize: '14.5px', color: done || current ? '#e6edf3' : '#444' }}>
                      <span style={{ display: 'inline-block', width: '25px' }}>{done ? '✅' : current ? '🔄' : '⚫'}</span> {label}
                    </div>
                  );
                })}
                <div
                  style={{
                    marginTop: '25px',
                    padding: '15px',
                    backgroundColor: '#0d1117',
                    borderRadius: '8px',
                    border: '1px dashed #444',
                    fontSize: '13.5px',
                    color: '#a8cdff',
                    textAlign: 'center',
                    minHeight: '50px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.3s',
                  }}
                >
                  {analyzeProgress.label || '대기 중...'}
                </div>
              </div>
            </div>
          ) : (
            <div className="markdown-github-theme" style={{ animation: 'fadeIn 0.4s ease-out' }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={renderMarkdownComponents}>
                {analyzerResponse || '저장된 레포트가 없습니다.'}
              </ReactMarkdown>
            </div>
          )}
        </div>

        <div
          style={{
            padding: '20px 30px',
            backgroundColor: '#161b22',
            borderTop: '1px solid #30363d',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ color: '#8b949e', fontSize: '13px' }}>대상 TR: {(displayTrkorrs || []).join(', ') || '—'}</span>
          <div style={{ display: 'flex', gap: '15px' }}>
            <button
              onClick={onDownload}
              disabled={loadingAnalysis}
              style={{
                padding: '10px 20px',
                background: '#2b2b2b',
                color: loadingAnalysis ? '#666' : '#a8cdff',
                border: '1px solid #444',
                borderRadius: '6px',
                cursor: loadingAnalysis ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
              }}
            >
              결과 다운로드
            </button>
            <button
              onClick={onApproveDeploy}
              disabled={loadingAnalysis}
              style={{
                padding: '10px 30px',
                background: loadingAnalysis ? '#444' : '#238636',
                color: loadingAnalysis ? '#888' : '#fff',
                border: '1px solid rgba(240,246,252,0.1)',
                borderRadius: '6px',
                cursor: loadingAnalysis ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                boxShadow: loadingAnalysis ? 'none' : '0 0 10px rgba(35, 134, 54, 0.4)',
              }}
            >
              🚀 심의 결과 확인 및 배포 승인
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
