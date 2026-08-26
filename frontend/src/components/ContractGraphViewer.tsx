import React, { useState } from 'react';
import { GitGraph, CheckCircle, AlertCircle, RefreshCw, FileText, Database, Server, Layout, CheckSquare, Info } from 'lucide-react';
import { ContractGraphData, ContractNode } from '../types';

interface ContractGraphViewerProps {
  graphData: ContractGraphData;
  onResetDemo: () => void;
}

export const ContractGraphViewer: React.FC<ContractGraphViewerProps> = ({ graphData, onResetDemo }) => {
  const [selectedNode, setSelectedNode] = useState<ContractNode | null>(null);

  // Group nodes by layer
  const layers = ['Requirement', 'Frontend', 'API', 'Backend', 'Database', 'Test'];
  const nodesByLayer: Record<string, ContractNode[]> = {};
  layers.forEach((l) => { nodesByLayer[l] = []; });

  graphData.nodes.forEach((node) => {
    const layer = node.layer || 'General';
    if (!nodesByLayer[layer]) nodesByLayer[layer] = [];
    nodesByLayer[layer].push(node);
  });

  const getLayerIcon = (layer: string) => {
    switch (layer.toLowerCase()) {
      case 'requirement': return <FileText size={14} color="#a78bfa" />;
      case 'frontend': return <Layout size={14} color="#22d3ee" />;
      case 'api': return <Server size={14} color="#fbbf24" />;
      case 'backend': return <Server size={14} color="#34d399" />;
      case 'database': return <Database size={14} color="#f43f5e" />;
      case 'test': return <CheckSquare size={14} color="#10b981" />;
      default: return <GitGraph size={14} color="#9ca3af" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'violated':
        return <span className="badge badge-danger" style={{ fontSize: '0.6rem' }}><AlertCircle size={10} /> VIOLATION</span>;
      case 'modified':
        return <span className="badge badge-warning" style={{ fontSize: '0.6rem' }}>MODIFIED</span>;
      default:
        return <span className="badge badge-success" style={{ fontSize: '0.6rem' }}><CheckCircle size={10} /> SYNCED</span>;
    }
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '14px 18px',
        borderBottom: '1px solid var(--border-card)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitGraph size={18} color="#a78bfa" />
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Cross-Layer Contract Graph</h2>
          <span className="badge badge-accent" style={{ fontSize: '0.65rem' }}>
            {graphData.nodes.length} Nodes • {graphData.edges.length} Edges
          </span>
        </div>

        <button onClick={onResetDemo} className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
          <RefreshCw size={13} />
          <span>Reset Demo</span>
        </button>
      </div>

      {/* Main Graph Grid / Multi-Tier Swimlanes */}
      <div style={{
        flex: 1,
        overflowX: 'auto',
        overflowY: 'auto',
        padding: '16px',
        display: 'grid',
        gridTemplateColumns: `repeat(${layers.length}, minmax(160px, 1fr))`,
        gap: '12px',
        background: 'radial-gradient(ellipse at top, rgba(139, 92, 246, 0.05) 0%, transparent 70%)',
      }}>
        {layers.map((layerName) => {
          const layerNodes = nodesByLayer[layerName] || [];
          return (
            <div
              key={layerName}
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                padding: '12px 10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              {/* Layer Title */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                paddingBottom: '8px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
              }}>
                {getLayerIcon(layerName)}
                <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
                  {layerName}
                </span>
              </div>

              {/* Node Cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {layerNodes.map((node) => {
                  const isSelected = selectedNode?.id === node.id;
                  return (
                    <div
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      className="glass-panel-interactive"
                      style={{
                        padding: '10px',
                        borderRadius: '8px',
                        background: isSelected ? 'rgba(6, 182, 212, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                        border: `1px solid ${isSelected ? 'var(--primary)' : 'rgba(255, 255, 255, 0.08)'}`,
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ffffff' }}>
                          {node.name}
                        </span>
                        {getStatusBadge(node.status)}
                      </div>

                      <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-subtle)', wordBreak: 'break-all' }}>
                        {node.id}
                      </div>
                    </div>
                  );
                })}

                {layerNodes.length === 0 && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)', textAlign: 'center', padding: '12px 0' }}>
                    No nodes
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div style={{
          padding: '14px 18px',
          borderTop: '1px solid var(--border-card)',
          background: 'rgba(0, 0, 0, 0.4)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Info size={16} color="#22d3ee" />
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>
                {selectedNode.name}
              </span>
              <span className="badge badge-accent" style={{ fontSize: '0.65rem' }}>{selectedNode.layer}</span>
            </div>
            <div className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Metadata: {JSON.stringify(selectedNode.metadata)}
            </div>
          </div>

          <button onClick={() => setSelectedNode(null)} className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
            Close
          </button>
        </div>
      )}
    </div>
  );
};
