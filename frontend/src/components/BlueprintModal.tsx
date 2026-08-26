import React from 'react';
import { Layers, CheckCircle2, X, Database } from 'lucide-react';
import { ProjectBlueprint } from '../types';

interface BlueprintModalProps {
  blueprint: ProjectBlueprint | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: () => void;
}

export const BlueprintModal: React.FC<BlueprintModalProps> = ({
  blueprint,
  isOpen,
  onClose,
  onApprove,
}) => {
  if (!isOpen || !blueprint) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(5, 8, 15, 0.85)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9000,
      padding: '24px',
    }}>
      <div className="glass-panel" style={{
        maxWidth: '850px',
        width: '100%',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        border: '1px solid rgba(139, 92, 246, 0.4)',
        boxShadow: '0 0 50px rgba(139, 92, 246, 0.2)',
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-card)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #8b5cf6, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Layers size={22} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff' }}>
                  {blueprint.project_name} — Architectural Blueprint
                </h2>
                {blueprint.approved ? (
                  <span className="badge badge-success">Approved</span>
                ) : (
                  <span className="badge badge-warning">Awaiting Approval</span>
                )}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {blueprint.objective}
              </p>
            </div>
          </div>

          <button onClick={onClose} className="btn-secondary" style={{ padding: '6px 10px' }}>
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Selected Stack */}
          <div>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', color: '#a78bfa', marginBottom: '10px' }}>
              Selected Technology Stack
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
              {Object.entries(blueprint.selected_stack).map(([k, v]) => (
                <div key={k} style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-card)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{k}</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#22d3ee' }}>{v}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Features */}
          <div>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', color: '#a78bfa', marginBottom: '10px' }}>
              Planned Features & Roles
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {blueprint.features.map((f, i) => (
                <span key={i} className="badge badge-primary" style={{ textTransform: 'none', fontSize: '0.8rem', padding: '6px 12px' }}>
                  {f}
                </span>
              ))}
            </div>
          </div>

          {/* Database Schema */}
          <div>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', color: '#a78bfa', marginBottom: '10px' }}>
              Database Schema Specification
            </h3>
            {blueprint.db_schema.map((tbl, i) => (
              <div key={i} style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '8px', padding: '14px', border: '1px solid var(--border-card)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#f43f5e', fontWeight: 600 }}>
                  <Database size={16} />
                  <span>Table: {tbl.table}</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {tbl.columns.map((c, ci) => (
                    <div key={ci} className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      • <strong style={{ color: '#ffffff' }}>{c.name}</strong> ({c.type}) — <em>{c.constraints}</em>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* API Endpoints */}
          <div>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', color: '#a78bfa', marginBottom: '10px' }}>
              API Endpoints
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {blueprint.api_endpoints.map((ep, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.03)', padding: '8px 12px', borderRadius: '6px' }}>
                  <span className={`badge ${ep.method === 'POST' ? 'badge-success' : 'badge-primary'}`} style={{ fontSize: '0.65rem' }}>
                    {ep.method}
                  </span>
                  <span className="font-mono" style={{ fontSize: '0.8rem', color: '#ffffff' }}>{ep.path}</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>{ep.description}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border-card)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: '12px',
          background: 'rgba(0, 0, 0, 0.3)',
        }}>
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>

          {!blueprint.approved && (
            <button onClick={onApprove} className="btn-primary">
              <CheckCircle2 size={16} />
              <span>Approve Blueprint & Build Graph</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
