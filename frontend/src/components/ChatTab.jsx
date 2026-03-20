import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { renderMarkdownComponents } from './markdownComponents';

const SUGGESTED_QUESTIONS = [
  'ST22 사용법 알려줘',
  'PO 조회 방법',
  'ALV Grid 기본 함수',
  'EKKO vs EKPO 차이',
  'SAP 덤프 T-Code 확인',
  'CTS PRD 이관 주의사항',
];

export default function ChatTab({
  loggedInUser,
  chatHistory,
  chatInput,
  setChatInput,
  isChatLoading,
  chatEndRef,
  trListLength,
  setActiveTab,
  handleChatSubmit,
  handleKeyDown,
  handleSuggestionClick,
  placeholder = 'CTS Bundler에게 물어보기',
  suggestions,
}) {
  const displaySuggestions = suggestions != null ? suggestions : SUGGESTED_QUESTIONS;
  const showTrChip = suggestions == null;

  return (
    <div className="chat-container">
      <div className="chat-history">
        {chatHistory.length === 0 && (
          <div className="welcome-section">
            <div className="greeting-text">
              {loggedInUser}님, 안녕하세요
              <br />
              {suggestions != null ? 'RAG 지식베이스(종속성·티켓)에 대해 물어보세요.' : '무엇을 도와드릴까요?'}
            </div>
            <div className="suggestions-grid">
              {showTrChip && (
                <div className="suggestion-chip" onClick={() => setActiveTab('analyzer')}>
                  내 TR 목록 보기 ({trListLength}개)
                </div>
              )}
              {displaySuggestions.map((q, idx) => (
                <div key={idx} className="suggestion-chip" onClick={() => handleSuggestionClick(q)}>
                  {q}
                </div>
              ))}
            </div>
          </div>
        )}
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            <div className={`message-icon ${msg.role}`}>
              {msg.role === 'user' ? (
                'U'
              ) : (
                <img src="/logo.png" alt="CB" style={{ width: '28px', height: 'auto' }} />
              )}
            </div>
            <div className="chat-message-content markdown-github-theme">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={renderMarkdownComponents}>
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        {isChatLoading && (
          <div className="chat-message ai">
            <div className="message-icon ai">
              <img src="/logo.png" alt="CB" style={{ width: '28px', height: 'auto' }} />
            </div>
            <div className="chat-message-content" style={{ display: 'flex', alignItems: 'center' }}>
              <div className="spinner"></div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>
      <div className="input-section">
        <div className="chat-input-wrapper">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
          />
          <button onClick={() => handleChatSubmit()} disabled={isChatLoading || !chatInput.trim()}>
            전송
          </button>
        </div>
      </div>
    </div>
  );
}
