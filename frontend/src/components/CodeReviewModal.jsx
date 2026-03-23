import React, { useEffect, useRef } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import MarkdownContent from './MarkdownContent';
import Spinner from './Spinner';

export default function CodeReviewModal({
  isOpen,
  currentReviewData,
  onClose,
  isEditingTicketSpec,
  editTicketId,
  setEditTicketId,
  editDesc,
  setEditDesc,
  savingTicketMapping,
  writingToSap,
  onStartEditTicketSpec,
  onSaveTicketMapping,
  onCancelEditTicketSpec,
  onExecuteCodeReview,
  onWriteRefactoredToSap,
  onConfirmReview,
  extractRefactoredCode,
}) {
  const streamEndRef = useRef(null);

  useEffect(() => {
    if (currentReviewData?.isLoading && currentReviewData?.aiResult) {
      streamEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [currentReviewData?.aiResult, currentReviewData?.isLoading]);

  if (!isOpen || !currentReviewData) return null;

  const hasRefactoredCode = !!extractRefactoredCode(currentReviewData.aiResult);

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
          width: '95vw',
          height: '90vh',
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <h3 style={{ margin: 0, color: '#e6edf3', fontSize: '18px' }}>🤖 AI Code Inspector (Clean ABAP)</h3>
            <span style={{ backgroundColor: '#2b2b2b', color: '#a8cdff', padding: '4px 10px', borderRadius: '15px', fontSize: '12px', fontWeight: 'bold' }}>
              {currentReviewData.objName}
            </span>
            {currentReviewData.isLoading && (
              <span
                style={{
                  backgroundColor: 'rgba(168, 205, 255, 0.15)',
                  color: '#a8cdff',
                  padding: '4px 10px',
                  borderRadius: '15px',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  border: '1px solid #388bfd',
                  animation: 'pulse 1.5s ease-in-out infinite',
                }}
              >
                ● Azure OpenAI 스트리밍 출력 중
              </span>
            )}
            {currentReviewData.writtenToSap && (
              <span
                style={{
                  backgroundColor: 'rgba(35, 134, 54, 0.3)',
                  color: '#3fb950',
                  padding: '4px 12px',
                  borderRadius: '15px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  border: '1px solid #238636',
                }}
              >
                ✓ 리팩토링 적용됨
              </span>
            )}
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '20px' }}>
            ✕
          </button>
        </div>
        {currentReviewData.writtenToSap && (
          <div
            style={{
              padding: '10px 25px',
              backgroundColor: 'rgba(35, 134, 54, 0.15)',
              borderBottom: '1px solid #238636',
              color: '#3fb950',
              fontSize: '13px',
              fontWeight: 'bold',
            }}
          >
            리팩토링 코드가 SAP에 적용되었습니다. 아래 소스코드는 적용된 내용입니다.
          </div>
        )}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <div style={{ width: '25%', padding: '25px', borderRight: '1px solid #30363d', backgroundColor: '#0d1117', overflowY: 'auto' }}>
            <div style={{ marginBottom: '25px' }}>
              <label style={{ color: '#8b949e', fontSize: '13px', display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>🎫 연동된 JIRA 티켓</label>
              {isEditingTicketSpec ? (
                <input
                  type="text"
                  value={editTicketId}
                  onChange={(e) => setEditTicketId(e.target.value)}
                  placeholder="예: PROJ-1234 (비워두면 미매핑)"
                  style={{ width: '100%', padding: '12px', background: '#161b22', border: '1px solid #58a6ff', color: '#a8cdff', borderRadius: '6px', fontWeight: 'bold' }}
                />
              ) : (
                <input
                  type="text"
                  value={currentReviewData.ticket}
                  readOnly
                  style={{ width: '100%', padding: '12px', background: '#161b22', border: '1px solid #30363d', color: '#a8cdff', borderRadius: '6px', fontWeight: 'bold' }}
                />
              )}
            </div>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ color: '#8b949e', fontSize: '13px', display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>📝 현업 요구사항 명세</label>
              {isEditingTicketSpec ? (
                <textarea
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  placeholder="현업 요구사항을 입력하세요. (JIRA 연동 전까지 수동 입력)"
                  style={{ width: '100%', height: '150px', padding: '12px', background: '#161b22', border: '1px solid #58a6ff', color: '#e6edf3', borderRadius: '6px', resize: 'vertical', lineHeight: '1.6' }}
                />
              ) : (
                <textarea
                  value={currentReviewData.desc}
                  readOnly
                  style={{ width: '100%', height: '150px', padding: '12px', background: '#161b22', border: '1px solid #30363d', color: '#e6edf3', borderRadius: '6px', resize: 'none', lineHeight: '1.6' }}
                />
              )}
            </div>
            {isEditingTicketSpec ? (
              <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
                <button
                  onClick={onSaveTicketMapping}
                  disabled={savingTicketMapping}
                  style={{ flex: 1, padding: '10px', background: '#238636', color: '#fff', border: 'none', borderRadius: '6px', cursor: savingTicketMapping ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '13px' }}
                >
                  {savingTicketMapping ? '저장 중...' : '저장'}
                </button>
                <button
                  onClick={onCancelEditTicketSpec}
                  disabled={savingTicketMapping}
                  style={{ padding: '10px 16px', background: '#30363d', color: '#e6edf3', border: '1px solid #8b949e', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}
                >
                  취소
                </button>
              </div>
            ) : (
              <button
                onClick={onStartEditTicketSpec}
                style={{ marginBottom: '20px', width: '100%', padding: '10px', background: 'transparent', color: '#58a6ff', border: '1px solid #58a6ff', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}
              >
                ✏️ 직접 입력 / 수정
              </button>
            )}

            {!currentReviewData.aiResult && !currentReviewData.isLoading && !currentReviewData.isCodeLoading && (
              <button
                onClick={onExecuteCodeReview}
                style={{ width: '100%', padding: '15px', background: 'var(--accent-color)', color: '#000', fontSize: '14px', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', boxShadow: '0 4px 12px rgba(168, 205, 255, 0.3)' }}
              >
                ▶ AI 논리 분석 및 리팩토링 시작
              </button>
            )}

            {currentReviewData.isLoading && !currentReviewData.aiResult && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '40px', gap: '12px' }}>
                <Spinner size={36} borderWidth={3} />
                <span style={{ color: '#8b949e', fontSize: '13px', textAlign: 'center', lineHeight: 1.5 }}>
                  Azure OpenAI에 요청 전송 중…
                  <br />
                  <span style={{ fontSize: '12px', color: '#666' }}>곧 우측에 리뷰가 실시간으로 표시됩니다.</span>
                </span>
              </div>
            )}
            {currentReviewData.isLoading && currentReviewData.aiResult && (
              <div style={{ marginTop: '24px', padding: '10px', background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', fontSize: '12px', color: '#58a6ff' }}>
                ↳ 응답 스트리밍 수신 중 (미리보기는 우측 패널)
              </div>
            )}
          </div>

          <div style={{ width: '35%', padding: '25px', borderRight: '1px solid #30363d', backgroundColor: '#161b22', overflowY: 'auto' }}>
            <label style={{ color: '#8b949e', fontSize: '14px', display: 'block', marginBottom: '15px', fontWeight: 'bold' }}>
              🖥️ {currentReviewData.appliedSource ? 'SAP 반영 소스코드 (리팩토링 적용됨)' : 'SAP 원본 소스코드'}
            </label>
            {currentReviewData.isCodeLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60%', gap: '15px' }}>
                <Spinner size={30} borderWidth={3} />
                <span style={{ color: '#a8cdff', fontSize: '13px' }}>SAP 서버에서 원본 코드를 추출 중입니다...</span>
              </div>
            ) : (
              <div className="markdown-github-theme">
                <SyntaxHighlighter
                  language="abap"
                  style={vscDarkPlus}
                  customStyle={{ margin: 0, height: 'calc(100vh - 200px)', borderRadius: '8px', border: '1px solid #30363d', fontSize: '13px', backgroundColor: '#161b22' }}
                >
                  {(currentReviewData.appliedSource || currentReviewData.originalCode) || '* 코드가 없습니다.'}
                </SyntaxHighlighter>
              </div>
            )}
          </div>

          <div style={{ flex: 1, padding: '30px', backgroundColor: '#0d1117', overflowY: 'auto' }}>
            {!currentReviewData.aiResult && !currentReviewData.isLoading && (
              <div style={{ display: 'flex', height: '100%', justifyContent: 'center', alignItems: 'center', color: '#8b949e', fontSize: '16px' }}>
                좌측에서 분석을 시작하면 리팩토링 제안이 표시됩니다.
              </div>
            )}
            {currentReviewData.isLoading && !currentReviewData.aiResult && (
              <div style={{ display: 'flex', height: '100%', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: '#8b949e', gap: '16px' }}>
                <Spinner size={48} borderWidth={4} borderColor="#388bfd" borderTopColor="transparent" />
                <div style={{ fontSize: '15px', textAlign: 'center', maxWidth: '360px', lineHeight: 1.6 }}>
                  모델이 리뷰 마크다운을 생성하고 있습니다.
                  <br />
                  <span style={{ fontSize: '13px', color: '#666' }}>토큰이 도착하는 대로 아래에 이어서 표시됩니다.</span>
                </div>
              </div>
            )}
            {currentReviewData.aiResult && (
              <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
                <MarkdownContent>
                  {currentReviewData.aiResult}
                </MarkdownContent>
                {currentReviewData.isLoading && (
                  <span
                    style={{
                      display: 'inline-block',
                      width: '10px',
                      height: '1.1em',
                      marginLeft: '4px',
                      verticalAlign: 'text-bottom',
                      backgroundColor: '#a8cdff',
                      animation: 'codeReviewCursorBlink 0.9s step-end infinite',
                    }}
                    aria-hidden
                  />
                )}
                <div ref={streamEndRef} style={{ height: '1px' }} />
              </div>
            )}
          </div>
        </div>

        {currentReviewData.aiResult && !currentReviewData.isLoading && (
          <div
            style={{
              padding: '20px 30px',
              backgroundColor: '#161b22',
              borderTop: '1px solid #30363d',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '15px',
              flexWrap: 'wrap',
            }}
          >
            <button
              onClick={onWriteRefactoredToSap}
              disabled={writingToSap || !hasRefactoredCode}
              style={{
                padding: '10px 20px',
                background: writingToSap ? '#444' : '#1f6feb',
                color: '#fff',
                border: '1px solid #388bfd',
                borderRadius: '6px',
                cursor: writingToSap ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
              }}
            >
              {writingToSap ? '저장 중...' : '📤 리팩토링 코드 SAP에 쓰기'}
            </button>
            <div style={{ display: 'flex', gap: '15px' }}>
              <button
                onClick={onClose}
                style={{ padding: '10px 25px', background: 'transparent', color: '#e6edf3', border: '1px solid #8b949e', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
              >
                나중에 결정
              </button>
              <button
                onClick={onConfirmReview}
                style={{
                  padding: '10px 30px',
                  background: '#238636',
                  color: '#fff',
                  border: '1px solid rgba(240,246,252,0.1)',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  boxShadow: '0 0 10px rgba(35, 134, 54, 0.4)',
                }}
              >
                ✅ 이상 없음 (리뷰 Confirm 저장)
              </button>
            </div>
          </div>
        )}
        {currentReviewData.aiResult && currentReviewData.isLoading && (
          <div
            style={{
              padding: '12px 30px',
              backgroundColor: '#161b22',
              borderTop: '1px solid #30363d',
              color: '#8b949e',
              fontSize: '12px',
              textAlign: 'center',
            }}
          >
            생성이 끝나면 SAP 쓰기·리뷰 확정 버튼이 활성화됩니다.
          </div>
        )}
      </div>
      <style>{`
        @keyframes codeReviewCursorBlink { 50% { opacity: 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.65; } }
      `}</style>
    </div>
  );
}
