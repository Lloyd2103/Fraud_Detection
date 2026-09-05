import React from 'react';

export default function AlertTable({ alerts = [], onSelectTx }) {
  if (!alerts.length) {
    return (
      <div style={{ textAlign: 'center', padding: '2.5rem', color: '#94a3b8' }}>
        No alerts found matching current filter.
      </div>
    );
  }

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead>
          <tr style={{ background: 'rgba(30, 41, 59, 0.5)', color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase' }}>
            <th style={{ padding: '0.75rem 1rem' }}>Tx ID</th>
            <th style={{ padding: '0.75rem 1rem' }}>Timestamp</th>
            <th style={{ padding: '0.75rem 1rem' }}>Source ➔ Dest</th>
            <th style={{ padding: '0.75rem 1rem' }}>Channel / Type</th>
            <th style={{ padding: '0.75rem 1rem' }}>Amount</th>
            <th style={{ padding: '0.75rem 1rem' }}>Risk Score</th>
            <th style={{ padding: '0.75rem 1rem' }}>Status</th>
            <th style={{ padding: '0.75rem 1rem' }}>Action</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map(tx => {
            const score = parseFloat(tx.risk_score || 0);
            const scorePct = (score * 100).toFixed(1);
            const isProcessed = tx.inspection_status === 'PROCESSED';
            const formattedAmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.amount || 0);

            return (
              <tr key={tx.transaction_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', fontWeight: 600, color: '#fff' }}>
                  {tx.transaction_id}
                </td>
                <td style={{ padding: '0.75rem 1rem', fontSize: '0.82rem', color: '#94a3b8' }}>
                  {tx.timestamp}
                </td>
                <td style={{ padding: '0.75rem 1rem', fontSize: '0.82rem', fontFamily: 'monospace' }}>
                  {tx.source_account} ➔ {tx.dest_account}
                </td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  <span style={{ background: '#1e293b', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem' }}>
                    {tx.channel || 'ONLINE'}
                  </span>
                </td>
                <td style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>{formattedAmt}</td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  <span style={{ 
                    padding: '0.2rem 0.6rem', 
                    borderRadius: '9999px', 
                    fontWeight: 700, 
                    fontSize: '0.78rem',
                    background: score >= 0.8 ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)',
                    color: score >= 0.8 ? '#fca5a5' : '#fcd34d'
                  }}>
                    {scorePct}%
                  </span>
                </td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  {isProcessed ? (
                    <span style={{ color: '#10b981', fontSize: '0.78rem' }}>✓ Inspected</span>
                  ) : (
                    <span style={{ color: '#ef4444', fontSize: '0.78rem' }}>Pending Review</span>
                  )}
                </td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  <button 
                    onClick={() => onSelectTx(tx.transaction_id)}
                    style={{ 
                      background: '#3b82f6', 
                      color: '#fff', 
                      border: 'none', 
                      padding: '0.35rem 0.75rem', 
                      borderRadius: '6px', 
                      cursor: 'pointer',
                      fontSize: '0.8rem'
                    }}
                  >
                    🔍 Inspect
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
