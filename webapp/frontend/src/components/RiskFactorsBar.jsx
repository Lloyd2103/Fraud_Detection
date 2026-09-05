import React from 'react';

export default function RiskFactorsBar({ factors = [] }) {
  return (
    <div style={{ marginTop: '1rem' }}>
      <h4 style={{ fontSize: '0.95rem', marginBottom: '0.75rem', color: '#fff' }}>
        🚨 Top Contributing Risk Factors (GBT Explanation)
      </h4>
      {factors.map((f, i) => (
        <div key={i} style={{ marginBottom: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
            <span style={{ color: '#fff', fontWeight: 500 }}>{f.name}</span>
            <span style={{ color: '#ef4444', fontWeight: 700 }}>{(f.weight * 100).toFixed(0)}% impact</span>
          </div>
          <div style={{ width: '100%', height: '8px', background: '#1e293b', borderRadius: '9999px', overflow: 'hidden' }}>
            <div 
              style={{ 
                width: `${f.weight * 100}%`, 
                height: '100%', 
                background: f.severity === 'CRITICAL' ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #3b82f6, #f59e0b)',
                borderRadius: '9999px'
              }}
            />
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
            {f.description} • Value: <span style={{ color: '#cbd5e1' }}>{f.value}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
