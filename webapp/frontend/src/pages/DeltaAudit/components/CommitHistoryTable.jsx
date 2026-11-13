import React from 'react';
import { History, ChevronLeft, ChevronRight } from 'lucide-react';
import { formatVietnamTime } from '../../../utils/formatters';

const getOpBadge = (opStr = '') => {
  const s = opStr.toUpperCase();
  if (s.includes('MERGE')) return { bg: '#eff6ff', color: '#1d4ed8', border: '#bfdbfe' };
  if (s.includes('OPTIMIZE')) return { bg: '#faf5ff', color: '#7e22ce', border: '#e9d5ff' };
  if (s.includes('SET TBLPROPERTIES')) return { bg: '#fefce8', color: '#a16207', border: '#fef08a' };
  if (s.includes('WRITE') || s.includes('APPEND')) return { bg: '#f0fdf4', color: '#15803d', border: '#bbf7d0' };
  return { bg: '#f4f4f5', color: '#09090b', border: '#e4e4e7' };
};

const formatOperationDesc = (c) => {
  const op = c.operation || '';
  if (op === 'SET TBLPROPERTIES') {
    let props = c.operationParameters?.properties;
    if (typeof props === 'string') {
      try {
        const parsed = JSON.parse(props);
        const pairs = Object.entries(parsed).map(([k, v]) => `${k}=${v}`).join(', ');
        return `set property: ${pairs}`;
      } catch {
        return `set property: ${props}`;
      }
    } else if (props && typeof props === 'object') {
      const pairs = Object.entries(props).map(([k, v]) => `${k}=${v}`).join(', ');
      return `set property: ${pairs}`;
    }
    return 'set table properties';
  }
  const metrics = c.operationMetrics;
  if (metrics && (metrics.numFiles || metrics.numOutputRows || metrics.numTargetRowsInserted)) {
    const parts = [];
    if (metrics.numFiles) parts.push(`${metrics.numFiles} file(s)`);
    const rows = metrics.numOutputRows || metrics.numTargetRowsInserted || metrics.numTargetRowsUpdated;
    if (rows) parts.push(`${Number(rows).toLocaleString('en-US')} rows written`);
    if (parts.length > 0) return parts.join(', ');
  }
  if (c.operationParameters?.mode) {
    return `Write (${c.operationParameters.mode})`;
  }
  return typeof c.operationMetrics === 'object' && Object.keys(c.operationMetrics || {}).length > 0
    ? JSON.stringify(c.operationMetrics)
    : (c.operation || 'Delta transaction commit');
};

export default function CommitHistoryTable({
  currentCommits,
  totalCommitsCount,
  auditData,
  historyPage,
  setHistoryPage,
  totalPages,
  loadedVersion,
  loading,
}) {
  return (
    <div className="shadcn-card" style={{ overflow: 'hidden' }}>
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e4e4e7', backgroundColor: '#ffffff', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h4 style={{ margin: '0 0 0.2rem 0', color: '#09090b', fontSize: '0.9375rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <History size={16} strokeWidth={1.5} />
            <span>Delta Lake Transaction Log Commit History (DESCRIBE HISTORY)</span>
          </h4>
          <p style={{ fontSize: '0.75rem', color: '#71717a', margin: 0 }}>
            Showing {currentCommits.length} commits of latest {totalCommitsCount} commits (out of {auditData?.head_version != null ? auditData.head_version + 1 : totalCommitsCount} commits in Delta history).
          </p>
        </div>

        {totalPages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <button
              disabled={historyPage <= 1}
              onClick={() => setHistoryPage((p) => p - 1)}
              className="btn-shadcn btn-secondary"
              style={{ height: '26px', padding: '0 0.5rem', fontSize: '0.75rem' }}
            >
              <ChevronLeft size={13} />
              <span>Prev</span>
            </button>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#09090b', padding: '0 0.3rem' }}>
              {historyPage} / {totalPages}
            </span>
            <button
              disabled={historyPage >= totalPages}
              onClick={() => setHistoryPage((p) => p + 1)}
              className="btn-shadcn btn-secondary"
              style={{ height: '26px', padding: '0 0.5rem', fontSize: '0.75rem' }}
            >
              <span>Next</span>
              <ChevronRight size={13} />
            </button>
          </div>
        )}
      </div>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <table className="shadcn-table">
          <thead>
            <tr>
              <th>Version</th>
              <th>Timestamp</th>
              <th>Operation</th>
              <th>Engine</th>
              <th>Author</th>
              <th>Operation Description / Metrics</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2.5rem', color: '#71717a', fontSize: '0.875rem' }}>
                  Reading Delta Lake transaction log history...
                </td>
              </tr>
            ) : currentCommits.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: '#71717a' }}>
                  No commit history found in target table.
                </td>
              </tr>
            ) : (
              currentCommits.map((c, idx) => {
                const isSelected = c.version === loadedVersion;
                const op = c.operation || c.operationType || 'WRITE';
                const badgeStyle = getOpBadge(op);
                const user = c.userName || 'unknown';
                const engine = c.engineInfo || c.engine || 'Spark 3.5 / Delta 3.1';
                const desc = formatOperationDesc(c);

                return (
                  <tr
                    key={c.version ?? idx}
                    style={{
                      backgroundColor: isSelected ? '#f4f4f5' : 'transparent',
                      fontWeight: isSelected ? 600 : 400,
                    }}
                  >
                    <td style={{ fontWeight: 600, color: isSelected ? '#09090b' : '#27272a' }}>
                      Version #{c.version} {isSelected && <span style={{ fontSize: '0.6875rem', color: '#dc2626', fontWeight: 700, marginLeft: '0.3rem' }}>(SELECTED)</span>}
                    </td>
                    <td style={{ color: '#71717a', fontSize: '0.8125rem' }}>
                      {formatVietnamTime(c.timestamp)}
                    </td>
                    <td>
                      <span style={{
                        padding: '0.15rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        backgroundColor: badgeStyle.bg,
                        color: badgeStyle.color,
                        border: `1px solid ${badgeStyle.border}`,
                      }}>
                        {op}
                      </span>
                    </td>
                    <td style={{ color: '#71717a', fontSize: '0.8125rem' }}>
                      {engine}
                    </td>
                    <td style={{ color: '#09090b', fontFamily: "'JetBrains Mono', monospace", fontSize: '0.8125rem' }}>
                      {user}
                    </td>
                    <td style={{ color: '#71717a', maxWidth: '340px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.75rem', fontFamily: "'JetBrains Mono', monospace" }} title={desc}>
                      {desc}
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

