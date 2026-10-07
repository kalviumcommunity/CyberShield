import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getDocuments } from '../api/documents';
import type { Document, DocumentType } from '../types';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import { FileText, Search, Upload, ChevronRight, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const TYPE_OPTIONS: { value: '' | DocumentType; label: string }[] = [
  { value: '', label: 'All Types' },
  { value: 'threat_intelligence', label: 'Threat Intelligence' },
  { value: 'incident_runbook', label: 'Incident Runbook' },
  { value: 'vulnerability_advisory', label: 'Vulnerability Advisory' },
];

const DocumentsPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [filter, setFilter] = useState<'' | DocumentType>('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    getDocuments(0, 100, filter || undefined)
      .then(setDocuments)
      .catch(() => setError('Failed to load documents.'))
      .finally(() => setLoading(false));
  }, [filter]);

  const filtered = documents.filter(
    (d) =>
      d.title.toLowerCase().includes(search.toLowerCase()) ||
      d.file_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-5xl">
      <div className="mb-6 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <FileText className="h-7 w-7 text-blue-400" />
            <h1 className="text-3xl font-bold text-white">Documents</h1>
          </div>
          <p className="text-slate-400">Threat intelligence, runbooks, and advisories.</p>
        </div>
        {isAdmin && (
          <Link
            to="/documents/upload"
            className="flex items-center gap-2 rounded-lg bg-cyber-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-cyber-700"
          >
            <Upload className="h-4 w-4" /> Upload Document
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or filename…"
            className="w-full rounded-lg border border-slate-700 bg-slate-900 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 outline-none focus:border-cyber-500"
          />
        </div>
        {/* Type filter */}
        <div className="flex gap-2 flex-wrap">
          {TYPE_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
                filter === value
                  ? 'border-cyber-600 bg-cyber-600/20 text-cyber-300'
                  : 'border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-800 bg-red-900/20 p-4">
          <AlertTriangle className="h-5 w-5 text-red-400" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 py-20 text-center">
          <FileText className="mx-auto mb-3 h-10 w-10 text-slate-600" />
          <p className="text-slate-400">No documents found.</p>
          {isAdmin && (
            <Link to="/documents/upload" className="mt-3 inline-block text-sm text-cyber-400 hover:underline">
              Upload your first document →
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((doc) => (
            <Link
              key={doc.id}
              to={`/documents/${doc.id}`}
              className="group flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900 px-5 py-4 transition hover:border-slate-600"
            >
              <FileText className="h-5 w-5 shrink-0 text-slate-500 group-hover:text-blue-400 transition" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-white group-hover:text-cyber-300 transition truncate">
                  {doc.title}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {doc.file_name} · {doc.extracted_text_length.toLocaleString()} chars
                </p>
              </div>
              <Badge variant={doc.document_type as DocumentType} />
              <p className="text-xs text-slate-500 shrink-0">
                {new Date(doc.created_at).toLocaleDateString()}
              </p>
              <ChevronRight className="h-4 w-4 text-slate-600 group-hover:text-slate-300 transition" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default DocumentsPage;
