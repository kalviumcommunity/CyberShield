import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getHealth } from '../api/health';
import { getDocuments } from '../api/documents';
import type { HealthResponse } from '../types';
import {
  Shield,
  FileText,
  ShieldAlert,
  Database,
  Activity,
  ChevronRight,
} from 'lucide-react';
import Spinner from '../components/ui/Spinner';

const DashboardPage: React.FC = () => {
  const { user, isAdmin } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [docCount, setDocCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getHealth().catch(() => null),
      getDocuments(0, 100).catch(() => []),
    ]).then(([h, docs]) => {
      setHealth(h);
      setDocCount(Array.isArray(docs) ? docs.length : 0);
      setLoading(false);
    });
  }, []);

  const indexedChunks = health?.vector_index?.indexed_chunks ?? 0;
  const dbStatus = health?.database ?? 'unknown';
  const faissStatus = health?.vector_index?.status ?? 'unknown';

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">
          Welcome back, {user?.name?.split(' ')[0]} 👋
        </h1>
        <p className="mt-1 text-slate-400">
          {isAdmin ? 'Admin console — manage documents and the FAISS index.' : 'Analyst console — submit alerts and retrieve mitigation guidance.'}
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          {/* Stats cards */}
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={<FileText className="h-5 w-5 text-blue-400" />}
              label="Documents"
              value={docCount ?? 0}
              bg="bg-blue-900/20 border-blue-800/50"
            />
            <StatCard
              icon={<Shield className="h-5 w-5 text-cyber-400" />}
              label="Indexed Chunks"
              value={indexedChunks}
              bg="bg-cyber-900/20 border-cyber-800/50"
            />
            <StatCard
              icon={<Database className="h-5 w-5 text-green-400" />}
              label="Database"
              value={dbStatus}
              bg="bg-green-900/20 border-green-800/50"
              isText
            />
            <StatCard
              icon={<Activity className="h-5 w-5 text-purple-400" />}
              label="FAISS Index"
              value={faissStatus}
              bg="bg-purple-900/20 border-purple-800/50"
              isText
            />
          </div>

          {/* System Health Banner */}
          {health && (
            <div
              className={`mb-8 flex items-center gap-3 rounded-xl border px-5 py-4 ${
                health.status === 'healthy'
                  ? 'border-green-800 bg-green-900/20'
                  : 'border-red-800 bg-red-900/20'
              }`}
            >
              <div
                className={`h-2.5 w-2.5 rounded-full ${
                  health.status === 'healthy' ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`}
              />
              <p className="text-sm text-slate-300">
                <span className="font-semibold text-white">{health.app}</span> —{' '}
                {health.message}
              </p>
            </div>
          )}

          {/* Quick Actions */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <QuickAction
              to="/mitigation"
              icon={<ShieldAlert className="h-6 w-6 text-red-400" />}
              title="Submit Security Alert"
              desc="Enter an active threat alert and get AI-grounded mitigation steps."
            />
            <QuickAction
              to="/documents"
              icon={<FileText className="h-6 w-6 text-blue-400" />}
              title="Browse Documents"
              desc="View uploaded threat intelligence, runbooks, and advisories."
            />
            {isAdmin && (
              <QuickAction
                to="/documents/upload"
                icon={<Shield className="h-6 w-6 text-cyber-400" />}
                title="Upload Document"
                desc="Upload a new PDF, DOCX, or TXT document and run the processing pipeline."
              />
            )}
          </div>
        </>
      )}
    </div>
  );
};

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  bg: string;
  isText?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, bg, isText }) => (
  <div className={`rounded-xl border p-5 ${bg}`}>
    <div className="mb-3">{icon}</div>
    <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</p>
    <p className={`mt-1 font-bold text-white capitalize ${isText ? 'text-base' : 'text-2xl'}`}>
      {value}
    </p>
  </div>
);

interface QuickActionProps {
  to: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
}

const QuickAction: React.FC<QuickActionProps> = ({ to, icon, title, desc }) => (
  <Link
    to={to}
    className="group flex items-start gap-4 rounded-xl border border-slate-800 bg-slate-800/30 p-5 transition hover:border-slate-600 hover:bg-slate-800/60"
  >
    <div className="mt-0.5">{icon}</div>
    <div className="flex-1">
      <p className="font-semibold text-white group-hover:text-cyber-300 transition-colors">
        {title}
      </p>
      <p className="mt-1 text-sm text-slate-400">{desc}</p>
    </div>
    <ChevronRight className="mt-1 h-4 w-4 text-slate-500 group-hover:text-slate-300 transition-colors" />
  </Link>
);

export default DashboardPage;
