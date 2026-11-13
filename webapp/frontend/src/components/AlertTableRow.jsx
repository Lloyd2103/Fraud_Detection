import React from 'react';
import { formatVietnamTime } from '../utils/formatters';
import { CheckCircle2, Clock, ChevronRight } from 'lucide-react';

export default function AlertTableRow({
  tx,
  idx,
  isInspectedView,
  onSelectTx,
}) {
  const txId = tx.ma_giao_dich || tx.transaction_id || `TX_${idx}`;
  const timeStr = tx.thoi_diem || tx.timestamp || '';
  const srcAcc = tx.tai_khoan_nguon || tx.source_account || 'N/A';
  const dstAcc = tx.tai_khoan_dich || tx.dest_account || 'N/A';
  const channel = tx.kenh || tx.channel || 'ONLINE';
  const transType = tx.loai || tx.trans_type || '';
  const amt = tx.so_tien !== undefined ? tx.so_tien : (tx.amount !== undefined ? tx.amount : 0);
  const score = parseFloat(tx.diem_rui_ro !== undefined ? tx.diem_rui_ro : (tx.risk_score || 0));
  const scorePct = (score * 100).toFixed(1);

  const rawStatus = (tx.trang_thai_tham_dinh || tx.inspection_status || tx.audit_status || 'PENDING').toUpperCase();
  const isProcessed = rawStatus === 'PROCESSED' ||
    rawStatus === 'DA_XU_LY' ||
    rawStatus === 'INSPECTED' ||
    rawStatus === 'CONFIRMED_FRAUD' ||
    rawStatus === 'CLEARED_LEGITIMATE' ||
    (tx.decision_label !== undefined && tx.decision_label !== null);

  const isFraud = tx.decision_label === 1 || rawStatus === 'CONFIRMED_FRAUD';
  const auditorStaff = tx.inspector_name || tx.inspector_username || tx.inspector_id || tx.auditor_id || tx.nguoi_tham_dinh || 'Auditor_01';
  const auditorTooltip = tx.inspector_name
    ? `ID: ${auditorStaff} • ${tx.inspector_name} (${tx.inspector_role || 'staff'})${tx.inspector_email ? ` <${tx.inspector_email}>` : ''}`
    : (auditorStaff === 'Auditor_01' ? 'Legacy System Auditor (Demo/Seed Data)' : `ID: ${auditorStaff}`);
  const inspectedAt = tx.decision_timestamp || tx.inspected_at || timeStr;
  const justification = tx.reason || tx.ly_do || 'Abnormal Balance Discrepancy';
  const formattedAmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(amt);

  if (isInspectedView) {
    return (
      <tr key={txId} style={{ transition: 'background-color 0.15s ease' }}>
        <td style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: '#09090b', fontSize: '0.8125rem' }}>
          {txId}
        </td>
        <td>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.2rem 0.55rem',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: 700,
            backgroundColor: isFraud ? '#fee2e2' : '#dcfce7',
            color: isFraud ? '#991b1b' : '#166534',
            border: `1px solid ${isFraud ? '#fecaca' : '#bbf7d0'}`,
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: isFraud ? '#dc2626' : '#16a34a' }} />
            {isFraud ? 'FRAUD (1)' : 'LEGIT (0)'}
          </span>
        </td>
        <td style={{ color: '#09090b', fontWeight: 600, fontSize: '0.8125rem' }} title={auditorTooltip}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              backgroundColor: '#f4f4f5',
              border: '1px solid #e4e4e7',
              fontSize: '0.625rem',
              fontWeight: 700,
              color: '#52525b',
            }}>
              {String(auditorStaff)[0]?.toUpperCase() || 'A'}
            </span>
            <span style={{ borderBottom: '1px dotted #a1a1aa', cursor: 'help' }}>
              {auditorStaff}
            </span>
          </div>
        </td>
        <td style={{ color: '#71717a', fontSize: '0.75rem' }}>
          {formatVietnamTime(inspectedAt)}
        </td>
        <td style={{ color: '#52525b', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.75rem' }} title={justification}>
          {justification}
        </td>
        <td style={{ fontWeight: 600, color: '#09090b', fontSize: '0.8125rem' }}>
          {formattedAmt}
        </td>
        <td>
          <span style={{
            backgroundColor: '#f4f4f5',
            border: '1px solid #e4e4e7',
            padding: '0.15rem 0.45rem',
            borderRadius: '4px',
            fontSize: '0.75rem',
            color: '#27272a',
          }}>
            {channel}
          </span>
        </td>
        <td style={{ textAlign: 'right' }}>
          <button
            onClick={() => onSelectTx && onSelectTx(txId)}
            className="btn-shadcn btn-outline"
            style={{ height: '1.75rem', padding: '0 0.55rem', fontSize: '0.72rem', gap: '0.2rem' }}
          >
            <span>Review</span>
            <ChevronRight size={12} strokeWidth={2} />
          </button>
        </td>
      </tr>
    );
  }

  // Pending queue row
  return (
    <tr key={txId} style={{ transition: 'background-color 0.15s ease' }}>
      <td style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: '#09090b', fontSize: '0.8125rem' }}>
        {txId}
      </td>
      <td style={{ color: '#71717a', fontSize: '0.75rem' }}>
        {formatVietnamTime(timeStr)}
      </td>
      <td style={{ color: '#27272a', fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem' }}>
        {srcAcc} ➔ {dstAcc}
      </td>
      <td>
        <span style={{
          backgroundColor: '#f4f4f5',
          border: '1px solid #e4e4e7',
          padding: '0.15rem 0.45rem',
          borderRadius: '4px',
          fontSize: '0.75rem',
          color: '#27272a',
        }}>
          {channel} {transType ? `• ${transType}` : ''}
        </span>
      </td>
      <td style={{ fontWeight: 600, color: '#09090b', fontSize: '0.8125rem' }}>
        {formattedAmt}
      </td>
      <td>
        <span style={{
          fontWeight: 700,
          color: score >= 0.8 ? '#dc2626' : (score >= 0.5 ? '#d97706' : '#16a34a'),
          fontSize: '0.8125rem',
        }}>
          {scorePct}%
        </span>
      </td>
      <td>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.35rem',
          padding: '0.15rem 0.5rem',
          borderRadius: '9999px',
          fontSize: '0.6875rem',
          fontWeight: 600,
          backgroundColor: isProcessed ? '#f4f4f5' : '#fef2f2',
          color: isProcessed ? '#71717a' : '#991b1b',
          border: `1px solid ${isProcessed ? '#e4e4e7' : '#fee2e2'}`,
        }}>
          {isProcessed ? <CheckCircle2 size={11} strokeWidth={2.5} /> : <Clock size={11} strokeWidth={2.5} />}
          <span>{isProcessed ? 'Inspected' : 'Pending'}</span>
        </span>
      </td>
      <td style={{ textAlign: 'right' }}>
        <button
          onClick={() => onSelectTx && onSelectTx(txId)}
          className="btn-shadcn btn-outline"
          style={{ height: '1.75rem', padding: '0 0.6rem', fontSize: '0.75rem', gap: '0.25rem' }}
        >
          <span>Inspect</span>
          <ChevronRight size={13} strokeWidth={1.5} />
        </button>
      </td>
    </tr>
  );
}

