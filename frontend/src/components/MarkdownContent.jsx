import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { renderMarkdownComponents } from './markdownComponents';

export default function MarkdownContent({ content, className = '' }) {
  return (
    <div className={`markdown-github-theme ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={renderMarkdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
