import React from 'react';
import MarkdownContent from './MarkdownContent';
import Spinner from './Spinner';

const SUGGESTIONS = [
  '11355 사번 TR 목록 알려줘',
  'ZMMR0030 종속성 알려줘',
  '내 TR 리스트 보여주고, 그중 하나를 골라 티켓 매핑과 관련 오브젝트 종속성 알려주세요',
  // 'ZMMR0030이 뭘 호출해?',
  'ST22 사용법 알려줘',
  'CTS PRD 이관 주의사항',
];

function StepsBlock({ steps, reactUsedTools }) {
  // tool_result(도구 출력 텍스트)는 본문 마크다운과 중복되어 보이므로 표시하지 않음 — tool_call만 표시
  const callSteps = (steps || []).filter((s) => s.type === 'tool_call');
  if (callSteps.length === 0) return null;
  return (
    <div
      className="agent-steps"
      style={{
        marginTop: '10px',
        padding: '10px 12px',
        background: 'rgba(0,0,0,0.25)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        fontSize: '13px',
      }}
    >
      <div style={{ color: 'var(--accent-color)', marginBottom: '8px', fontWeight: 'bold' }}>
        사용한 도구 {reactUsedTools > 0 ? `(${reactUsedTools}회)` : ''}
      </div>
      {callSteps.map((s, idx) => (
        <div key={idx} style={{ marginBottom: '8px' }}>
          <span style={{ color: '#8bc34a' }}>
            도구: <code style={{ background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: '4px' }}>{s.tool}</code>
            {s.args && Object.keys(s.args).length > 0 && (
              <span style={{ color: 'var(--text-muted)', marginLeft: '6px' }}>
                {JSON.stringify(s.args)}
              </span>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function AgentTab({
  history,
  input,
  setInput,
  isLoading,
  streamPreview,
  chatEndRef,
  trListLength = 0,
  setActiveTab,
  handleSubmit,
  handleKeyDown,
  handleSuggestionClick,
}) {
  return (
    <div className="chat-container">
      <div className="chat-history">
        {history.length === 0 && (
          <div className="welcome-section">
            <div className="greeting-text">
              SAP Assistant
              <br />
              <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                일반 대화, 지식 검색(RAG), TR·종속성·티켓 조회, ReAct 에이전트 호출을 요청 내용에 맞게 판단해 답합니다.
              </span>
            </div>
            <div className="suggestions-grid">
              {trListLength >= 0 && (
                <div className="suggestion-chip" onClick={() => setActiveTab('analyzer')}>
                  내 TR 목록 보기 ({trListLength}개)
                </div>
              )}
              {SUGGESTIONS.map((q, idx) => (
                <div key={idx} className="suggestion-chip" onClick={() => handleSuggestionClick(q)}>
                  {q}
                </div>
              ))}
            </div>
          </div>
        )}
        {history.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            <div className={`message-icon ${msg.role}`}>
              {msg.role === 'user' ? 'U' : <img src="/logo.png" alt="CB" style={{ width: '28px', height: 'auto' }} />}
            </div>
            <div className="chat-message-content">
              <MarkdownContent>
                {msg.content}
              </MarkdownContent>
              {msg.role === 'ai' && (msg.steps || msg.react_used_tools !== undefined) && (
                <StepsBlock steps={msg.steps} reactUsedTools={msg.react_used_tools ?? 0} />
              )}
            </div>
          </div>
        ))}
        {isLoading && streamPreview == null && (
          <div className="chat-message ai">
            <div className="message-icon ai">
              <img src="/logo.png" alt="CB" style={{ width: '28px', height: 'auto' }} />
            </div>
            <div
              className="chat-message-content agent-chat-loading"
              style={{ display: 'flex', alignItems: 'center', gap: '10px' }}
            >
              <Spinner />
              <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>응답 생성 중…</span>
            </div>
          </div>
        )}
        {isLoading && streamPreview != null && (
          <div className="chat-message ai">
            <div className="message-icon ai">
              <img src="/logo.png" alt="CB" style={{ width: '28px', height: 'auto' }} />
            </div>
            <div className="chat-message-content">
              <MarkdownContent>
                {streamPreview}
              </MarkdownContent>
              <span className="agent-stream-cursor" aria-hidden />
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>
      <div className="input-section">
        <div className="chat-input-wrapper">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="무엇이든 물어보세요 (필요 시 도구 자동 호출)"
          />
          <button onClick={() => handleSubmit()} disabled={isLoading || !input.trim()}>
            전송
          </button>
        </div>
      </div>
    </div>
  );
}
