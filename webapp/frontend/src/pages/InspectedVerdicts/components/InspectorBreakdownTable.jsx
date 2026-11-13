import React from 'react';
import { Download } from 'lucide-react';

export default function InspectorBreakdownTable({
  verdictStats,
  activeRangeLabel,
  period,
  selectedDate,
  selectedMonth,
}) {
  const inspectors = verdictStats?.per_inspector || [];

  const handleExportCsv = () => {
    if (!inspectors.length) return;
    const headers = ['auditor_id', 'username', 'full_name', 'total_verdicts', 'fraud', 'legit', 'fraud_rate_pct'];
    const rows = inspectors.map((i) => [
      i.inspector_id,
      `"${i.username || ''}"`,
      `"${i.full_name || ''}"`,
      i.total,
      i.fraud,
      i.legit,
      (i.fraud_rate * 100).toFixed(2),
    ]);
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `auditor_stats_${period}_${period === 'day' ? selectedDate : selectedMonth}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="shadcn-card" style={{ padding: '1.25rem', marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 600, color: '#09090b' }}>
            Auditor Performance Breakdown ({activeRangeLabel})
          </h4>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: '#71717a' }}>
            Inspection performance per auditor in the selected time range
          </p>
        </div>
        <button
          onClick={handleExportCsv}
          disabled={!inspectors.length}
          className="btn-shadcn btn-secondary"
          style={{ height: '1.875rem', padding: '0 0.65rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
        >
          <Download size={13} />
          <span>Export CSV</span>
        </button>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e4e4e7', textAlign: 'left', color: '#71717a', fontSize: '0.75rem', textTransform: 'uppercase' }}>
              <th style={{ padding: '0.5rem 0.75rem', fontWeight: 600 }}>Auditor Name</th>
              <th style={{ padding: '0.5rem 0.75rem', fontWeight: 600 }}>Username</th>
              <th style={{ padding: '0.5rem 0.75rem', fontWeight: 600, textAlign: 'right' }}>Total Verdicts</th>
              <th style={{ padding: '0.5rem 0.75rem', fontWeight: 600, textAlign: 'right' }}>FRAUD</th>
              <th style={{ padding: '0.5rem 0.75rem', fontWeight: 600, textAlign: 'right' }}>LEGIT</th>
              <th style={{ padding: '0.5rem 0.75rem', fontWeight: 600, textAlign: 'right' }}>Fraud Rate</th>
            </tr>
          </thead>
          <tbody>
            {inspectors.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '1.5rem', textAlign: 'center', color: '#a1a1aa' }}>
                  No auditor performance data in this period
                </td>
              </tr>
            ) : (
              inspectors.map((insp) => (
                <tr key={insp.inspector_id} style={{ borderBottom: '1px solid #f4f4f5' }}>
                  <td style={{ padding: '0.5rem 0.75rem', fontWeight: 600, color: '#09090b' }}>
                    {insp.full_name || insp.username || `User #${insp.inspector_id}`}
                  </td>
                  <td style={{ padding: '0.5rem 0.75rem', color: '#71717a' }}>
                    {insp.username || '—'}
                  </td>
                  <td style={{ padding: '0.5rem 0.75rem', textAlign: 'right', fontWeight: 600 }}>
                    {insp.total}
                  </td>
                  <td style={{ padding: '0.5rem 0.75rem', textAlign: 'right', fontWeight: 600, color: '#dc2626' }}>
                    {insp.fraud}
                  </td>
                  <td style={{ padding: '0.5rem 0.75rem', textAlign: 'right', fontWeight: 600, color: '#16a34a' }}>
                    {insp.legit}
                  </td>
                  <td style={{ padding: '0.5rem 0.75rem', textAlign: 'right', fontWeight: 600, color: insp.fraud_rate > 0.5 ? '#dc2626' : '#09090b' }}>
                    {(insp.fraud_rate * 100).toFixed(1)}%
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
