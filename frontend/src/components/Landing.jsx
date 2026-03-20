import React from 'react';

export default function Landing({ loginId, setLoginId, isLoggingIn, handleLogin }) {
  return (
    <div className="landing-container">
      <div className="login-box">
        <img
          src="/logo.png"
          alt="CTS Bundler Logo"
          className="login-logo"
          onError={(e) => {
            e.target.style.display = 'none';
          }}
        />
        <h2>Welcome to CTS Bundler</h2>
        <p>사번(ID)을 입력하여 시작하세요.</p>
        <form onSubmit={handleLogin} className="login-form">
          <input
            type="text"
            placeholder="예: 11355"
            value={loginId}
            onChange={(e) => setLoginId(e.target.value)}
            className="login-input"
            autoFocus
          />
          <button type="submit" className="login-button" disabled={isLoggingIn}>
            {isLoggingIn ? '확인 중...' : '시작하기'}
          </button>
        </form>
      </div>
    </div>
  );
}
