import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  History,
  RotateCcw,
  Plus,
  Terminal,
  FileDiff,
  CheckCircle,
  AlertTriangle,
  Play,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import { GitCheckpoint } from '../types';
import {
  fetchCheckpoints,
  createCheckpoint,
  rollbackToCheckpoint,
  fetchGitDiff,
  executeShellCommand,
} from '../services/api';

interface GitSafetyViewProps {
  onSpeak?: (text: string) => void;
}

export const GitSafetyView: React.FC<GitSafetyViewProps> = ({ onSpeak }) => {
  const [checkpoints, setCheckpoints] = useState<GitCheckpoint[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [newCheckpointName, setNewCheckpointName] = useState<string>('');
  const [newCheckpointDesc, setNewCheckpointDesc] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);

  // Diff & Shell State
  const [diffContent, setDiffContent] = useState<string>('');
  const [shellCommand, setShellCommand] = useState<string>('python -m pytest backend/tests');
  const [shellOutput, setShellOutput] = useState<string>('');
  const [shellRunning, setShellRunning] = useState<boolean>(false);
  const [activeSubTab, setActiveSubTab] = useState<'checkpoints' | 'diff' | 'terminal'>('checkpoints');

  const loadData = async () => {
    setLoading(true);
    try {
      const [cps, d] = await Promise.all([
        fetchCheckpoints().catch(() => []),
        fetchGitDiff().catch(() => ({ diff: '' })),
      ]);
      setCheckpoints(cps);
      setDiffContent(d.diff || 'Workspace is synchronized with latest checkpoint.');
    } catch (e) {
      console.error('Error loading git data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateCheckpoint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCheckpointName.trim()) return;

    try {
      const res = await createCheckpoint(newCheckpointName, newCheckpointDesc);
      setCheckpoints((prev) => [...prev, res.checkpoint]);
      setShowCreateModal(false);
      setNewCheckpointName('');
      setNewCheckpointDesc('');
      if (onSpeak) onSpeak(`Safety checkpoint ${newCheckpointName} created successfully.`);
    } catch (err: any) {
      alert(`Failed to create checkpoint: ${err.message}`);
    }
  };

  const handleRollback = async (checkpointId: string) => {
    if (!window.confirm(`Are you sure you want to rollback to checkpoint ${checkpointId}? Any unsaved changes will be discarded.`)) {
      return;
    }
    try {
      await rollbackToCheckpoint(checkpointId);
      loadData();
      if (onSpeak) onSpeak(`Rolled back successfully to checkpoint ${checkpointId}.`);
    } catch (err: any) {
      alert(`Rollback failed: ${err.message}`);
    }
  };

  const handleRunShell = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shellCommand.trim()) return;
    setShellRunning(true);
    setShellOutput(`Executing in sandbox: ${shellCommand}...\n`);

    try {
      const res = await executeShellCommand(shellCommand);
      const output = `Exit Code: ${res.exit_code} (Elapsed: ${res.elapsed_seconds}s)\n\nSTDOUT:\n${res.stdout}\n\nSTDERR:\n${res.stderr}`;
      setShellOutput(output);
    } catch (err: any) {
      setShellOutput(`Execution Failed / Permission Rejected:\n${err.message}`);
    } finally {
      setShellRunning(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto my-6 space-y-6">
      {/* Header Banner */}
      <div className="glass-panel p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white">Git Safety & Checkpoints</h2>
              <span className="pill pill-emerald text-xs">Automated Rollback Protection</span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Instant snapshot checkpoints before multi-file modifications and automated rollback on test failures.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary text-xs"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Create Safety Snapshot</span>
        </button>
      </div>

      {/* Sub Tabs */}
      <div className="flex border-b border-white/10 gap-2">
        {[
          { id: 'checkpoints', label: `Saved Checkpoints (${checkpoints.length})` },
          { id: 'diff', label: 'Sandbox Working Diff' },
          { id: 'terminal', label: 'Sandboxed Test Terminal' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id as any)}
            className={`pb-2.5 px-3 text-xs font-medium transition-all ${
              activeSubTab === tab.id
                ? 'border-b-2 border-indigo-500 text-white font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Contents */}
      <div className="glass-panel p-6">
        {activeSubTab === 'checkpoints' && (
          <div className="space-y-4">
            {checkpoints.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-xs">
                No checkpoints created yet. Click "Create Safety Snapshot" to save the current repository state.
              </div>
            ) : (
              <div className="space-y-3">
                {checkpoints.map((cp) => (
                  <div
                    key={cp.id}
                    className="p-4 rounded-xl bg-slate-900/80 border border-white/5 hover:border-white/15 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-cyan-300">{cp.id}</span>
                        <span className="text-sm font-semibold text-white">{cp.name}</span>
                      </div>
                      <p className="text-xs text-slate-400">{cp.description || 'Automated pre-execution checkpoint.'}</p>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 pt-1">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(cp.timestamp).toLocaleString()}</span>
                        <span>•</span>
                        <span>Commit: {cp.commit_hash.substring(0, 8)}</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleRollback(cp.id)}
                      className="btn-danger text-xs"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Rollback to this state</span>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSubTab === 'diff' && (
          <div className="space-y-3">
            <h4 className="text-xs font-mono uppercase text-slate-400">Current Sandbox Diff (HEAD)</h4>
            <pre className="code-block text-xs max-h-96 overflow-y-auto">
              {diffContent}
            </pre>
          </div>
        )}

        {activeSubTab === 'terminal' && (
          <div className="space-y-4">
            <form onSubmit={handleRunShell} className="flex gap-2">
              <input
                type="text"
                value={shellCommand}
                onChange={(e) => setShellCommand(e.target.value)}
                placeholder="e.g. pytest backend/tests, npm test, git status"
                className="flex-1 p-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs font-mono text-cyan-300 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="submit"
                disabled={shellRunning}
                className="btn-primary text-xs"
              >
                <Play className={`w-3.5 h-3.5 ${shellRunning ? 'animate-spin' : ''}`} />
                <span>{shellRunning ? 'Running...' : 'Run in Sandbox'}</span>
              </button>
            </form>

            <pre className="code-block text-xs font-mono min-h-[160px] max-h-96 overflow-y-auto text-emerald-400">
              {shellOutput || 'Ready. Enter a command above to execute within the project sandbox with zero-trust permission gating.'}
            </pre>
          </div>
        )}
      </div>

      {/* Modal: Create Checkpoint */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="glass-modal max-w-md w-full p-6 border border-indigo-500/30">
            <h3 className="text-base font-bold text-white mb-2">Create Safety Snapshot</h3>
            <p className="text-xs text-slate-400 mb-4">
              Snapshot current codebase state into Git registry for instant rollback protection.
            </p>

            <form onSubmit={handleCreateCheckpoint} className="space-y-3">
              <div>
                <label className="text-xs font-mono uppercase text-slate-300 block mb-1">
                  Checkpoint Name:
                </label>
                <input
                  type="text"
                  value={newCheckpointName}
                  onChange={(e) => setNewCheckpointName(e.target.value)}
                  placeholder="e.g. Before Student Model Migration"
                  required
                  className="w-full p-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-mono uppercase text-slate-300 block mb-1">
                  Description / Context:
                </label>
                <textarea
                  value={newCheckpointDesc}
                  onChange={(e) => setNewCheckpointDesc(e.target.value)}
                  placeholder="Details on the changes about to be made..."
                  rows={2}
                  className="w-full p-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary text-xs">
                  Save Checkpoint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
