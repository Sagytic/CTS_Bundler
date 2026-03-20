import React from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

/** Shared ReactMarkdown `components` map (separate file for react-refresh). */
export const renderMarkdownComponents = {
  a: ({
    // react-markdown passes mdast node; omit from DOM spread
    // eslint-disable-next-line no-unused-vars
    node,
    ...props
  }) => (
    <a {...props} target="_blank" rel="noopener noreferrer" style={{ color: '#58a6ff', textDecoration: 'underline' }} />
  ),
  code({
    // eslint-disable-next-line no-unused-vars
    node,
    inline,
    className,
    children,
    ...props
  }) {
    const match = /language-(\w+)/.exec(className || '');
    return !inline && match ? (
      <SyntaxHighlighter
        {...props}
        children={String(children).replace(/\n$/, '')}
        style={vscDarkPlus}
        language={match[1] === 'abap' ? 'abap' : match[1]}
        PreTag="div"
        customStyle={{
          borderRadius: '8px',
          border: '1px solid #30363d',
          fontSize: '13px',
          backgroundColor: '#161b22',
        }}
      />
    ) : (
      <code
        {...props}
        className={className}
        style={{
          backgroundColor: 'rgba(110,118,129,0.4)',
          padding: '0.2em 0.4em',
          borderRadius: '6px',
          fontSize: '85%',
        }}
      >
        {children}
      </code>
    );
  },
};
