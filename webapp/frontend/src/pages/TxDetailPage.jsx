import React, { useState, useEffect } from 'react';
import { fetchTransactionDetail, submitInspection } from '../services/api';
import RiskFactorsBar from '../components/RiskFactorsBar';

export default function TxDetailPage({ transactionId, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reason, setReason] = useState('Abnormal Balance Discrepancy');
  const [inspector, setInspector] = useState('Auditor_01');

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
    try {
      await submitInspection(transactionId, {
        label,
        inspector_id: inspector,
        reason,
        processing_time_seconds: 8
      });
      alert(`Successfully recorded inspection verdict (${label === 1 ? 'FRAUD' : 'LEGITIMATE'}) to Lakehouse!`);
      loadDetail();
    } catch (err) {
      alert(`Error saving verdict: ${err.message}`);
    }
  };

  if (!transactionId) {
    return <div style={{ color: '#94a3b8', padding: '2rem' }}>No transaction selected.</div>;
  }

  if (loading || !data) {
    return <div style={{ color: '#94a3b8', padding: '2rem' }}>Loading transaction details for {transactionId}...</div>;
  }

  const tx = data.detail || {};

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: '1.5rem' }}>
      <div>
        <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ color: '#fff' }}>💳 Transaction Details: <span style={{ color: '#3b82f6' }}>{tx.transaction_id}</span></h3>
            <button onClick={onBack} style={{ background: '#1e293b', border: 'none', color: '#fff', padding: '0.4rem 0.8rem', borderRadius: '6px', cursor: 'pointer' }}>
              ➔ Back to Queue
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
            <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Amount</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.amount || 0)}
              </div>
            </div>
            <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Channel / Type</div>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: '#fff' }}>
                {tx.trans_type} ({tx.channel})
              </div>
            </div>
            <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Timestamp</div>
              <div style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>{tx.timestamp}</div>
            </div>
          </div>

          <RiskFactorsBar factors={data.risk_factors} />
        </div>
      </div>

      <div>
        <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(59,130,246,0.3)' }}>
          <h3 style={{ color: '#fff', marginBottom: '0.75rem' }}>⚖️ Fraud Auditor Verdict</h3>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1.25rem' }}>
            Verdicts are recorded to <code>silver.inspection_decisions</code> to trigger the Airflow retraining feedback loop.
          </p>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#94a3b8', marginBottom: '0.3rem' }}>Auditor ID</label>
            <input 
              type="text" 
              value={inspector} 
              onChange={e => setInspector(e.target.value)} 
              style={{ width: '100%', padding: '0.6rem', background: '#0a0e17', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '6px' }} 
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#94a3b8', marginBottom: '0.3rem' }}>Reason</label>
            <select 
              value={reason} 
              onChange={e => setReason(e.target.value)}
              style={{ width: '100%', padding: '0.6rem', background: '#0a0e17', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '6px' }}
            >
              <option value="Abnormal Balance Discrepancy">Abnormal Balance Discrepancy</option>
              <option value="Sudden Amount Spike vs 30-Day History">Sudden Amount Spike vs 30-Day History</option>
              <option value="Suspicious New Destination Account (Mule)">Suspicious New Destination Account (Mule)</option>
              <option value="Legitimate Transaction Confirmed by Cardholder">Legitimate Transaction Confirmed by Cardholder</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <button 
              onClick={() => handleDecision(1)}
              style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '0.75rem', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
            >
              🚨 FRAUD
            </button>
            <button 
              onClick={() => handleDecision(0)}
              style={{ background: '#10b981', color: '#fff', border: 'none', padding: '0.75rem', borderRadius: '6px', fontWeight: 700, cursor: 'pointer' }}
            >
              🛡️ LEGITIMATE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
