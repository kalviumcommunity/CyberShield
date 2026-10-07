import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadDocument, processDocument, embedDocument } from '../api/documents';
import type { DocumentType } from '../types';
import Spinner from '../components/ui/Spinner';
import { Upload, FileText, CheckCircle, AlertTriangle, ChevronRight } from 'lucide-react';

type Step = 'upload' | 'process' | 'embed' | 'done';

interface StepState {
  status: 'idle' | 'running' | 'done' | 'error';
  message?: string;
}

const DOC_TYPES: { value: DocumentType; label: string; desc: string }[] = [
  {
    value: 'threat_intelligence',
    label: 'Threat Intelligence',
    desc: 'APT reports, IOC feeds, threat actor profiles',
  },
  {
    value: 'incident_runbook',
    label: 'Incident Runbook',
    desc: 'Step-by-step incident response procedures',
  },
  {
    value: 'vulnerability_advisory',
    label: 'Vulnerability Advisory',
    desc: 'CVE advisories, patch guidance, security bulletins',
  },
];

const DocumentUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<DocumentType>('incident_runbook');
  const [title, setTitle] = useState('');
  const [documentId, setDocumentId] = useState<number | null>(null);

  const [steps, setSteps] = useState<Record<Step, StepState>>({
    upload: { status: 'idle' },
    process: { status: 'idle' },
    embed: { status: 'idle' },
    done: { status: 'idle' },
  });

  const [globalLoading, setGlobalLoading] = useState(false);
  const [globalError, setGlobalError] = useState('');

  const setStepState = (step: Step, state: StepState) =>
    setSteps((prev) => ({ ...prev, [step]: state }));

  const handleFileDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const runPipeline = async () => {
    if (!file) return;
    setGlobalError('');
    setGlobalLoading(true);

    let docId = documentId;

    // Step 1: Upload
    if (!docId) {
      setStepState('upload', { status: 'running' });
      try {
        const res = await uploadDocument(file, docType, title || undefined);
        docId = res.document_id;
        setDocumentId(docId);
        setStepState('upload', {
          status: 'done',
          message: `Uploaded "${res.title}" — ${res.extracted_text_length.toLocaleString()} chars extracted`,
        });
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Upload failed.';
        setStepState('upload', { status: 'error', message: msg });
        setGlobalError(msg);
        setGlobalLoading(false);
        return;
      }
    }

    // Step 2: Process (chunk)
    setStepState('process', { status: 'running' });
    try {
      const res = await processDocument(docId!);
      setStepState('process', {
        status: 'done',
        message: res.message,
      });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Processing failed.';
      setStepState('process', { status: 'error', message: msg });
      setGlobalError(msg);
      setGlobalLoading(false);
      return;
    }

    // Step 3: Embed
    setStepState('embed', { status: 'running' });
    try {
      const res = await embedDocument(docId!);
      setStepState('embed', {
        status: 'done',
        message: res.message,
      });
      setStepState('done', { status: 'done' });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Embedding failed.';
      setStepState('embed', { status: 'error', message: msg });
      setGlobalError(msg);
    } finally {
      setGlobalLoading(false);
    }
  };

  const allDone = steps.done.status === 'done';

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Upload className="h-7 w-7 text-cyber-400" />
          <h1 className="text-3xl font-bold text-white">Upload Document</h1>
        </div>
        <p className="text-slate-400">
          Upload a PDF, DOCX, or TXT file. The pipeline will extract text → chunk → embed into the FAISS index automatically.
        </p>
      </div>

      {/* Config Form */}
      {!allDone && (
        <div className="mb-6 space-y-5 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          {/* File Drop Zone */}
          <div>
            <label
              htmlFor="file-input"
              onDrop={handleFileDrop}
              onDragOver={(e) => e.preventDefault()}
              className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-slate-700 bg-slate-800/30 px-6 py-10 text-center transition hover:border-cyber-600 hover:bg-slate-800/60"
            >
              {file ? (
                <>
                  <FileText className="h-10 w-10 text-cyber-400" />
                  <div>
                    <p className="font-semibold text-white">{file.name}</p>
                    <p className="text-sm text-slate-400">
                      {(file.size / 1024).toFixed(1)} KB · Click to change
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <Upload className="h-10 w-10 text-slate-500" />
                  <div>
                    <p className="font-medium text-slate-300">Drop file here or click to browse</p>
                    <p className="text-sm text-slate-500">PDF, DOCX, TXT — max 20 MB</p>
                  </div>
                </>
              )}
              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.txt"
                className="sr-only"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>

          {/* Title (optional) */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              Title <span className="text-slate-500">(optional)</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Custom document title (defaults to filename)"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white placeholder-slate-500 outline-none transition focus:border-cyber-500"
            />
          </div>

          {/* Document Type */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">Document Type</label>
            <div className="space-y-2">
              {DOC_TYPES.map(({ value, label, desc }) => (
                <label
                  key={value}
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition ${
                    docType === value
                      ? 'border-cyber-600 bg-cyber-600/10'
                      : 'border-slate-700 bg-slate-800/30 hover:border-slate-600'
                  }`}
                >
                  <input
                    type="radio"
                    name="docType"
                    value={value}
                    checked={docType === value}
                    onChange={() => setDocType(value)}
                    className="mt-1 accent-cyber-500"
                  />
                  <div>
                    <p className="font-medium text-white">{label}</p>
                    <p className="text-xs text-slate-400">{desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Pipeline Steps */}
      <div className="mb-6 space-y-3">
        {(
          [
            { key: 'upload', label: 'Upload & Extract Text' },
            { key: 'process', label: 'Chunk Document (500-800 words)' },
            { key: 'embed', label: 'Generate Embeddings & Update FAISS Index' },
          ] as { key: Step; label: string }[]
        ).map(({ key, label }) => {
          const state = steps[key];
          return (
            <div
              key={key}
              className={`flex items-start gap-4 rounded-xl border p-4 transition ${
                state.status === 'done'
                  ? 'border-green-800 bg-green-900/10'
                  : state.status === 'running'
                  ? 'border-cyber-700 bg-cyber-900/10'
                  : state.status === 'error'
                  ? 'border-red-800 bg-red-900/10'
                  : 'border-slate-800 bg-slate-900/30'
              }`}
            >
              <div className="mt-0.5">
                {state.status === 'done' && <CheckCircle className="h-5 w-5 text-green-400" />}
                {state.status === 'running' && <Spinner size="sm" />}
                {state.status === 'error' && <AlertTriangle className="h-5 w-5 text-red-400" />}
                {state.status === 'idle' && (
                  <div className="h-5 w-5 rounded-full border-2 border-slate-600" />
                )}
              </div>
              <div>
                <p className="font-medium text-white text-sm">{label}</p>
                {state.message && (
                  <p className={`mt-1 text-xs ${state.status === 'error' ? 'text-red-300' : 'text-slate-400'}`}>
                    {state.message}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Global error */}
      {globalError && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-red-800 bg-red-900/20 p-4">
          <AlertTriangle className="h-5 w-5 text-red-400" />
          <p className="text-sm text-red-300">{globalError}</p>
        </div>
      )}

      {/* Actions */}
      {allDone ? (
        <div className="space-y-3 rounded-2xl border border-green-800 bg-green-900/10 p-6 text-center">
          <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
          <p className="text-lg font-bold text-white">Document Ready!</p>
          <p className="text-sm text-slate-400">
            The document has been uploaded, chunked, and embedded into the FAISS index.
          </p>
          <div className="flex gap-3 justify-center mt-4">
            <button
              onClick={() => navigate(`/documents/${documentId}`)}
              className="rounded-lg bg-cyber-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-cyber-700 transition"
            >
              View Document
            </button>
            <button
              onClick={() => {
                setFile(null);
                setTitle('');
                setDocumentId(null);
                setSteps({ upload: { status: 'idle' }, process: { status: 'idle' }, embed: { status: 'idle' }, done: { status: 'idle' } });
              }}
              className="rounded-lg border border-slate-700 px-5 py-2.5 text-sm font-semibold text-slate-300 hover:border-slate-500 hover:text-white transition"
            >
              Upload Another
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={runPipeline}
          disabled={!file || globalLoading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyber-600 py-3.5 font-semibold text-white transition hover:bg-cyber-700 disabled:opacity-50"
        >
          {globalLoading ? <Spinner size="sm" /> : <ChevronRight className="h-5 w-5" />}
          {globalLoading ? 'Processing…' : 'Run Pipeline (Upload → Chunk → Embed)'}
        </button>
      )}
    </div>
  );
};

export default DocumentUploadPage;
