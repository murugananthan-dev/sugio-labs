import React, { useEffect, useState } from 'react';
import { SessionSummary } from '../types';
import { fetchSessionHistory } from '../services/api';
import { Folder, Clock, CheckCircle2, XCircle, ArrowRight, Loader2 } from 'lucide-react';

interface SessionHistoryViewProps {
  onClose: () => void;
}

export const SessionHistoryView: React.FC<SessionHistoryViewProps> = ({ onClose }) => {
  const [history, setHistory] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSessionHistory()
      .then((data) => setHistory(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const formatTime = (timeStr: string) => {
    return new Date(timeStr).toLocaleString();
  };

  return (
    <div className="bg-slate-900 border border-white/10 rounded-xl overflow-hidden flex flex-col h-full max-h-[80vh]">
      <div className="p-4 border-b border-white/10 bg-slate-950 flex justify-between items-center">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Clock className="w-5 h-5 text-indigo-400" />
          Project History
        </h2>
        <button onClick={onClose} className="text-slate-400 hover:text-white px-3 py-1 rounded border border-white/10 bg-slate-800">
          Close
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
          </div>
        ) : error ? (
          <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400">
            Failed to load history: {error}
          </div>
        ) : history.length === 0 ? (
          <div className="text-center text-slate-500 py-12">
            <Folder className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p>No project history found.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((session) => (
              <div key={session.session_id} className="p-4 bg-slate-800/50 rounded-lg border border-white/5 hover:border-indigo-500/30 transition-colors">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-sm font-semibold text-slate-200">{session.project_name}</h3>
                  {session.status === 'COMPLETED' ? (
                    <span className="flex items-center gap-1 text-[10px] uppercase font-bold text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded">
                      <CheckCircle2 className="w-3 h-3" /> Completed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] uppercase font-bold text-rose-400 bg-rose-400/10 px-2 py-0.5 rounded">
                      <XCircle className="w-3 h-3" /> {session.status}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mb-2 truncate">
                  {session.workspace_path}
                </p>
                <div className="flex justify-between items-center mt-3 pt-3 border-t border-white/5 text-xs text-slate-500">
                  <span className="font-mono">{formatTime(session.timestamp)}</span>
                  <span className="font-mono bg-slate-900 px-2 py-0.5 rounded">ID: {session.session_id.substring(0, 8)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
