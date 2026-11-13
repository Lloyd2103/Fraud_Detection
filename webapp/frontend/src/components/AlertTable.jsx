import React from 'react';
import AlertTableRow from './AlertTableRow';

export default function AlertTable({
  alerts = [],
  onSelectTx,
  hasFilters = false,
  onResetFilters = null,
  isInspectedView = false,
  sortBy = 'risk_score',
  sortOrder = 'desc',
  sortCriteria = [],
  onSort = null,
}) {
  if (!alerts.length) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '3.5rem 1.5rem',
        color: '#71717a',
        fontSize: '0.875rem',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.75rem',
      }}>
        {isInspectedView ? (
          <div>No inspected verdicts recorded for this date</div>
        ) : hasFilters ? (
          <>
            <div style={{ color: '#09090b', fontWeight: 600 }}>
              No transactions match the current filters
            </div>
            <div style={{ color: '#71717a', fontSize: '0.8125rem' }}>
              Try adjusting the Channel, Amount range, or search keywords.
            </div>
            {onResetFilters && (
              <button
                onClick={onResetFilters}
                className="btn-shadcn btn-secondary"
                style={{ height: '2rem', padding: '0 0.85rem', fontSize: '0.75rem', marginTop: '0.25rem' }}
              >
                Reset All Filters
              </button>
            )}
          </>
        ) : (
          <div>
            No alert transactions in queue. Waiting for Kafka stream &amp; Delta Lake telemetry.
          </div>
        )}
      </div>
    );
  }

  // Determine active sort criteria
  const activeCriteria = (sortCriteria && sortCriteria.length > 0)
    ? sortCriteria
    : (sortBy ? [{ field: sortBy, order: sortOrder || 'desc' }] : []);

  const getSortInfo = (field) => {
    const idx = activeCriteria.findIndex((c) => c.field === field);
    if (idx === -1) return null;
    return {
      priority: idx + 1,
      order: activeCriteria[idx].order,
      total: activeCriteria.length,
    };
  };

  const renderSortHeader = (label, field, highlightColor = null) => {
    const info = getSortInfo(field);
    const isActive = !!info;
    const isPri1 = info && info.priority === 1;

    return (
      <th
        onClick={() => onSort && onSort(field)}
        style={{
          cursor: onSort ? 'pointer' : 'default',
          userSelect: 'none',
          whiteSpace: 'nowrap',
          backgroundColor: isPri1 ? 'rgba(37, 99, 235, 0.08)' : (isActive ? 'rgba(37, 99, 235, 0.03)' : undefined),
          transition: 'all 0.15s ease',
        }}
        title={
          isActive
            ? (isPri1
              ? `Priority #1 (Primary: ${info.order === 'desc' ? 'Descending' : 'Ascending'}). Click to reverse.`
              : `Priority #${info.priority} (Secondary). Click to make Priority #1.`)
            : `Click to add ${label} to sort.`
        }
      >
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{
            color: isPri1 ? (highlightColor || '#2563eb') : (isActive ? '#334155' : undefined),
            fontWeight: isActive ? 700 : undefined,
          }}>
            {label}
          </span>
          {isActive && (
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '2px',
              fontSize: '0.7rem',
              padding: '1px 5px',
              borderRadius: '4px',
              backgroundColor: isPri1 ? (info.order === 'desc' ? '#eff6ff' : '#fef2f2') : '#f1f5f9',
              color: isPri1 ? (info.order === 'desc' ? '#1d4ed8' : '#b91c1c') : '#475569',
              border: isPri1 ? `1px solid ${info.order === 'desc' ? '#bfdbfe' : '#fecaca'}` : '1px solid #cbd5e1',
              fontWeight: 700,
              lineHeight: 1.2,
            }}>
              {info.total > 1 && (
                <span style={{
                  fontSize: '0.625rem',
                  backgroundColor: isPri1 ? (info.order === 'desc' ? '#2563eb' : '#dc2626') : '#94a3b8',
                  color: '#ffffff',
                  borderRadius: '50%',
                  width: '13px',
                  height: '13px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: '1px',
                }}>
                  {info.priority}
                </span>
              )}
              <span>{info.order === 'desc' ? '↓' : '↑'}</span>
            </span>
          )}
        </div>
      </th>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ width: '100%', overflowX: 'auto' }}>
        <table className="shadcn-table">
          <thead>
            {isInspectedView ? (
              <tr>
                <th>Tx ID</th>
                <th>Recorded Verdict</th>
                <th>Auditor Staff</th>
                <th>Inspected At</th>
                <th>Justification &amp; Notes</th>
                <th>Amount</th>
                <th>Channel</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            ) : (
              <tr>
                <th>Tx ID</th>
                {renderSortHeader('Event time (dataset)', 'timestamp')}
                <th>Source ➔ Destination</th>
                <th>Channel</th>
                {renderSortHeader('Amount', 'amount')}
                {renderSortHeader('Risk Score', 'risk_score', '#dc2626')}
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            )}
          </thead>
          <tbody>
            {alerts.map((tx, idx) => (
              <AlertTableRow
                key={tx.ma_giao_dich || tx.transaction_id || `TX_${idx}`}
                tx={tx}
                idx={idx}
                isInspectedView={isInspectedView}
                onSelectTx={onSelectTx}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
