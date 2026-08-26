import React from 'react';
import { Target, AlertTriangle, CheckCircle, ShieldAlert, Layers, ArrowRight } from 'lucide-react';
import { ImpactReport } from '../types';

interface ImpactViewProps {
  impactReport: ImpactReport | null;
  onClear: () => void;
}

export const ImpactView: React.FC<ImpactViewProps> = ({ impactReport, onClear }) => {
  if (!impactReport) return null;

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'high': return '#fb7185';
      case 'medium': return '#fbbf24';
      default: return '#34d399';
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '18px', border: '1px solid rgba(245, 158, 11, 0.4)', background: 'rgba(245, 158, 11, 0.04)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Target size={20} color="#fbbf24" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>Cross-Layer Impact Analysis</h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge" style={{ background: `${getRiskColor(impactReport.risk_level)}20`, color: getRiskColor(impactReport.risk_level), border: `1px solid ${getRiskColor(impactReport.risk_level)}50` }}>
            Risk: {impactReport.risk_level.toUpperCase()}
          </span>
          <button onClick={onClear} className="btn-secondary" style={{ padding: '2px 8px', fontSize: '0.7rem' }}>
            Dismiss
          </button>
        </div>
      </div>

      {/* Summary */}
      <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginBottom: '14px', lineHeight: 1.5 }}>
        {impactReport.summary}
      </p>

      {/* Tiers Affected Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '8px',
        marginBottom: '16px',
      }}>
        {[
          { label: 'Frontend', count: impactReport.affected_frontend.length, color: '#22d3ee' },
          { label: 'Backend', count: impactReport.affected_backend.length, color: '#34d399' },
          { label: 'APIs', count: impactReport.affected_apis.length, color: '#fbbf24' },
          { label: 'Database', count: impactReport.affected_database.length, color: '#f43f5e' },
          { label: 'Tests', count: impactReport.affected_tests.length, color: '#10b981' },
        ].map((tier, idx) => (
          <div key={idx} style={{
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '8px',
            padding: '8px 10px',
            textAlign: 'center',
            border: '1px solid var(--border-card)',
          }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 800, color: tier.color }}>{tier.count}</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{tier.label}</div>
          </div>
        ))}
      </div>

      {/* Contract Violations Warning */}
      {impactReport.violations && impactReport.violations.length > 0 && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          borderRadius: '8px',
          padding: '12px',
          marginBottom: '14px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#fb7185', fontWeight: 600, fontSize: '0.8rem', marginBottom: '6px' }}>
            <AlertTriangle size={15} />
            <span>Contract Drift Detected</span>
          </div>
          {impactReport.violations.map((v, i) => (
            <p key={i} style={{ fontSize: '0.75rem', color: '#fca5a5', lineHeight: 1.4 }}>
              • {v.description}
            </p>
          ))}
        </div>
      )}

      {/* Explanations List */}
      <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '10px' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
          Detailed Layer Modifications:
        </span>
        <ul style={{ listStyle: 'none', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {impactReport.explanations.map((exp, i) => (
            <li key={i} style={{ fontSize: '0.75rem', color: 'var(--text-main)', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <ArrowRight size={13} color="#22d3ee" style={{ marginTop: '2px', flexShrink: 0 }} />
              <span>{exp}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
