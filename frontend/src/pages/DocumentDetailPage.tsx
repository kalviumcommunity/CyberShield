import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getDocument, getDocumentChunks } from '../api/documents';
import type { Document, DocumentChunk } from '../types';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import { FileText, ChevronLeft, Database, AlertTriangle } from 'lucide-react';

const DocumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const docId = Number(id);

  const [doc, setDoc] = useState<Document | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [error, setError] = useState('');
  const [showContent, setShowContent] = useState(false);

  useEffect(() => {
    getDocument(docId)
      .then((d) => {
        setDoc(d);
        setLoading(false);
        // Fetch chunks
        setChunksLoading(true);
        return getDocumentChunks(docId);
      })
      .then(setChunks)
      .catch(() => setError('Failed to load document.'))
      .finally(() => {
        setLoading(false);
        setChunksLoading(false);
      });
  }, [docId]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-red-800 bg-red-900/20 p-6">
        <AlertTriangle className="h-6 w-6 text-red-400" />
        <p className="text-red-300">{error || 'Document not found.'}</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <Link
        to="/documents"
        className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition"
      >
        <ChevronLeft className="h-4 w-4" /> Back to Documents
      </Link>

      {/* Header */}
      <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-900/30 border border-blue-800/50">
            <FileText className="h-6 w-6 text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-white">{doc.title}</h1>
            <p className="mt-1 text-sm text-slate-400">{doc.file_name}</p>
          </div>
          <Badge variant={doc.document_type as import('../types').DocumentType} />
        </div>

        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <InfoItem label="Document ID" value={`#${doc.id}`} />
          <InfoItem label="Text Length" value={`${doc.extracted_text_length.toLocaleString()} chars`} />
          <InfoItem label="Chunks" value={chunks.length.toString()} />
          <InfoItem label="Uploaded" value={new Date(doc.created_at).toLocaleDateString()} />
        </div>
      </div>

      {/* Raw Content Toggle */}
      {doc.content && (
        <div className="mb-6">
          <button
            onClick={() => setShowContent(!showContent)}
            className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-white transition"
          >
            <FileText className="h-4 w-4" />
            {showContent ? 'Hide' : 'Show'} Extracted Text
          </button>
          {showContent && (
            <div className="max-h-64 overflow-y-auto rounded-xl border border-slate-800 bg-slate-800/50 p-4">
              <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                {doc.content}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Chunks */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-slate-400" />
          <h2 className="font-semibold text-white">
            Text Chunks{chunks.length > 0 ? ` (${chunks.length})` : ''}
          </h2>
        </div>

        {chunksLoading ? (
          <div className="flex justify-center py-10">
            <Spinner />
          </div>
        ) : chunks.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900 py-12 text-center">
            <Database className="mx-auto mb-3 h-8 w-8 text-slate-600" />
            <p className="text-slate-400 text-sm">
              No chunks yet. An admin must process and embed this document.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {chunks.map((chunk) => (
              <div
                key={chunk.id}
                className="rounded-xl border border-slate-800 bg-slate-900 p-4"
              >
                <div className="mb-2 flex items-center gap-3">
                  <span className="text-xs font-bold text-slate-500">
                    Chunk #{chunk.chunk_index + 1}
                  </span>
                  {chunk.embedding && (
                    <span className="text-xs text-green-400 font-medium">✓ Embedded</span>
                  )}
                </div>
                <p className="text-sm leading-relaxed text-slate-300 font-mono">
                  {chunk.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const InfoItem: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <p className="text-xs text-slate-500 font-medium">{label}</p>
    <p className="mt-0.5 text-sm font-semibold text-white">{value}</p>
  </div>
);

export default DocumentDetailPage;
