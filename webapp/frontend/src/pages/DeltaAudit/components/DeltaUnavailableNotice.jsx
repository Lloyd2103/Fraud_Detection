import React from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';

// Shown in place of a Delta table/list when the data cannot be read (for example HDFS is down),
// so an outage is never displayed as "0 commits" or "no records".
export default function DeltaUnavailableNotice({ subject, reason, loading = false }) {
  if (loading) {
    return (
      <div className="shadcn-card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.6rem', color: '#71717a', fontSize: '0.875rem' }}>
        <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
        <span>Loading {subject.toLowerCase()}...</span>
      </div>
    );
  }

  const hdfsDown = typeof reason === 'string' && reason.startsWith('HDFS is unreachable');
  const shortReason = hdfsDown ? 'HDFS unreachable' : (reason || 'reason unknown');

  return (
    <div className="shadcn-card" style={{ padding: '1.25rem', backgroundColor: '#fffbeb', border: '1px solid #fde68a' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#92400e', fontWeight: 600, fontSize: '0.9375rem' }}>
        <AlertTriangle size={16} />
        <span>{subject} unavailable ({shortReason})</span>
      </div>
      {reason && reason !== shortReason && (
        <p style={{ margin: '0.4rem 0 0', fontSize: '0.8125rem', color: '#92400e' }}>{reason}</p>
      )}
    </div>
  );
}
