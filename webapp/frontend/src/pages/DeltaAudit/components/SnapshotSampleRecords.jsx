import React from 'react';
import { FileSpreadsheet } from 'lucide-react';
import { formatVietnamTime } from '../../../utils/formatters';

export default function SnapshotSampleRecords({
  sampleData = [],
  loading,
  loadedVersion,
  selectedVersion,
}) {
  return (
    <div className="shadcn-card" style={{ overflow: 'hidden' }}>
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e4e4e7', backgroundColor: '#ffffff' }}>
        <h4 style={{ margin: '0 0 0.2rem 0', color: '#09090b', fontSize: '0.9375rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <FileSpreadsheet size={16} strokeWidth={1.5} />
          <span>Point-in-Time Sample Records (Loaded via VERSION AS OF {loadedVersion ?? selectedVersion})</span>
        </h4>
        <p style={{ fontSize: '0.75rem', color: '#71717a', margin: 0 }}>
          Showing up to 50 sample records read directly from Delta Lake snapshot version #{loadedVersion ?? selectedVersion}.
        </p>
      </div>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <table className="shadcn-table">
          <thead>
            <tr>
              <th>Tx ID</th>
              <th>Timestamp</th>
              <th>Source ➔ Destination</th>
              <th>Channel / Type</th>
              <th>Amount</th>
              <th>Risk Score &amp; Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2.5rem', color: '#71717a', fontSize: '0.875rem' }}>
                  Loading point-in-time sample records from snapshot version #{selectedVersion}...
                </td>
              </tr>
            ) : sampleData.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: '#71717a' }}>
                  No sample records in Delta snapshot version #{loadedVersion ?? selectedVersion}.
                </td>
              </tr>
            ) : (
              sampleData.map((s, idx) => {
                const amt = s.so_tien !== undefined ? s.so_tien : (s.amount || 0);
                const amtFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(amt);
                const txId = s.ma_giao_dich || s.transaction_id || `TX_${idx}`;
                const tTime = s.thoi_diem || s.timestamp || '';
                const src = s.tai_khoan_nguon || s.source_account || '—';
                const dst = s.tai_khoan_dich || s.dest_account || '—';
                const tType = s.loai || s.trans_type || 'TRANSFER';
                const channel = s.kenh || s.channel || 'ONLINE';
                const isFraud = s.nhan !== undefined ? s.nhan : (s.is_fraud_label !== undefined ? s.is_fraud_label : 0);

                return (
                  <tr key={idx}>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", color: '#09090b', fontWeight: 600, fontSize: '0.8125rem' }}>
                      {txId}
                    </td>
                    <td style={{ color: '#71717a', fontSize: '0.8125rem' }}>
                      {tTime ? formatVietnamTime(tTime) : '—'}
                    </td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", color: '#27272a', fontSize: '0.8125rem' }}>
                      {src} ➔ {dst}
                    </td>
                    <td>
                      <span style={{ backgroundColor: '#f4f4f5', border: '1px solid #e4e4e7', padding: '0.15rem 0.45rem', borderRadius: '4px', fontSize: '0.75rem', color: '#27272a' }}>
                        {tType} ({channel})
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: '#09090b', fontSize: '0.8125rem' }}>
                      {amtFmt}
                    </td>
                    <td>
                      {s.risk_score !== undefined ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <span style={{
                            color: s.risk_score >= 0.80 ? '#b91c1c' : '#15803d',
                            fontWeight: 700,
                            fontSize: '0.8125rem',
                            backgroundColor: s.risk_score >= 0.80 ? '#fef2f2' : '#f0fdf4',
                            padding: '0.15rem 0.45rem',
                            borderRadius: '4px',
                            border: `1px solid ${s.risk_score >= 0.80 ? '#fee2e2' : '#dcfce7'}`,
                          }}>
                            Score: {s.risk_score.toFixed(2)}
                          </span>
                          <span style={{ fontSize: '0.6875rem', color: '#71717a' }}>({s.inspection_status || 'PENDING'})</span>
                        </div>
                      ) : isFraud === 1 ? (
                        <span style={{ color: '#b91c1c', fontWeight: 600, fontSize: '0.8125rem', backgroundColor: '#fef2f2', padding: '0.15rem 0.45rem', borderRadius: '4px', border: '1px solid #fee2e2' }}>
                          Fraud (1)
                        </span>
                      ) : (
                        <span style={{ color: '#15803d', fontWeight: 500, fontSize: '0.8125rem', backgroundColor: '#f0fdf4', padding: '0.15rem 0.45rem', borderRadius: '4px', border: '1px solid #dcfce7' }}>
                          Legitimate (0)
                        </span>
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

