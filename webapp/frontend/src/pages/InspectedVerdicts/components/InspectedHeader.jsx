import React from 'react';
import { RotateCw } from 'lucide-react';

export default function InspectedHeader({
  lastUpdatedTime,
  fetchTableData,
  onSwitchTab,
  pendingCount,
  totalRecords,
}) {
  return (
    <div style={{
      padding: '1rem 1.25rem',
      borderBottom: '1px solid #e4e4e7',
      backgroundColor: '#ffffff',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: '0.75rem',
    }}>
      <div>
        <h3 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 600, color: '#09090b' }}>
          Audited Verdicts History
        </h3>
        <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: '#71717a' }}>
          Audited transactions with human-in-the-loop labels for model retraining
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {lastUpdatedTime && (
          <span style={{ fontSize: '0.75rem', color: '#71717a', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <RotateCw size={11} /> Updated at {lastUpdatedTime.toLocaleTimeString('en-US', { hour12: false })}
          </span>
        )}
        <button onClick={fetchTableData} className="btn-shadcn btn-secondary" style={{ height: '1.875rem', padding: '0 0.5rem', fontSize: '0.75rem' }}>
          Refresh
        </button>

        {/* Pill Toggle */}
        <div style={{ display: 'inline-flex', padding: '2px', backgroundColor: '#f4f4f5', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
          <button
            type="button"
            onClick={() => onSwitchTab ? onSwitchTab('alerts') : (window.location.hash = '#alerts')}
            style={{
              padding: '0.25rem 0.65rem',
              fontSize: '0.75rem',
              fontWeight: 500,
              borderRadius: '4px',
              backgroundColor: 'transparent',
              color: '#71717a',
              border: 'none',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <span>Pending Queue</span>
            <span style={{ fontSize: '0.6875rem', padding: '0.05rem 0.35rem', borderRadius: '9999px', backgroundColor: '#e4e4e7', color: '#52525b', fontWeight: 600 }}>
              {pendingCount ?? '—'}
            </span>
          </button>
          <button
            type="button"
            style={{
              padding: '0.25rem 0.65rem',
              fontSize: '0.75rem',
              fontWeight: 600,
              borderRadius: '4px',
              backgroundColor: '#ffffff',
              color: '#09090b',
              boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
              border: 'none',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <span>Inspected Verdicts</span>
            <span style={{ fontSize: '0.6875rem', padding: '0.05rem 0.35rem', borderRadius: '9999px', backgroundColor: '#16a34a', color: '#ffffff', fontWeight: 600 }}>
              {totalRecords}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

