import React from 'react';
import { AlertTriangle } from 'lucide-react';

export default function RiskFactorsBar({ factors = [] }) {
  if (!factors || !factors.length) {
    return (
      <div style={{ marginTop: '0.85rem', color: '#71717a', fontSize: '0.8125rem' }}>
        No critical risk factors flagged for this transaction.
      </div>
    );
  }

  return (
    <div style={{ marginTop: '1rem' }}>
      <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.65rem', color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
        <AlertTriangle size={14} strokeWidth={2} style={{ color: '#d97706' }} />
        <span>Top Risk Contributing Factors (GBT Explanation)</span>
      </h4>
      {factors.slice(0, 3).map((f, i) => {
        const factorName = f.name || f.ten || f.feature_name || `Factor ${i + 1}`;
        const factorWeight = (f.weight !== undefined ? f.weight : (f.dong_gop !== undefined ? f.dong_gop : (f.contribution !== undefined ? f.contribution : 0.3)));
        const severity = f.severity || (factorWeight >= 0.4 ? 'CRITICAL' : 'NORMAL');
        const factorVal = f.value || f.gia_tri || '';
        const factorDesc = f.description || f.mo_ta || '';
        const barWidthPct = Math.min(100, Math.max(10, Math.round(Number(factorWeight) * 100)));

        return (
          <div key={i} style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '0.25rem' }}>
              <span style={{ color: '#09090b', fontWeight: 500 }}>{factorName}</span>
              <span style={{ color: severity === 'CRITICAL' ? '#b91c1c' : '#09090b', fontWeight: 600 }}>
                Relative contribution: {Number(factorWeight).toFixed(2)}
              </span>
            </div>
            <div style={{ width: '100%', height: '6px', backgroundColor: '#f4f4f5', borderRadius: '3px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${barWidthPct}%`,
                  height: '100%',
                  backgroundColor: severity === 'CRITICAL' ? '#ef4444' : '#09090b',
                  borderRadius: '3px'
                }}
              />
            </div>
            <div style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.2rem' }}>
              {factorDesc} {factorVal && `• Value: `}<span style={{ color: '#09090b', fontWeight: 500 }}>{factorVal}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
