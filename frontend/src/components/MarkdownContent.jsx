import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { renderMarkdownComponents } from './markdownComponents';

export default function MarkdownContent({ content, children, className = '', style }) {
  const markdownSource = children || content || '';
  return (
    <div className={`markdown-github-theme ${className}`} style={style}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={renderMarkdownComponents}>
        {markdownSource}
      </ReactMarkdown>
    </div>
  );
}
