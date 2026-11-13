import React from 'react';
import { Scale, CheckCircle2, Save } from 'lucide-react';
import { formatVietnamTime } from '../../../utils/formatters';

export default function TxDecisionCard({
  tx,
  transactionId,
  isAlreadyInspected,
  recordedVerdict,
  inspector,
  presetReason,
  setPresetReason,
  customReason,
  setCustomReason,
  handleDecision,
  handleSaveDetails,
  handleResetPending,
  submitting,
}) {
  return (
    <div className="shadcn-card" style={{ padding: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
        <h3 style={{ margin: 0, color: '#09090b', fontSize: '0.9375rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Scale size={16} strokeWidth={1.75} />
          <span>Auditor Decision (Feedback Loop)</span>
        </h3>
        {isAlreadyInspected && (
          <span style={{
            fontSize: '0.6875rem',
            fontWeight: 700,
            padding: '0.15rem 0.5rem',
            borderRadius: '4px',
            backgroundColor: recordedVerdict === 1 ? '#fee2e2' : '#dcfce7',
            color: recordedVerdict === 1 ? '#991b1b' : '#166534',
            border: `1px solid ${recordedVerdict === 1 ? '#fecaca' : '#bbf7d0'}`,
          }}>
            {recordedVerdict === 1 ? 'FRAUD CONFIRMED' : 'CLEARED LEGITIMATE'}
          </span>
        )}
      </div>
      <p style={{ fontSize: '0.75rem', color: '#71717a', margin: '0 0 1rem 0' }}>
        Recorded to CockroachDB inspection_decisions, synced to Delta Lake via Changefeed &amp; Kafka.
      </p>

      {isAlreadyInspected && (
        <div style={{
          backgroundColor: recordedVerdict === 1 ? '#fef2f2' : '#f0fdf4',
          border: `1px solid ${recordedVerdict === 1 ? '#fee2e2' : '#dcfce7'}`,
          padding: '0.85rem',
          borderRadius: '6px',
          marginBottom: '1rem',
          fontSize: '0.8125rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.4rem' }}>
            <CheckCircle2 size={15} color={recordedVerdict === 1 ? '#dc2626' : '#16a34a'} strokeWidth={2.5} />
            <strong style={{ color: recordedVerdict === 1 ? '#991b1b' : '#166534' }}>
              Already Inspected &amp; Recorded
            </strong>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.75rem', color: recordedVerdict === 1 ? '#7f1d1d' : '#14532d' }}>
            <div>• <strong>Recorded Verdict:</strong> {recordedVerdict === 1 ? 'FRAUD (1)' : 'LEGITIMATE (0)'}</div>
            <div>• <strong>Auditor Staff:</strong> {tx.inspector_name ? `${tx.inspector_name} (${tx.inspector_id})` : (tx.inspector_id || 'N/A')}</div>
            {tx.decision_timestamp && <div>• <strong>Recorded At:</strong> {formatVietnamTime(tx.decision_timestamp)}</div>}
            <div>• <strong>Investigation Justification:</strong> {tx.reason || customReason || presetReason || 'N/A'}</div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: '0.75rem' }}>
        <label style={{ display: 'block', fontSize: '0.75rem', color: '#71717a', marginBottom: '0.25rem', fontWeight: 500 }}>
          Auditor ID (Current logged-in account)
        </label>
        <input
          type="text"
          value={inspector}
          readOnly
          disabled
          className="shadcn-input"
          style={{ backgroundColor: '#f4f4f5', color: '#71717a', cursor: 'not-allowed' }}
        />
      </div>

      <div style={{ marginBottom: '0.75rem' }}>
        <label style={{ display: 'block', fontSize: '0.75rem', color: '#71717a', marginBottom: '0.25rem', fontWeight: 500 }}>
          Preset Investigation Justification
        </label>
        <select
          value={presetReason}
          onChange={(e) => {
            const val = e.target.value;
            setPresetReason(val);
            if (val !== 'OTHER') {
              setCustomReason(val);
            } else {
              setCustomReason('');
            }
          }}
          className="shadcn-input"
          style={{ cursor: 'pointer', appearance: 'auto' }}
        >
          <option value="Abnormal Balance Discrepancy">Abnormal Balance Discrepancy</option>
          <option value="Sudden Amount Spike vs 30-Day History">Sudden Amount Spike vs 30-Day History</option>
          <option value="Suspicious New Destination Account (Mule)">Suspicious New Destination Account (Mule)</option>
          <option value="Account Draining / Rapid Cash-Out Sequence">Account Draining / Rapid Cash-Out Sequence</option>
          <option value="Legitimate Transaction Confirmed by Cardholder">Legitimate Transaction Confirmed by Cardholder</option>
          <option value="OTHER">Other / Custom Justification (Enter below)...</option>
        </select>
      </div>

      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
          <label style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>
            Custom Justification &amp; Notes
          </label>
          <button
            type="button"
            onClick={handleSaveDetails}
            disabled={submitting}
            className="btn-shadcn btn-outline"
            style={{ height: '1.65rem', padding: '0 0.5rem', fontSize: '0.72rem', gap: '0.25rem' }}
            title="Save edited notes and auditor ID without altering verdict"
          >
            <Save size={12} strokeWidth={2} />
            <span>Save Notes &amp; ID</span>
          </button>
        </div>
        <textarea
          rows={2}
          value={customReason}
          onChange={(e) => setCustomReason(e.target.value)}
          placeholder="Type specific audit reason, cardholder statement, or investigative notes here..."
          className="shadcn-input"
          style={{ height: 'auto', padding: '0.5rem', resize: 'vertical' }}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        <button
          onClick={() => handleDecision(1)}
          disabled={submitting}
          className="btn-shadcn"
          style={{
            backgroundColor: recordedVerdict === 1 && isAlreadyInspected ? '#dc2626' : '#09090b',
            color: '#ffffff',
            height: '2.5rem',
          }}
        >
          <span>{isAlreadyInspected ? 'Update: Fraud (1)' : 'Confirm Fraud (1)'}</span>
        </button>
        <button
          onClick={() => handleDecision(0)}
          disabled={submitting}
          className="btn-shadcn btn-secondary"
          style={{
            height: '2.5rem',
            borderColor: recordedVerdict === 0 && isAlreadyInspected ? '#16a34a' : undefined,
            color: recordedVerdict === 0 && isAlreadyInspected ? '#16a34a' : undefined,
            fontWeight: recordedVerdict === 0 && isAlreadyInspected ? 700 : 500,
          }}
        >
          <span>{isAlreadyInspected ? 'Update: Legitimate (0)' : 'Legitimate (0)'}</span>
        </button>
      </div>

      {isAlreadyInspected && (
        <div style={{ marginTop: '0.75rem', textAlign: 'center' }}>
          <button
            type="button"
            onClick={handleResetPending}
            disabled={submitting}
            style={{
              background: 'none',
              border: 'none',
              color: '#71717a',
              fontSize: '0.75rem',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Reset Status Back to Pending
          </button>
        </div>
      )}
    </div>
  );
}

