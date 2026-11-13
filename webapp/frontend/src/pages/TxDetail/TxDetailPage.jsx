import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ArrowLeft, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useTransactions } from '../../hooks/useTransactions';
import { useVerdicts } from '../../hooks/useVerdicts';
import RiskFactorsBar from '../../components/RiskFactorsBar';
import TxTimelineChart from './components/TxTimelineChart';
import TxDecisionCard from './components/TxDecisionCard';
import TxHistoryTable from './components/TxHistoryTable';

export default function TxDetailPage({ transactionId, onBack, sourceTab = 'alerts' }) {
  const { user: currentUser } = useAuth();
  const { getDetail, updateDetail } = useTransactions();
  const { submitDecision } = useVerdicts();

  const defaultInspectorId = currentUser?.id;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [presetReason, setPresetReason] = useState('Abnormal Balance Discrepancy');
  const [customReason, setCustomReason] = useState('');
  const [inspector, setInspector] = useState(defaultInspectorId);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);
  const openedAtRef = useRef(Date.now());

  useEffect(() => {
    openedAtRef.current = Date.now();
  }, [transactionId]);

  useEffect(() => {
    if (currentUser) {
      setInspector(currentUser.full_name || currentUser.username || currentUser.id);
    }
  }, [currentUser]);

  const loadDetail = useCallback(async () => {
    if (!transactionId) return;
    setLoading(true);
    try {
      const res = await getDetail(transactionId);
      setData(res);
      if (res?.detail?.reason) {
        setCustomReason(res.detail.reason);
      }
    } catch (err) {
      console.error('Error fetching detail:', err);
    } finally {
      setLoading(false);
    }
  }, [transactionId, getDetail]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleDecision = async (label) => {
    setSubmitting(true);
    setMessage(null);
    const finalReason = customReason.trim() ? customReason.trim() : presetReason;

    try {
      const elapsedSeconds = Math.max(1, Math.round((Date.now() - openedAtRef.current) / 1000));
      await submitDecision(transactionId, {
        label,
        nhan: label,
        reason: finalReason,
        ly_do: finalReason,
        processing_time: elapsedSeconds,
        thoi_gian_xu_ly_giay: elapsedSeconds,
      });
      const verdict = label === 1 ? 'FRAUD (1)' : 'LEGITIMATE (0)';
      setMessage({ type: 'success', text: `Verdict recorded: ${verdict} for ${transactionId} written to Silver: Inspection Decisions!` });
      loadDetail();
    } catch (err) {
      setMessage({ type: 'error', text: `Error recording verdict: ${err.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSaveDetails = async () => {
    setSubmitting(true);
    setMessage(null);
    const finalReason = customReason.trim() ? customReason.trim() : presetReason;

    try {
      await updateDetail(transactionId, { reason: finalReason });
      setMessage({ type: 'success', text: 'Transaction details and notes updated successfully in PostgreSQL serving store!' });
      loadDetail();
    } catch (err) {
      setMessage({ type: 'error', text: `Error updating transaction: ${err.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetPending = async () => {
    setSubmitting(true);
    try {
      await updateDetail(transactionId, {
        inspection_status: 'PENDING',
        decision_label: null,
      });
      setMessage({ type: 'success', text: `Transaction ${transactionId} reset back to PENDING queue in PostgreSQL!` });
      loadDetail();
    } catch (err) {
      setMessage({ type: 'error', text: `Error resetting status: ${err.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  if (!transactionId) {
    const returnTitle = sourceTab === 'inspected' ? 'Inspected Verdicts' : 'Alert Queue';
    return (
      <div className="shadcn-card" style={{ padding: '3rem', textAlign: 'center', color: '#71717a' }}>
        <p style={{ margin: '0 0 1rem 0' }}>
          Please select a transaction from <strong>{returnTitle}</strong> to inspect details.
        </p>
        <button onClick={onBack} className="btn-shadcn btn-primary" style={{ height: '2.25rem', padding: '0 1rem' }}>
          Back to {returnTitle}
        </button>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="shadcn-card" style={{ padding: '3rem', textAlign: 'center', color: '#71717a', fontSize: '0.875rem' }}>
        Loading transaction telemetry for <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: '#09090b' }}>{transactionId}</span>...
      </div>
    );
  }

  const tx = data.detail || {};
  const rawInspectionStatus = (tx.inspection_status || '').toUpperCase();
  const isAlreadyInspected = rawInspectionStatus === 'PROCESSED' ||
    rawInspectionStatus === 'CONFIRMED_FRAUD' ||
    rawInspectionStatus === 'CLEARED_LEGITIMATE' ||
    rawInspectionStatus === 'DA_XU_LY' ||
    rawInspectionStatus === 'INSPECTED' ||
    (tx.decision_label !== undefined && tx.decision_label !== null);
  const recordedVerdict = (tx.decision_label === 1 || rawInspectionStatus === 'CONFIRMED_FRAUD') ? 1 : 0;
  const recentHistory = data.recent_history || [];
  const timelinePoints = data.timeline_points || [];
  const formattedAmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.amount || 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header Bar with Back Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ color: '#09090b', fontSize: '1.25rem', fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
            Transaction Inspection &amp; Triage
          </h2>
          <p style={{ color: '#71717a', fontSize: '0.8125rem', margin: '0.15rem 0 0 0' }}>
            Inspect high-risk event <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: '#09090b' }}>{tx.transaction_id}</span> and record verdict to Lakehouse
          </p>
        </div>
        <button
          onClick={onBack}
          className="btn-shadcn btn-outline"
          style={{ height: '2.25rem', padding: '0 0.85rem' }}
        >
          <ArrowLeft size={14} strokeWidth={1.5} />
          <span>{sourceTab === 'inspected' ? 'Back to Inspected Verdicts' : 'Back to Alert Queue'}</span>
        </button>
      </div>

      {message && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          backgroundColor: message.type === 'success' ? '#f0fdf4' : '#fef2f2',
          border: `1px solid ${message.type === 'success' ? '#dcfce7' : '#fee2e2'}`,
          color: message.type === 'success' ? '#166534' : '#991b1b',
          fontSize: '0.8125rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          {message.type === 'success' ? <CheckCircle2 size={16} strokeWidth={2} /> : <AlertTriangle size={16} strokeWidth={2} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Grid: 2 Columns */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem', alignItems: 'start' }}>
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Main Info Card */}
          <div className="shadcn-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0, color: '#09090b', fontSize: '1rem', fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                  {tx.transaction_id}
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#71717a' }}>Event time (dataset): {tx.timestamp}</span>
              </div>
              <span style={{
                padding: '0.2rem 0.6rem',
                borderRadius: '9999px',
                fontWeight: 700,
                fontSize: '0.8125rem',
                backgroundColor: (data.risk_score || 0) >= 0.8 ? '#fef2f2' : '#fffbeb',
                color: (data.risk_score || 0) >= 0.8 ? '#991b1b' : '#92400e',
                border: `1px solid ${(data.risk_score || 0) >= 0.8 ? '#fee2e2' : '#fef3c7'}`,
              }}>
                Risk Score: {((data.risk_score || 0) * 100).toFixed(1)}%
              </span>
            </div>

            {/* 3 Metric Badges */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
              <div style={{ backgroundColor: '#fafafa', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
                <div style={{ fontSize: '0.75rem', color: '#71717a' }}>Amount</div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#09090b', marginTop: '0.15rem' }}>
                  {formattedAmt}
                </div>
              </div>
              <div style={{ backgroundColor: '#fafafa', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
                <div style={{ fontSize: '0.75rem', color: '#71717a' }}>Channel / Type</div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#09090b', marginTop: '0.15rem' }}>
                  {tx.trans_type} <span style={{ color: '#71717a', fontSize: '0.75rem' }}>({tx.channel})</span>
                </div>
              </div>
              <div style={{ backgroundColor: '#fafafa', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
                <div style={{ fontSize: '0.75rem', color: '#71717a' }}>Accounts</div>
                <div style={{ fontSize: '0.75rem', fontFamily: "'JetBrains Mono', monospace", color: '#09090b', marginTop: '0.15rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {tx.source_account} ➔ {tx.dest_account}
                </div>
              </div>
            </div>

            {/* Top 3 Risk Factors */}
            <RiskFactorsBar factors={data.risk_factors || []} />
          </div>

          {/* Timeline Chart Card */}
          <TxTimelineChart tx={tx} timelinePoints={timelinePoints} />
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <TxDecisionCard
            tx={tx}
            transactionId={transactionId}
            isAlreadyInspected={isAlreadyInspected}
            recordedVerdict={recordedVerdict}
            inspector={inspector}
            presetReason={presetReason}
            setPresetReason={setPresetReason}
            customReason={customReason}
            setCustomReason={setCustomReason}
            handleDecision={handleDecision}
            handleSaveDetails={handleSaveDetails}
            handleResetPending={handleResetPending}
            submitting={submitting}
          />

          {/* Account Balance Summary Card */}
          <div className="shadcn-card" style={{ padding: '1.25rem' }}>
            <h4 style={{ margin: '0 0 0.75rem 0', color: '#09090b', fontSize: '0.875rem', fontWeight: 600 }}>
              Source Account Balances
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8125rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f4f4f5', paddingBottom: '0.35rem' }}>
                <span style={{ color: '#71717a' }}>Previous Balance:</span>
                <strong style={{ color: '#09090b' }}>
                  {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.old_balance_source || 0)}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f4f4f5', paddingBottom: '0.35rem' }}>
                <span style={{ color: '#71717a' }}>Updated Balance:</span>
                <strong style={{ color: tx.new_balance_source === 0 ? '#dc2626' : '#09090b' }}>
                  {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.new_balance_source || 0)}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#71717a' }}>Model Version:</span>
                <span style={{ color: '#09090b', fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem' }}>{data.model_version || 'v1.4-GBT'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent 20 Transactions Table Card */}
      <TxHistoryTable tx={tx} recentHistory={recentHistory} />
    </div>
  );
}

