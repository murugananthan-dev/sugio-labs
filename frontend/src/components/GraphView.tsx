import React, { useState } from 'react';
import {
  Network,
  Layers,
  RefreshCw,
  Info,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Database,
  Terminal,
  Cpu,
  TestTube,
} from 'lucide-react';
import { ContractGraphData, ContractNode } from '../types';

interface GraphViewProps {
  graph: ContractGraphData | null;
  onRefresh: () => void;
  onResetSample: () => void;
  loading: boolean;
}

export const GraphView: React.FC<GraphViewProps> = ({
  graph,
  onRefresh,
  onResetSample,
  loading,
}) => {
  const [selectedNode, setSelectedNode] = useState<ContractNode | null>(null);
  const [filterLayer, setFilterLayer] = useState<string>('all');

  const layers = ['Requirement', 'Frontend', 'API', 'Backend', 'Database', 'Test'];

  const getLayerColor = (layer: string) => {
    switch (layer.toLowerCase()) {
      case 'requirement':
        return 'border-purple-500/50 bg-purple-950/30 text-purple-300';
      case 'frontend':
        return 'border-blue-500/50 bg-blue-950/30 text-blue-300';
      case 'api':
        return 'border-cyan-500/50 bg-cyan-950/30 text-cyan-300';
      case 'backend':
        return 'border-indigo-500/50 bg-indigo-950/30 text-indigo-300';
      case 'database':
        return 'border-emerald-500/50 bg-emerald-950/30 text-emerald-300';
      case 'test':
        return 'border-amber-500/50 bg-amber-950/30 text-amber-300';
      default:
        return 'border-slate-700 bg-slate-900 text-slate-300';
    }
  };

  const getLayerIcon = (layer: string) => {
    switch (layer.toLowerCase()) {
      case 'requirement':
        return <Layers className="w-4 h-4 text-purple-400" />;
      case 'frontend':
        return <FileCode className="w-4 h-4 text-blue-400" />;
      case 'api':
        return <Terminal className="w-4 h-4 text-cyan-400" />;
      case 'backend':
        return <Cpu className="w-4 h-4 text-indigo-400" />;
      case 'database':
        return <Database className="w-4 h-4 text-emerald-400" />;
      case 'test':
        return <TestTube className="w-4 h-4 text-amber-400" />;
      default:
        return <Network className="w-4 h-4 text-slate-400" />;
    }
  };

  const filteredNodes =
    graph?.nodes.filter(
      (n) => filterLayer === 'all' || n.layer.toLowerCase() === filterLayer.toLowerCase()
    ) || [];

  return (
    <div className="max-w-6xl mx-auto my-6 space-y-6">
      {/* Top Controls Bar */}
      <div className="glass-panel p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center">
            <Network className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Cross-Layer Contract Graph</h3>
            <p className="text-xs text-slate-400">
              {graph?.nodes.length || 0} nodes • {graph?.edges.length || 0} dependency edges
            </p>
          </div>
        </div>

        {/* Layer Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-900/80 p-1 rounded-xl border border-white/5">
          <button
            onClick={() => setFilterLayer('all')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              filterLayer === 'all' ? 'bg-white/10 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Layers
          </button>
          {layers.map((l) => (
            <button
              key={l}
              onClick={() => setFilterLayer(l)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                filterLayer.toLowerCase() === l.toLowerCase()
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button onClick={onRefresh} disabled={loading} className="btn-secondary text-xs">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </button>
          <button onClick={onResetSample} className="btn-primary text-xs">
            <span>Reset Demo Graph</span>
          </button>
        </div>
      </div>

      {/* Main Graph Grid & Details View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Visual Layered Node Cards */}
        <div className="lg:col-span-2 space-y-4">
          {layers
            .filter((l) => filterLayer === 'all' || filterLayer.toLowerCase() === l.toLowerCase())
            .map((layerName) => {
              const layerNodes = graph?.nodes.filter(
                (n) => n.layer.toLowerCase() === layerName.toLowerCase()
              ) || [];

              if (layerNodes.length === 0) return null;

              return (
                <div key={layerName} className="glass-panel p-4">
                  <div className="flex items-center gap-2 mb-3">
                    {getLayerIcon(layerName)}
                    <span className="text-xs font-mono uppercase font-bold tracking-wider text-slate-300">
                      {layerName} Layer
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      ({layerNodes.length} contract node{layerNodes.length > 1 ? 's' : ''})
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {layerNodes.map((node) => {
                      const isSelected = selectedNode?.id === node.id;
                      return (
                        <div
                          key={node.id}
                          onClick={() => setSelectedNode(node)}
                          className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                            getLayerColor(node.layer)
                          } ${
                            isSelected
                              ? 'ring-2 ring-cyan-400 shadow-lg shadow-cyan-500/20 scale-[1.02]'
                              : 'hover:border-white/30'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="font-mono text-xs font-bold truncate text-white">
                              {node.name}
                            </span>
                            <span className="pill pill-emerald text-[9px] py-0.5 px-2">
                              {node.status}
                            </span>
                          </div>
                          <span className="font-mono text-[10px] text-slate-400 block truncate">
                            {node.id}
                          </span>

                          {/* Preview Fields / Methods */}
                          {node.metadata.fields && (
                            <div className="mt-2 text-[10px] font-mono text-slate-300 bg-slate-950/60 p-1.5 rounded border border-white/5">
                              <span className="text-slate-500">fields: </span>
                              {Object.keys(node.metadata.fields).join(', ')}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
        </div>

        {/* Selected Node Details & Connected Edges Inspector */}
        <div className="glass-panel p-5 h-fit sticky top-24">
          <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-3">
            <Info className="w-4 h-4 text-cyan-400" />
            <h4 className="text-sm font-bold text-white">Contract Node Inspector</h4>
          </div>

          {selectedNode ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-400">Node Identifier</span>
                <p className="text-xs font-mono font-bold text-cyan-300 break-all">{selectedNode.id}</p>
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase text-slate-400">Name & Layer</span>
                <p className="text-sm font-semibold text-white">{selectedNode.name}</p>
                <span className="pill pill-indigo text-[10px] mt-1">{selectedNode.layer}</span>
              </div>

              {/* Inbound & Outbound Edges */}
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-400">Dependency Links</span>
                <div className="mt-2 space-y-1.5">
                  {graph?.edges
                    .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                    .map((e, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-slate-900 border border-white/5 text-[11px] font-mono text-slate-300"
                      >
                        <span className="text-indigo-400">{e.source}</span>
                        <span className="text-slate-500"> ➔ ({e.relation_type}) ➔ </span>
                        <span className="text-cyan-400">{e.target}</span>
                      </div>
                    ))}
                </div>
              </div>

              {/* Raw Node Metadata */}
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-400">Metadata Payload</span>
                <pre className="code-block text-[11px] mt-1 max-h-60 overflow-y-auto">
                  {JSON.stringify(selectedNode.metadata, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500 text-xs">
              Click any node in the Contract Graph above to inspect its fields, dependencies, and schema contracts.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
