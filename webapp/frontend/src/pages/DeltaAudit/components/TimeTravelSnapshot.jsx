import React from 'react';
import {
  History, Play, CheckCircle2, AlertTriangle, Database, ShieldCheck,
  GitCommit, Layers, Loader2
} from 'lucide-react';
import { formatVietnamTime } from '../../../utils/formatters';

const pct = (x) => (x === null || x === undefined || Number.isNaN(Number(x)) ? '—' : `${(Number(x) * 100).toFixed(2)}%`);

const STATUS_STYLE = {
  MATCH: { bg: '#dcfce7', fg: '#166534' },
  MISMATCH: { bg: '#fee2e2', fg: '#b91c1c' },
  NOT_AVAILABLE: { bg: '#f4f4f5', fg: '#52525b' },
};

function StatusBadge({ status }) {
  const label = status || 'NOT_AVAILABLE';
  const st = STATUS_STYLE[label] || STATUS_STYLE.NOT_AVAILABLE;
  return (
    <span style={{ fontSize: '0.6875rem', fontWeight: 700, padding: '0.1rem 0.35rem', borderRadius: '3px', backgroundColor: st.bg, color: st.fg }}>
      {label}
    </span>
  );
}

export default function TimeTravelSnapshot({
  selectedVersion,
  setSelectedVersion,
  loadedVersion,
  commits,
  modelRegistryMap,
  handleManualLoad,
  handleKeyDown,
  loading,
  loadError,
  auditData,
  user,
  forceRecompute,
  setForceRecompute,
  handleRerun,
  rerunLoading,
  rerunResult,
}) {
  return (
    <>
      {/* Header Banner */}
      <div className="shadcn-card" style={{ padding: '1.25rem', backgroundColor: '#ffffff' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ margin: '0 0 0.35rem 0', fontSize: '1.125rem', fontWeight: 700, color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <History size={20} strokeWidth={2} />
              <span>Delta Lake Time Travel &amp; Reproducible Audit</span>
            </h2>
            <p style={{ margin: 0, fontSize: '0.8125rem', color: '#71717a' }}>
              Query historical table states using Delta Lake ACID log transaction commits (<code>VERSION AS OF {loadedVersion ?? selectedVersion ?? '<version>'}</code>).
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0891b2', backgroundColor: '#ecfeff', padding: '0.2rem 0.6rem', borderRadius: '4px', border: '1px solid #cff4fc' }}>
              ACID Guaranteed
            </span>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#16a34a', backgroundColor: '#f0fdf4', padding: '0.2rem 0.6rem', borderRadius: '4px', border: '1px solid #dcfce7' }}>
              Zero Copy Snapshot
            </span>
          </div>
        </div>
      </div>

      {/* Snapshot Controls & Metrics Card */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <label style={{ color: '#09090b', fontWeight: 600, fontSize: '0.8125rem' }}>
              Select Delta Commit / Model:
            </label>
            <select
              value={selectedVersion ?? ''}
              onChange={(e) => setSelectedVersion(Number(e.target.value))}
              className="shadcn-input"
              style={{ width: 'auto', fontWeight: 500, cursor: 'pointer', appearance: 'auto', minWidth: '400px' }}
            >
              {commits.length > 0 ? (
                commits.map((c) => {
                  let tag = '';
                  const mInfo = modelRegistryMap[c.version];
                  if (mInfo) {
                    tag = `[${mInfo.model_version}${mInfo.is_active === 1 ? ' - ACTIVE' : ''}] `;
                  } else if (c.operation === 'SET TBLPROPERTIES') {
                    tag = '[CDF Enabled] ';
                  } else if (c.operation === 'WRITE') {
                    tag = '[Streaming Batch] ';
                  }

                  return (
                    <option key={c.version} value={c.version}>
                      {tag}Commit #{c.version} ({c.operation} • {formatVietnamTime(c.timestamp)})
                    </option>
                  );
                })
              ) : (
                <option value={selectedVersion ?? ''}>{selectedVersion !== null && selectedVersion !== undefined ? `Delta Commit #${selectedVersion}` : 'No commit loaded'}</option>
              )}
            </select>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.75rem', color: '#71717a' }}>or Version:</span>
              <input
                type="number"
                min="0"
                value={selectedVersion ?? ''}
                onChange={(e) => setSelectedVersion(e.target.value === '' ? null : Number(e.target.value))}
                onKeyDown={handleKeyDown}
                className="shadcn-input"
                style={{ width: '85px', height: '2.1rem', textAlign: 'center', fontWeight: 600 }}
              />
            </div>

            <button
              onClick={handleManualLoad}
              disabled={loading}
              className="btn-shadcn btn-secondary"
              style={{ height: '2.1rem', padding: '0 0.85rem', fontSize: '0.78125rem', fontWeight: 600 }}
            >
              {loading ? (
                <>
                  <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Loading...</span>
                </>
              ) : (
                <span>Load Snapshot</span>
              )}
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            {user?.role === 'admin' && (
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: '#71717a', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={forceRecompute}
                  onChange={(e) => setForceRecompute(e.target.checked)}
                  style={{ cursor: 'pointer' }}
                />
                <span>Force recompute (bypass saved results)</span>
              </label>
            )}

            <button
              onClick={handleRerun}
              disabled={rerunLoading || loading || !auditData || loadedVersion === null || loadedVersion === undefined}
              title={auditData ? undefined : 'Load a snapshot first'}
              className="btn-shadcn btn-primary"
              style={{ height: '2.25rem', padding: '0 1rem' }}
            >
              {rerunLoading ? (
                <>
                  <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Re-evaluating...</span>
                </>
              ) : (
                <>
                  <Play size={13} strokeWidth={2} />
                  <span>Rerun Evaluation on this Version</span>
                </>
              )}
            </button>
          </div>
        </div>

        {loadError && (
          <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', padding: '0.75rem 1rem', marginBottom: '1rem', color: '#dc2626', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={15} />
            <span>Cannot load snapshot: {loadError}</span>
          </div>
        )}

        {/* 4 Summary Badges */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
          <div style={{ backgroundColor: '#fafafa', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Database size={13} /> Target Delta Table
            </div>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#09090b', fontFamily: "'JetBrains Mono', monospace", marginTop: '0.2rem' }}>
              {loading ? <span style={{ color: '#a1a1aa' }}>loading...</span> : (auditData?.target_table || '—')}
            </div>
          </div>

          <div style={{ backgroundColor: '#fafafa', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Layers size={13} /> Total Snapshot Records
            </div>
            <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#09090b', marginTop: '0.2rem' }}>
              {loading ? (
                <span style={{ color: '#a1a1aa', fontSize: '0.875rem', fontWeight: 500 }}>loading...</span>
              ) : auditData?.total_records !== undefined ? (
                new Intl.NumberFormat('en-US').format(auditData.total_records)
              ) : (
                '—'
              )}
            </div>
          </div>

          <div style={{ backgroundColor: '#fafafa', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <GitCommit size={13} /> Parquet File List Checksum Hash
            </div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0891b2', fontFamily: "'JetBrains Mono', monospace", marginTop: '0.35rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {loading ? (
                <span style={{ color: '#a1a1aa', fontWeight: 400 }}>loading...</span>
              ) : (
                auditData?.reproducible_hash || '—'
              )}
            </div>
          </div>

          <div style={{ backgroundColor: '#fafafa', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <ShieldCheck size={13} /> Audit Status
            </div>
            <div style={{ fontSize: '0.8125rem', fontWeight: 700, marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              {loading ? (
                <span style={{ color: '#a1a1aa', fontWeight: 400 }}>loading...</span>
              ) : auditData?.audit_compliance_verified ? (
                <span style={{ color: '#16a34a', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                  <CheckCircle2 size={14} strokeWidth={2.5} />
                  <span>Verified valid version in _delta_log</span>
                </span>
              ) : (
                <span style={{ color: '#71717a', fontWeight: 500 }}>Unverified</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Rerun Results Banner */}
      {rerunResult && (rerunResult.status === 'UNAVAILABLE' || rerunResult.available === false) && (
        <div style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', padding: '1.25rem', color: '#92400e' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
            <AlertTriangle size={16} strokeWidth={2} />
            <h4 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 600 }}>
              Re-evaluation not available for Delta Snapshot #{rerunResult.delta_version ?? loadedVersion}
            </h4>
          </div>
          <p style={{ margin: 0, fontSize: '0.8125rem' }}>
            {rerunResult.message || rerunResult.reason || 'No evaluation result could be produced for this version.'}
          </p>
        </div>
      )}

      {rerunResult && rerunResult.status !== 'UNAVAILABLE' && rerunResult.available !== false && (
        <div style={{
          backgroundColor: rerunResult.reproducible_match ? '#f0fdf4' : '#fffbeb',
          border: `1px solid ${rerunResult.reproducible_match ? '#dcfce7' : '#fde68a'}`,
          borderRadius: '8px',
          padding: '1.25rem',
          color: rerunResult.reproducible_match ? '#166534' : '#92400e',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.4rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {rerunResult.reproducible_match ? <CheckCircle2 size={16} strokeWidth={2} /> : <AlertTriangle size={16} strokeWidth={2} />}
              <h4 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 600 }}>
                Audit Re-evaluation Result on Delta Snapshot #{rerunResult.delta_version ?? loadedVersion}
              </h4>
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#f4f4f5', color: '#3f3f46', padding: '0.15rem 0.5rem', borderRadius: '4px' }}>
              Source: {rerunResult.source_label || (rerunResult.source_type === 'saved' ? 'Saved evaluation result (not recomputed)' : 'Fresh recomputation')}
            </span>
          </div>

          {rerunResult.message && (
            <p style={{ margin: '0 0 0.65rem 0', fontSize: '0.8125rem' }}>{rerunResult.message}</p>
          )}

          <div style={{ display: 'flex', gap: '1.25rem', fontSize: '0.8125rem', flexWrap: 'wrap', color: '#3f3f46' }}>
            <div>
              Records Evaluated:{' '}
              <strong style={{ color: '#09090b' }}>
                {rerunResult.records_evaluated !== null && rerunResult.records_evaluated !== undefined
                  ? new Intl.NumberFormat('en-US').format(rerunResult.records_evaluated)
                  : '—'}
              </strong>
            </div>

            <div>
              Precision@200: <strong style={{ color: '#09090b' }}>{pct(rerunResult.original_precision_at_200)}</strong> ➔{' '}
              <strong style={{ color: '#09090b' }}>{pct(rerunResult.reproduced_precision_at_200)}</strong>{' '}
              <StatusBadge status={rerunResult.p200_status} />
            </div>

            <div>
              Recall@200: <strong style={{ color: '#09090b' }}>{pct(rerunResult.original_recall_at_200)}</strong> ➔{' '}
              <strong style={{ color: '#09090b' }}>{pct(rerunResult.reproduced_recall_at_200)}</strong>{' '}
              <StatusBadge status={rerunResult.recall_status} />
            </div>

            {(rerunResult.original_tp !== null && rerunResult.original_tp !== undefined) || (rerunResult.reproduced_tp !== null && rerunResult.reproduced_tp !== undefined) ? (
              <div>
                TP Detected: <strong style={{ color: '#09090b' }}>{rerunResult.original_tp ?? '—'}</strong> ➔{' '}
                <strong style={{ color: '#09090b' }}>{rerunResult.reproduced_tp ?? '—'}</strong>{' '}
                <StatusBadge status={rerunResult.tp_status} />
              </div>
            ) : null}
          </div>
        </div>
      )}
    </>
  );
}

