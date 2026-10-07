import { useState } from 'react';
import { getMitigationAnswer } from '../api/mitigation';
import type { MitigationAnswerResponse, Severity } from '../types';
import MarkdownRenderer from '../components/ui/MarkdownRenderer';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import { ShieldAlert, BookOpen, AlertTriangle, Zap } from 'lucide-react';

const SEVERITY_OPTIONS: { value: Severity; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

const EXAMPLE_ALERTS = [
  'Multiple failed SSH root login attempts observed on production bastion host.',
  'Suspicious PowerShell script execution detected on Windows domain controller.',
  'Ransomware file encryption activity detected across network shares.',
];

const MitigationPage: React.FC = () => {
  const [alert, setAlert] = useState('');
  const [severity, setSeverity] = useState<Severity>('high');
  const [topK, setTopK] = useState(5);
  const [response, setResponse] = useState<MitigationAnswerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!alert.trim()) return;
    setError('');
    setResponse(null);
    setLoading(true);
    try {
      const data = await getMitigationAnswer({
        alert: alert.trim(),
        top_k: topK,
        min_threshold: 0.30,
        severity,
      });
      setResponse(data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to retrieve mitigations. Ensure the backend is running.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <ShieldAlert className="h-7 w-7 text-red-400" />
          <h1 className="text-3xl font-bold text-white">Mitigation Advisor</h1>
        </div>
        <p className="text-slate-400">
          Describe an active security alert to retrieve AI-grounded mitigation steps from your threat intelligence knowledge base.
        </p>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-slate-300">
            Security Alert Description
          </label>
          <textarea
            value={alert}
            onChange={(e) => setAlert(e.target.value)}
            rows={4}
            placeholder="e.g. Multiple failed SSH root login attempts observed on production bastion host..."
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white placeholder-slate-500 outline-none transition resize-none focus:border-cyber-500 focus:ring-1 focus:ring-cyber-500"
          />
          {/* Example alerts */}
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLE_ALERTS.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setAlert(ex)}
                className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-400 hover:border-cyber-600 hover:text-cyber-300 transition"
              >
                {ex.slice(0, 50)}…
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          {/* Severity */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">Severity</label>
            <div className="flex gap-2">
              {SEVERITY_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setSeverity(value)}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
                    severity === value
                      ? 'border-cyber-600 bg-cyber-600/20 text-cyber-300'
                      : 'border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Top K */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              Max Results: <span className="text-white font-bold">{topK}</span>
            </label>
            <input
              type="range"
              min={1}
              max={10}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-32 accent-cyber-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !alert.trim()}
            className="ml-auto flex items-center gap-2 rounded-lg bg-red-600 px-6 py-2.5 font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? <Spinner size="sm" /> : <Zap className="h-4 w-4" />}
            {loading ? 'Analyzing…' : 'Get Mitigations'}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-800 bg-red-900/20 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Results */}
      {response && (
        <div className="space-y-6">
          {/* Alert summary */}
          <div className="rounded-xl border border-slate-700 bg-slate-800/40 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Alert</p>
            <p className="text-slate-200">{response.alert}</p>
            {response.alert_id && (
              <p className="mt-1 text-xs text-slate-500">Alert ID: #{response.alert_id}</p>
            )}
          </div>

          {/* AI Answer */}
          <div className="rounded-2xl border border-cyber-800/50 bg-slate-900 p-6">
            <div className="flex items-center gap-2 mb-4">
              <ShieldAlert className="h-5 w-5 text-cyber-400" />
              <h2 className="font-semibold text-white">AI Mitigation Guidance</h2>
              <Badge variant="info" label="RAG" className="ml-auto" />
            </div>
            {response.answer === 'Insufficient information found in the available security documents.' ? (
              <div className="flex items-center gap-3 rounded-lg border border-yellow-800 bg-yellow-900/20 p-4">
                <AlertTriangle className="h-5 w-5 text-yellow-400" />
                <p className="text-yellow-300 text-sm">
                  Insufficient information found in the available security documents. Please upload and embed relevant runbooks or advisories.
                </p>
              </div>
            ) : (
              <MarkdownRenderer content={response.answer} />
            )}
          </div>

          {/* Source Citations */}
          {response.sources.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <BookOpen className="h-5 w-5 text-slate-400" />
                <h2 className="font-semibold text-white">
                  Source Citations ({response.sources.length})
                </h2>
              </div>
              <div className="space-y-3">
                {response.sources.map((src, i) => (
                  <div
                    key={src.chunk_id}
                    className="rounded-xl border border-slate-800 bg-slate-900 p-5"
                  >
                    <div className="mb-3 flex items-center gap-3 flex-wrap">
                      <span className="text-xs font-bold text-slate-500">#{i + 1}</span>
                      <span className="font-medium text-white">{src.document_title}</span>
                      <Badge variant={src.document_type} />
                      <span className="ml-auto text-xs text-slate-400">
                        Score: <span className="font-semibold text-green-400">{(src.relevance_score * 100).toFixed(1)}%</span>
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed text-slate-300 font-mono bg-slate-800/60 rounded-lg p-3">
                      {src.mitigation_text}
                    </p>
                    <p className="mt-2 text-xs text-slate-500">
                      Source: {src.source_file} · Chunk #{src.chunk_id}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MitigationPage;
