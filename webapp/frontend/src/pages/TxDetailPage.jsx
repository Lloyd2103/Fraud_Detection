import React, { useState, useEffect } from 'react';
import 'chart.js/auto';
import { Line } from 'react-chartjs-2';
import { fetchTransactionDetail, submitInspection } from '../services/api';
import RiskFactorsBar from '../components/RiskFactorsBar';

export default function TxDetailPage({ transactionId, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reason, setReason] = useState('Abnormal Balance Discrepancy');
  const [inspector, setInspector] = useState('Auditor_01');
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);

  const loadDetail = async () => {
    if (!transactionId) return;
    setLoading(true);
    try {
      const res = await fetchTransactionDetail(transactionId);
      setData(res.data);
    } catch (err) {
      console.error('Error fetching detail:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [transactionId]);

  const handleDecision = async (label) => {
    setSubmitting(true);
    setMessage(null);
    try {
      const res = await submitInspection(transactionId, {
        label,
        nhan: label,
        inspector_id: inspector,
        nguoi_tham_dinh: inspector,
        reason,
        ly_do: reason,
        processing_time: 8,
        thoi_gian_xu_ly_giay: 8
      });
      const verdict = label === 1 ? 'GIAN LẬN / FRAUD (1)' : 'HỢP LỆ / LEGITIMATE (0)';
      setMessage({ type: 'success', text: `Kết luận thẩm định: ${verdict} cho ${transactionId} đã được ghi vào silver.ket_luan_tham_dinh!` });
      loadDetail();
    } catch (err) {
      setMessage({ type: 'error', text: `Lỗi ghi nhận kết luận: ${err.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  if (!transactionId) {
    return (
      <div style={{ background: '#111827', borderRadius: '12px', padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
        Please select a transaction from the <strong>Alert Queue</strong> to inspect details.
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div style={{ background: '#111827', borderRadius: '12px', padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
        Loading transaction details for <span style={{ color: '#3b82f6', fontFamily: 'monospace' }}>{transactionId}</span>...
      </div>
    );
  }

  const tx = data.detail || {};
  const recentHistory = data.recent_history || [];
  const timelinePoints = data.timeline_points || [];
  const formattedAmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.amount || 0);

  // Prepare Timeline Chart Data
  const timelineLabels = timelinePoints.map((p, idx) => {
    if (p.time && p.time.includes(' ')) {
      return p.time.split(' ')[1] || p.time;
    }
    return `T-${timelinePoints.length - idx}`;
  });

  const timelineAmounts = timelinePoints.map(p => p.amount);
  const pointBgColors = timelinePoints.map(p => p.is_current ? '#ef4444' : '#3b82f6');
  const pointBorderColors = timelinePoints.map(p => p.is_current ? '#fca5a5' : '#60a5fa');
  const pointRadii = timelinePoints.map(p => p.is_current ? 9 : 4);
  const pointHoverRadii = timelinePoints.map(p => p.is_current ? 12 : 7);

  const chartData = {
    labels: timelineLabels,
    datasets: [
      {
        label: 'Transaction Amount (VND)',
        data: timelineAmounts,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointBackgroundColor: pointBgColors,
        pointBorderColor: pointBorderColors,
        pointBorderWidth: 2,
        pointRadius: pointRadii,
        pointHoverRadius: pointHoverRadii,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#1f2937',
        titleColor: '#f9fafb',
        bodyColor: '#e5e7eb',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        callbacks: {
          label: (ctx) => {
            const val = ctx.parsed.y || 0;
            const isCurrent = timelinePoints[ctx.dataIndex]?.is_current;
            return `${isCurrent ? '🚨 CURRENT TX: ' : ''}${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)}`;
          }
        }
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8', font: { size: 11 } }
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: {
          color: '#94a3b8',
          font: { size: 11 },
          callback: (value) => `${(value / 1000).toFixed(0)}k`
        }
      }
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Back button & Title Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ color: '#fff', fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>
            💳 Transaction Detail & Auditor Triage
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.8rem', margin: '0.2rem 0 0 0' }}>
            Inspect high-risk transaction <span style={{ color: '#3b82f6', fontFamily: 'monospace' }}>{tx.transaction_id}</span> and record verdict to Delta Lake
          </p>
        </div>
        <button 
          onClick={onBack} 
          style={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 500 }}
        >
          ➔ Back to Queue
        </button>
      </div>

      {message && (
        <div style={{ 
          padding: '0.85rem 1.25rem', 
          borderRadius: '8px', 
          background: message.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          border: `1px solid ${message.type === 'success' ? '#10b981' : '#ef4444'}`,
          color: message.type === 'success' ? '#6ee7b7' : '#fca5a5',
          fontSize: '0.85rem'
        }}>
          {message.text}
        </div>
      )}

      {/* Grid: 2 Columns (Left: Details, Risk Factors, Timeline | Right: Verdict Form & Account Info) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.65fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Main Info Card */}
          <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '1.5rem' }}>⚡</span>
                <div>
                  <h3 style={{ margin: 0, color: '#fff', fontSize: '1.1rem' }}>{tx.transaction_id}</h3>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Timestamp: {tx.timestamp}</span>
                </div>
              </div>
              <div style={{ 
                padding: '0.35rem 0.8rem', 
                borderRadius: '9999px', 
                fontWeight: 700, 
                fontSize: '0.85rem',
                background: (data.risk_score || 0) >= 0.8 ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)',
                color: (data.risk_score || 0) >= 0.8 ? '#fca5a5' : '#fcd34d',
                border: `1px solid ${(data.risk_score || 0) >= 0.8 ? '#ef4444' : '#f59e0b'}`
              }}>
                Risk Score: {((data.risk_score || 0) * 100).toFixed(1)}%
              </div>
            </div>

            {/* 3 Metric Badges */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
              <div style={{ background: '#1e293b', padding: '0.85rem', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Transaction Amount</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                  {formattedAmt}
                </div>
              </div>
              <div style={{ background: '#1e293b', padding: '0.85rem', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Channel / Type</div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: '#fff', marginTop: '0.2rem' }}>
                  {tx.trans_type} <span style={{ color: '#3b82f6', fontSize: '0.8rem' }}>({tx.channel})</span>
                </div>
              </div>
              <div style={{ background: '#1e293b', padding: '0.85rem', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Source ➔ Destination</div>
                <div style={{ fontSize: '0.85rem', fontFamily: 'monospace', color: '#cbd5e1', marginTop: '0.2rem' }}>
                  {tx.source_account} ➔ {tx.dest_account}
                </div>
              </div>
            </div>

            {/* Top 3 Risk Factors Component */}
            <RiskFactorsBar factors={data.risk_factors || []} />
          </div>

          {/* Timeline Chart Card (DeTai_2.pdf 2.8 Requirement) */}
          <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h3 style={{ margin: 0, color: '#fff', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>📈</span> Timeline: Transaction Amount Over Time
              </h3>
              <span style={{ fontSize: '0.75rem', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }}></span>
                Red dot marks current transaction
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 1rem 0' }}>
              Visual inspection of spending trajectory for account <code style={{ color: '#cbd5e1' }}>{tx.source_account}</code> to detect sudden amount surges and anomalous spikes.
            </p>
            <div style={{ height: '240px', width: '100%' }}>
              <Line data={chartData} options={chartOptions} />
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Decision Card */}
          <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(59, 130, 246, 0.4)', boxShadow: '0 4px 20px rgba(0,0,0,0.4)' }}>
            <h3 style={{ margin: '0 0 0.5rem 0', color: '#fff', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>⚖️</span> Auditor Verdict (Feedback Loop)
            </h3>
            <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 1.25rem 0' }}>
              Submitted decisions are recorded to Delta Lake table <code style={{ color: '#93c5fd' }}>silver.inspection_decisions</code> and merged into <code style={{ color: '#93c5fd' }}>gold.risk_scores</code>, feeding Airflow DAG 3 for model retraining.
            </p>

            {tx.inspection_status === 'PROCESSED' && (
              <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', padding: '0.75rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.8rem', color: '#a7f3d0' }}>
                <strong>✓ Already Inspected:</strong> Verdict recorded as {tx.decision_label === 1 ? 'FRAUD' : 'LEGITIMATE'} by {tx.inspector_id || 'auditor'}.
              </div>
            )}

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                Auditor Staff ID
              </label>
              <input 
                type="text" 
                value={inspector} 
                onChange={e => setInspector(e.target.value)} 
                style={{ width: '100%', padding: '0.65rem 0.8rem', background: '#0a0e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px', fontSize: '0.85rem' }} 
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                Investigation Reason / Justification
              </label>
              <select 
                value={reason} 
                onChange={e => setReason(e.target.value)}
                style={{ width: '100%', padding: '0.65rem 0.8rem', background: '#0a0e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px', fontSize: '0.85rem' }}
              >
                <option value="Abnormal Balance Discrepancy">Abnormal Balance Discrepancy</option>
                <option value="Sudden Amount Spike vs 30-Day History">Sudden Amount Spike vs 30-Day History</option>
                <option value="Suspicious New Destination Account (Mule)">Suspicious New Destination Account (Mule)</option>
                <option value="Account Draining / Rapid Cash-Out Sequence">Account Draining / Rapid Cash-Out Sequence</option>
                <option value="Legitimate Transaction Confirmed by Cardholder">Legitimate Transaction Confirmed by Cardholder</option>
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <button 
                onClick={() => handleDecision(1)}
                disabled={submitting}
                style={{ 
                  background: 'linear-gradient(135deg, #ef4444, #dc2626)', 
                  color: '#fff', 
                  border: 'none', 
                  padding: '0.85rem', 
                  borderRadius: '8px', 
                  fontWeight: 700, 
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
                }}
              >
                🚨 CONFIRM FRAUD
              </button>
              <button 
                onClick={() => handleDecision(0)}
                disabled={submitting}
                style={{ 
                  background: 'linear-gradient(135deg, #10b981, #059669)', 
                  color: '#fff', 
                  border: 'none', 
                  padding: '0.85rem', 
                  borderRadius: '8px', 
                  fontWeight: 700, 
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
                }}
              >
                🛡️ LEGITIMATE
              </button>
            </div>
          </div>

          {/* Account Balance Summary Card */}
          <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)' }}>
            <h4 style={{ margin: '0 0 1rem 0', color: '#fff', fontSize: '0.95rem' }}>
              🏦 Source Account Balances
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.4rem' }}>
                <span style={{ color: '#94a3b8' }}>Old Balance:</span>
                <strong style={{ color: '#fff' }}>
                  {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.old_balance_source || 0)}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.4rem' }}>
                <span style={{ color: '#94a3b8' }}>New Balance:</span>
                <strong style={{ color: tx.new_balance_source === 0 ? '#ef4444' : '#fff' }}>
                  {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.new_balance_source || 0)}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Model Version:</span>
                <span style={{ color: '#3b82f6', fontFamily: 'monospace' }}>{data.model_version || 'v1.4-GBT'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent 20 Transactions Table Card (DeTai_2.pdf 2.8 Requirement) */}
      <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, color: '#fff', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>📜</span> Account Transaction History (Last 20 Transactions)
          </h3>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            Showing {recentHistory.length} historical records for <code style={{ color: '#fff' }}>{tx.source_account}</code>
          </span>
        </div>

        <div style={{ width: '100%', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ background: 'rgba(30, 41, 59, 0.5)', color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.72rem' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Tx ID</th>
                <th style={{ padding: '0.75rem 1rem' }}>Timestamp</th>
                <th style={{ padding: '0.75rem 1rem' }}>Destination</th>
                <th style={{ padding: '0.75rem 1rem' }}>Type & Channel</th>
                <th style={{ padding: '0.75rem 1rem' }}>Amount</th>
                <th style={{ padding: '0.75rem 1rem' }}>Label / Status</th>
              </tr>
            </thead>
            <tbody>
              {recentHistory.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                    No historical transactions found for this account.
                  </td>
                </tr>
              ) : (
                recentHistory.map((h, i) => {
                  const isCurrent = h.transaction_id === tx.transaction_id;
                  const amtFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(h.amount || 0);

                  return (
                    <tr 
                      key={h.transaction_id || i}
                      style={{ 
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        background: isCurrent ? 'rgba(239, 68, 68, 0.12)' : 'transparent',
                        borderLeft: isCurrent ? '3px solid #ef4444' : '3px solid transparent'
                      }}
                    >
                      <td style={{ padding: '0.65rem 1rem', fontFamily: 'monospace', fontWeight: isCurrent ? 700 : 400, color: isCurrent ? '#fca5a5' : '#fff' }}>
                        {h.transaction_id} {isCurrent && <span style={{ fontSize: '0.7rem', color: '#ef4444', fontWeight: 700 }}>(CURRENT)</span>}
                      </td>
                      <td style={{ padding: '0.65rem 1rem', color: '#94a3b8' }}>
                        {h.timestamp}
                      </td>
                      <td style={{ padding: '0.65rem 1rem', fontFamily: 'monospace', color: '#cbd5e1' }}>
                        {h.dest_account}
                      </td>
                      <td style={{ padding: '0.65rem 1rem' }}>
                        <span style={{ background: '#1e293b', padding: '0.2rem 0.45rem', borderRadius: '4px', fontSize: '0.75rem', color: '#cbd5e1' }}>
                          {h.trans_type} ({h.channel})
                        </span>
                      </td>
                      <td style={{ padding: '0.65rem 1rem', fontWeight: 600, color: isCurrent ? '#fca5a5' : '#fff' }}>
                        {amtFmt}
                      </td>
                      <td style={{ padding: '0.65rem 1rem' }}>
                        {h.is_fraud_label === 1 ? (
                          <span style={{ color: '#ef4444', fontWeight: 700 }}>Fraud (1)</span>
                        ) : (
                          <span style={{ color: '#10b981' }}>Normal (0)</span>
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
    </div>
  );
}
