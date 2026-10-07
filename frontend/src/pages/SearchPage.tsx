import { useState } from 'react';
import { semanticSearch } from '../api/search';
import type { SearchResultItem } from '../types';
import Spinner from '../components/ui/Spinner';
import { Search, AlertTriangle, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setError('');
    setLoading(true);
    setSearched(false);
    try {
      const data = await semanticSearch(query.trim(), topK);
      setResults(data);
      setSearched(true);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Search failed. Ensure the backend is running and the FAISS index is built.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Search className="h-7 w-7 text-cyber-400" />
          <h1 className="text-3xl font-bold text-white">Semantic Search</h1>
        </div>
        <p className="text-slate-400">
          Run a dense vector similarity search across all embedded document chunks using FAISS.
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. How to block SSH brute force attack?"
              className="w-full rounded-xl border border-slate-700 bg-slate-900 py-3.5 pl-12 pr-4 text-white placeholder-slate-500 outline-none transition focus:border-cyber-500 focus:ring-1 focus:ring-cyber-500"
            />
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4">
            <span className="text-xs text-slate-400 whitespace-nowrap">Top</span>
            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-12 bg-transparent text-center text-white outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="flex items-center gap-2 rounded-xl bg-cyber-600 px-6 py-3 font-semibold text-white transition hover:bg-cyber-700 disabled:opacity-50"
          >
            {loading ? <Spinner size="sm" /> : <Search className="h-4 w-4" />}
            {loading ? 'Searching…' : 'Search'}
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
      {searched && results.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 py-16 text-center">
          <Search className="mx-auto mb-3 h-10 w-10 text-slate-600" />
          <p className="text-slate-400">No results found for your query.</p>
          <p className="mt-1 text-sm text-slate-500">
            Try uploading and embedding documents first, or adjust your query.
          </p>
        </div>
      )}

      {results.length > 0 && (
        <div>
          <p className="mb-4 text-sm text-slate-400">
            {results.length} chunk{results.length !== 1 ? 's' : ''} found
          </p>
          <div className="space-y-4">
            {results.map((item, i) => (
              <div
                key={item.chunk_id}
                className="rounded-xl border border-slate-800 bg-slate-900 p-5 hover:border-slate-700 transition"
              >
                <div className="mb-3 flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-slate-500 font-semibold">#{i + 1}</span>
                      <Link
                        to={`/documents/${item.document_id}`}
                        className="font-semibold text-white hover:text-cyber-300 transition inline-flex items-center gap-1"
                      >
                        {item.document_title}
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Chunk #{item.chunk_id} · Doc #{item.document_id}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-green-400">
                      {(item.similarity_score * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-slate-500">similarity</p>
                  </div>
                </div>

                {/* Score bar */}
                <div className="mb-3 h-1.5 w-full rounded-full bg-slate-800">
                  <div
                    className="h-1.5 rounded-full bg-green-500 transition-all"
                    style={{ width: `${Math.min(item.similarity_score * 100, 100)}%` }}
                  />
                </div>

                <p className="text-sm leading-relaxed text-slate-300 font-mono bg-slate-800/50 rounded-lg p-3">
                  {item.chunk_content.length > 400
                    ? item.chunk_content.slice(0, 400) + '…'
                    : item.chunk_content}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
