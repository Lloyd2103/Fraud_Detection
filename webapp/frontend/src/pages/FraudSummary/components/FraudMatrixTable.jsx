import React from 'react';
import { fmt, fmtAmount, fmtPct } from '../fraudFormat';

const CHANNEL_ICON = { ONLINE: '\u{1F310}', ATM: '\u{1F3E7}', POS: '\u{1F4B3}', APP: '\u{1F4F1}' };

export default function FraudMatrixTable({ rawRows = [], riskColor }) {
  return (
    <div className="shadcn-card" style={{ overflow: 'hidden' }}>
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e4e4e7', backgroundColor: '#fafafa' }}>
        <h2 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 600, color: '#09090b' }}>
          Channel &times; Transaction Type Matrix
        </h2>
        <p style={{ margin: '0.15rem 0 0', fontSize: '0.75rem', color: '#71717a' }}>
          Full breakdown from the CockroachDB fraud_summary table (flagged transactions only)
        </p>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="shadcn-table">
          <thead>
            <tr>
              <th>Channel</th>
              <th>Type</th>
              <th>Flagged Transactions</th>
              <th>Flagged Amount</th>
              <th>Fraud Cases</th>
              <th>Fraud / Flagged</th>
              <th>Avg Amount / Tx</th>
            </tr>
          </thead>
          <tbody>
            {rawRows.map((r, i) => {
              const rate = r.fraud_rate_percentage || 0;
              const rc = riskColor(rate);
              const totalTx = r.total_transactions ?? 0;
              const totalVol = r.total_amount ?? r.total_volume ?? 0;
              const fraudCases = r.total_fraud_cases ?? r.fraud_volume ?? 0;
              const avgTx = totalTx > 0 ? Math.round(totalVol / totalTx) : 0;
              return (
                <tr key={i}>
                  <td style={{ fontWeight: 600, color: '#09090b' }}>{CHANNEL_ICON[r.channel] || ''} {r.channel}</td>
                  <td><span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem', backgroundColor: '#f4f4f5', padding: '0.15rem 0.4rem', borderRadius: 4 }}>{r.trans_type}</span></td>
                  <td style={{ textAlign: 'right' }}>{fmt(totalTx)}</td>
                  <td style={{ textAlign: 'right', color: '#09090b', fontWeight: 500 }}>{fmtAmount(totalVol)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600, color: fraudCases > 0 ? '#dc2626' : '#71717a' }}>{fmt(fraudCases)}</td>
                  <td>
                    <span style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      padding: '0.1rem 0.4rem',
                      borderRadius: 4,
                      color: rc.color,
                      backgroundColor: rc.bg,
                      border: `1px solid ${rc.border}`,
                    }}>
                      {fmtPct(rate)}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right', color: '#71717a', fontSize: '0.75rem' }}>{avgTx > 0 ? fmt(avgTx) : '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

