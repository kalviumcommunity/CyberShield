import ReactMarkdown from 'react-markdown';

interface Props {
  content: string;
}

const MarkdownRenderer: React.FC<Props> = ({ content }) => (
  <ReactMarkdown
    components={{
      h1: ({ children }) => (
        <h1 className="mb-3 mt-5 text-xl font-bold text-white">{children}</h1>
      ),
      h2: ({ children }) => (
        <h2 className="mb-2 mt-4 text-lg font-semibold text-white">{children}</h2>
      ),
      h3: ({ children }) => (
        <h3 className="mb-2 mt-3 text-base font-semibold text-slate-200">{children}</h3>
      ),
      p: ({ children }) => (
        <p className="mb-3 leading-relaxed text-slate-300">{children}</p>
      ),
      ul: ({ children }) => (
        <ul className="mb-3 list-disc pl-5 text-slate-300 space-y-1">{children}</ul>
      ),
      ol: ({ children }) => (
        <ol className="mb-3 list-decimal pl-5 text-slate-300 space-y-1">{children}</ol>
      ),
      li: ({ children }) => <li className="leading-relaxed">{children}</li>,
      strong: ({ children }) => (
        <strong className="font-semibold text-white">{children}</strong>
      ),
      code: ({ children }) => (
        <code className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-sm text-cyber-300">
          {children}
        </code>
      ),
      pre: ({ children }) => (
        <pre className="mb-3 overflow-x-auto rounded-lg bg-slate-800 p-4 font-mono text-sm text-slate-300">
          {children}
        </pre>
      ),
      blockquote: ({ children }) => (
        <blockquote className="mb-3 border-l-4 border-cyber-500 pl-4 italic text-slate-400">
          {children}
        </blockquote>
      ),
    }}
  >
    {content}
  </ReactMarkdown>
);

export default MarkdownRenderer;
