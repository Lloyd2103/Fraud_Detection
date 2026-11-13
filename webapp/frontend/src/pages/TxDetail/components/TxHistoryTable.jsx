import React from 'react';

export default function TxHistoryTable({ tx, recentHistory = [] }) {
  return (
    <div className="shadcn-card" style={{ overflow: 'hidden' }}>
      <div style={{
        padding: '1rem 1.25rem',
        borderBottom: '1px solid #e4e4e7',
        backgroundColor: '#ffffff',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <h3 style={{ margin: 0, color: '#09090b', fontSize: '0.9375rem', fontWeight: 600 }}>
            Account Transaction History (Recent 20 Transactions)
          </h3>
          <span style={{ fontSize: '0.75rem', color: '#71717a' }}>
            Historical records for account <code style={{ color: '#09090b' }}>{tx.source_account}</code>
          </span>
        </div>
      </div>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <table className="shadcn-table">
          <thead>
            <tr>
              <th>Tx ID</th>
              <th>Timestamp</th>
              <th>Destination</th>
              <th>Type &amp; Channel</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {recentHistory.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: '#71717a' }}>
                  No historical transactions found for this account.
                </td>
              </tr>
            ) : (
              recentHistory.map((h, i) => {
                const isCurrent = h.transaction_id === tx.transaction_id;
                const amtFmt = new Intl.NumberFormat('en-US', {
                  style: 'currency',
                  currency: 'VND',
                  maximumFractionDigits: 0,
                }).format(h.amount || 0);

                return (
                  <tr
                    key={h.transaction_id || i}
                    style={{
                      backgroundColor: isCurrent ? '#fef2f2' : 'transparent',
                    }}
                  >
                    <td style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontWeight: isCurrent ? 700 : 500,
                      color: isCurrent ? '#b91c1c' : '#09090b',
                    }}>
                      {h.transaction_id} {isCurrent && <span style={{ fontSize: '0.6875rem', color: '#dc2626' }}>(CURRENT)</span>}
                    </td>
                    <td style={{ color: '#71717a' }}>
                      {h.timestamp}
                    </td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", color: '#27272a' }}>
                      {h.dest_account}
                    </td>
                    <td>
                      <span style={{
                        backgroundColor: '#f4f4f5',
                        border: '1px solid #e4e4e7',
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                      }}>
                        {h.trans_type} ({h.channel})
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: isCurrent ? '#b91c1c' : '#09090b' }}>
                      {amtFmt}
                    </td>
                    <td>
                      {h.is_fraud_label === 1 ? (
                        <span style={{ color: '#dc2626', fontWeight: 600, fontSize: '0.75rem' }}>Fraud (1)</span>
                      ) : (
                        <span style={{ color: '#16a34a', fontWeight: 500, fontSize: '0.75rem' }}>Normal (0)</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

