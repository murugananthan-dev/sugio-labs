import React, { useState } from 'react';
import { importWorkspace, createWorkspace } from '../services/api';
import { ProjectWorkspace, ProjectScanResult } from '../types';

interface WorkspaceSetupProps {
  onWorkspaceReady: (ws: ProjectWorkspace, scanResult?: ProjectScanResult) => void;
  onError: (msg: string) => void;
}

export const WorkspaceSetup: React.FC<WorkspaceSetupProps> = ({ onWorkspaceReady, onError }) => {
  const [mode, setMode] = useState<'SELECT' | 'IMPORT' | 'CREATE'>('SELECT');
  const [path, setPath] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);

  const handleImport = async () => {
    if (!path.trim()) {
      onError("Please enter a valid absolute path.");
      return;
    }
    setLoading(true);
    try {
      const res = await importWorkspace(path.trim());
      // Re-create a ProjectWorkspace shape since import returns scan_result
      const ws: ProjectWorkspace = {
        project_id: 'session', // Will be updated by session fetch
        project_name: res.scan_result.project_name,
        root_path: res.scan_result.root_path,
        mode: 'IMPORT_EXISTING',
        detected_stack: { frontend: res.scan_result.frontend_detected ? 'yes' : 'no' },
        git_enabled: res.scan_result.git_status === 'enabled',
        status: 'active'
      };
      onWorkspaceReady(ws, res.scan_result);
    } catch (e: any) {
      onError(e.message || "Failed to import workspace.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!name.trim() || !path.trim()) {
      onError("Please enter both a project name and a parent path.");
      return;
    }
    setLoading(true);
    try {
      const res = await createWorkspace(name.trim(), path.trim());
      onWorkspaceReady(res.workspace);
    } catch (e: any) {
      onError(e.message || "Failed to create workspace.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
      <div className="glass-panel p-8 max-w-lg w-full">
        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
          <span>🚀</span> Workspace Setup
        </h2>
        
        {mode === 'SELECT' && (
          <div className="space-y-4">
            <p className="text-slate-300 text-sm mb-4">
              To begin, create a new project or import an existing codebase into the sandbox.
            </p>
            <button onClick={() => setMode('CREATE')} className="btn-primary w-full justify-center">
              Create New Project
            </button>
            <button onClick={() => setMode('IMPORT')} className="btn-secondary w-full justify-center">
              Import Existing Project
            </button>
          </div>
        )}

        {mode === 'IMPORT' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Absolute Directory Path</label>
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="e.g., C:/Projects/my-app"
                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white font-mono text-sm"
              />
            </div>
            <div className="flex gap-3 pt-4 border-t border-slate-700">
              <button onClick={() => setMode('SELECT')} className="btn-secondary flex-1 justify-center" disabled={loading}>Back</button>
              <button onClick={handleImport} className="btn-primary flex-1 justify-center" disabled={loading}>
                {loading ? 'Importing...' : 'Import'}
              </button>
            </div>
          </div>
        )}

        {mode === 'CREATE' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Project Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="my-new-app"
                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white font-mono text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Parent Directory (Absolute Path)</label>
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="e.g., C:/Projects"
                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white font-mono text-sm"
              />
            </div>
            <div className="flex gap-3 pt-4 border-t border-slate-700">
              <button onClick={() => setMode('SELECT')} className="btn-secondary flex-1 justify-center" disabled={loading}>Back</button>
              <button onClick={handleCreate} className="btn-primary flex-1 justify-center" disabled={loading}>
                {loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
