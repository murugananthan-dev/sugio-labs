import React from 'react';
import { Activity, Clock, CheckCircle2, AlertCircle, Loader2, ShieldAlert } from 'lucide-react';
import { AgentActivityLog } from '../types';

interface ActivityTimelineProps {
  logs: AgentActivityLog[];
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({ logs }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'running':
        return <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />;
      case 'waiting_permission':
        return <ShieldAlert className="w-3.5 h-3.5 text-amber-400 animate-pulse" />;
      default:
        return <AlertCircle className="w-3.5 h-3.5 text-rose-400" />;
    }
  };

  const getStatusPill = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="pill pill-emerald text-[9px] py-0.5 px-2">Done</span>;
      case 'running':
        return <span className="pill pill-indigo text-[9px] py-0.5 px-2">Active</span>;
      case 'waiting_permission':
        return <span className="pill pill-amber text-[9px] py-0.5 px-2">Gate</span>;
      default:
        return <span className="pill pill-rose text-[9px] py-0.5 px-2">Failed</span>;
    }
  };

  if (logs.length === 0) {
    return (
      <div className="glass-panel p-4 text-center text-xs text-slate-500">
        No agent actions recorded in this session. Start the wizard or trigger an action to view live activity.
      </div>
    );
  }

  return (
    <div className="glass-panel p-4 max-h-96 overflow-y-auto space-y-3">
      <div className="flex items-center justify-between border-b border-white/10 pb-2 mb-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
            Agent Activity Timeline
          </h4>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">{logs.length} events</span>
      </div>

      <div className="space-y-2.5">
        {logs.slice().reverse().map((log) => (
          <div
            key={log.id}
            className="p-2.5 rounded-xl bg-slate-900/70 border border-white/5 hover:border-white/10 transition-all text-xs"
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-1.5">
                {getStatusIcon(log.status)}
                <span className="font-semibold text-slate-200">{log.step}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {getStatusPill(log.status)}
                <span className="text-[10px] font-mono text-slate-500">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 pl-5 leading-relaxed">{log.details}</p>
            <div className="pl-5 mt-1">
              <span className="text-[9px] font-mono text-indigo-400">@{log.agent_name}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
