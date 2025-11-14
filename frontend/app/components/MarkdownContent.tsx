'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

interface MarkdownContentProps {
  content: string | unknown;
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({ content }) => {
  // Ensure content is always a string
  const contentString = typeof content === 'string' ? content : String(content || '');
  const components: Partial<Components> = {
    // Customize code blocks
    code: ({ className, children, ...props }) => {
      const isCodeBlock = className && className.startsWith('language-');
      return isCodeBlock ? (
        <pre className="rounded-xl glass-dark p-4 overflow-x-auto border border-white/10 shadow-lg">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      ) : (
        <code className="rounded-md glass px-1.5 py-0.5 text-sm text-blue-300/90 border border-white/10" {...props}>
          {children}
        </code>
      );
    },
    // Customize links
    a: (props) => (
      <a className="text-blue-400/90 hover:text-blue-300 underline transition-colors" {...props} />
    ),
    // Customize headings
    h1: (props) => (
      <h1 className="text-2xl font-semibold mt-4 mb-2 text-white/95 tracking-tight" {...props} />
    ),
    h2: (props) => (
      <h2 className="text-xl font-semibold mt-3 mb-2 text-white/95 tracking-tight" {...props} />
    ),
    h3: (props) => (
      <h3 className="text-lg font-medium mt-2 mb-1 text-white/90 tracking-tight" {...props} />
    ),
    // Customize lists
    ul: (props) => (
      <ul className="list-disc list-inside my-2 space-y-1 text-white/80" {...props} />
    ),
    ol: (props) => (
      <ol className="list-decimal list-inside my-2 space-y-1 text-white/80" {...props} />
    ),
    // Customize paragraphs
    p: (props) => (
      <p className="my-2 text-white/85 leading-relaxed" {...props} />
    ),
    // Customize blockquotes
    blockquote: (props) => (
      <blockquote
        className="border-l-4 border-white/20 pl-4 my-2 italic text-white/70 glass-dark rounded-r-lg py-2"
        {...props}
      />
    ),
    // Customize tables
    table: (props) => (
      <div className="overflow-x-auto my-2 rounded-xl">
        <table className="min-w-full border-collapse border border-white/10 glass-dark rounded-xl" {...props} />
      </div>
    ),
    th: (props) => (
      <th className="border border-white/10 px-4 py-2 glass font-semibold text-white/90" {...props} />
    ),
    td: (props) => (
      <td className="border border-white/10 px-4 py-2 text-white/80" {...props} />
    ),
  };

  return (
    <div className="markdown-content prose prose-invert prose-sm max-w-none dark:prose-invert">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {contentString}
      </ReactMarkdown>
    </div>
  );
};

