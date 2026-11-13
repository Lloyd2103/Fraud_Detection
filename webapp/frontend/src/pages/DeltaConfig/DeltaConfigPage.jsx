import React, { useState, useEffect, useCallback } from 'react';
import { 
  Database, Server, RefreshCw, HardDrive, CheckCircle2, ShieldCheck, 
  Layers, Zap, Cpu, AlertCircle, FileCode,
} from 'lucide-react';
import { useDeltaConfig } from '../../hooks/useDeltaConfig';

export default function DeltaConfigPage() {
  const { getConfig } = useDeltaConfig();
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getConfig();
      setConfig(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch Delta Lake configuration.');
    } finally {
      setLoading(false);
    }
  }, [getConfig]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const infra = config?.infrastructure || {};
  const tables = config?.medallion_tables || [];
  const properties = config?.table_properties || [];
  const constraints = config?.check_constraints || [];

  // Replication factor: only a real number is shown; null/undefined means "not measured".
  const replicationRaw = infra.replication_factor ?? infra.hdfs?.replication;
  const replication = replicationRaw === null || replicationRaw === undefined ? null : Number(replicationRaw);
  const replicationKnown = replication !== null && Number.isFinite(replication);
  const replicationText = !replicationKnown
    ? 'Unavailable'
    : replication >= 2
      ? `${replication}x replication (fault-tolerant)`
      : `${replication}x replication (no redundancy)`;
  const replicationColor = !replicationKnown ? '#71717a' : replication >= 2 ? '#16a34a' : '#d97706';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', minWidth: 0, maxWidth: '100%' }}>
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#09090b', margin: '0 0 0.25rem 0' }}>
            Delta Lake Infrastructure &amp; Medallion Architecture
          </h2>
          <p style={{ fontSize: '0.8125rem', color: '#71717a', margin: 0 }}>
            Unified metadata, HDFS storage hierarchy, Delta Lake table features, and data governance policies.
          </p>
        </div>
        <button
          onClick={loadConfig}
          disabled={loading}
          className="btn-shadcn btn-secondary"
          style={{ height: '2.25rem', padding: '0 0.85rem' }}
        >
          <RefreshCw size={13} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          <span>Refresh Metadata</span>
        </button>
      </div>

      {error && (
        <div style={{
          padding: '0.85rem 1rem',
          borderRadius: '8px',
          backgroundColor: '#fef2f2',
          border: '1px solid #fee2e2',
          color: '#991b1b',
          fontSize: '0.8125rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Cluster Hardware & HDFS Environment */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '0.9375rem', fontWeight: 600, color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Server size={16} />
          <span>Distributed Storage &amp; Engine Environment</span>
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
          <div style={{ backgroundColor: '#fafafa', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Delta Lake &amp; Spark Engine</div>
            <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#09090b', marginTop: '0.2rem' }}>
              {infra.delta_lake_version || infra.compute_engine?.delta || 'Unavailable'} &bull; {infra.spark_version ? `Spark ${infra.spark_version}` : (infra.compute_engine?.spark || 'Unavailable')}
            </div>
          </div>
          <div style={{ backgroundColor: '#fafafa', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>HDFS Active Namenode</div>
            <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#09090b', marginTop: '0.2rem', fontFamily: "'JetBrains Mono', monospace" }}>
              {infra.hdfs_namenode || infra.hdfs?.namenode_uri || 'Unavailable'}
            </div>
          </div>
          <div style={{ backgroundColor: '#fafafa', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Replication Factor</div>
            <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: replicationColor, marginTop: '0.2rem' }}>
              {replicationText}
            </div>
          </div>
          <div style={{ backgroundColor: '#fafafa', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
            <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Hadoop Version</div>
            <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#09090b', marginTop: '0.2rem' }}>
              {infra.hadoop_version ? `Apache Hadoop ${infra.hadoop_version}` : (infra.hdfs?.hadoop_version ? `Apache Hadoop ${infra.hdfs.hadoop_version}` : 'Unavailable')}
            </div>
          </div>
        </div>
      </div>

      {/* Medallion Architecture Table Paths */}
      <div className="shadcn-card" style={{ overflow: 'hidden', minWidth: 0, maxWidth: '100%' }}>
        <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e4e4e7', backgroundColor: '#ffffff' }}>
          <h3 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 600, color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Layers size={16} />
            <span>Medallion Architecture Layer Hierarchy</span>
          </h3>
        </div>
        <div style={{ width: '100%', maxWidth: '100%', overflowX: 'auto' }}>
          <table className="shadcn-table">
            <thead>
              <tr>
                <th>Tier</th>
                <th>Logical Name</th>
                <th>Storage Physical Path</th>
                <th>Format &amp; Schema</th>
                <th>Frequency</th>
                <th>Role in Architecture</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {tables.map((t, idx) => {
                const tierName = t.tier || t.layer || 'Table';
                const isBronze = tierName.toLowerCase().includes('bronze');
                const isSilver = tierName.toLowerCase().includes('silver');
                const statusStr = String(t.status || 'Unknown');
                const isStatusUnavailable = statusStr.toLowerCase().includes('unavailable') || statusStr.toLowerCase().includes('unknown') || statusStr.toLowerCase().includes('error');
                return (
                  <tr key={idx}>
                    <td>
                      <span style={{
                        fontWeight: 700,
                        fontSize: '0.6875rem',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '4px',
                        backgroundColor: isBronze ? '#fef3c7' : isSilver ? '#f4f4f5' : '#fef9c3',
                        color: isBronze ? '#92400e' : isSilver ? '#27272a' : '#854d0e',
                        border: `1px solid ${isBronze ? '#fde68a' : isSilver ? '#e4e4e7' : '#fef08a'}`
                      }}>
                        {tierName}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: '#09090b' }}>{t.name || '—'}</td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", color: '#71717a', fontSize: '0.75rem', wordBreak: 'break-all', minWidth: '180px', maxWidth: '300px' }}>{t.path || '—'}</td>
                    <td>
                      <span style={{ backgroundColor: '#f4f4f5', padding: '0.1rem 0.4rem', borderRadius: '4px', fontSize: '0.75rem', fontFamily: "'JetBrains Mono', monospace" }}>
                        {t.format || '—'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.75rem', color: '#71717a', minWidth: '160px', maxWidth: '260px' }}>{t.frequency || '—'}</td>
                    <td style={{ color: '#52525b', fontSize: '0.8125rem', minWidth: '150px' }}>{t.role || t.description || '—'}</td>
                    <td>
                      <span style={{
                        fontSize: '0.6875rem',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                        color: isStatusUnavailable ? '#71717a' : '#16a34a',
                        backgroundColor: isStatusUnavailable ? '#f4f4f5' : '#f0fdf4',
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        border: `1px solid ${isStatusUnavailable ? '#e4e4e7' : '#dcfce7'}`
                      }}>
                        {t.status || 'Unknown'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delta 3.1 Table Properties & ACID Config */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(400px, 100%), 1fr))', gap: '1.25rem' }}>
        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <h3 style={{ margin: '0 0 0.85rem 0', fontSize: '0.9375rem', fontWeight: 600, color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <FileCode size={16} />
            <span>Delta Lake Table Properties (`TBLPROPERTIES`)</span>
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {properties.map((p, idx) => {
              const propKey = p.property || p.key || '—';
              const valStr = String(p.value ?? 'Unavailable');
              const isUnavailable = p.status !== 'SET' || valStr.toLowerCase().includes('unavailable') || valStr.toLowerCase().includes('unknown');
              return (
                <div key={idx} style={{ padding: '0.65rem 0.85rem', backgroundColor: '#fafafa', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                    <code style={{ fontSize: '0.75rem', fontWeight: 600, color: '#09090b' }}>{propKey}</code>
                    <span style={{
                      fontSize: '0.6875rem',
                      fontWeight: 600,
                      color: isUnavailable ? '#71717a' : '#16a34a',
                      backgroundColor: isUnavailable ? '#f4f4f5' : '#f0fdf4',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '4px',
                      border: `1px solid ${isUnavailable ? '#e4e4e7' : '#dcfce7'}`
                    }}>
                      {p.value ?? 'Unavailable'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#71717a' }}>{p.description || '—'}</div>
                  {p.scope && (
                    <div style={{ fontSize: '0.7rem', color: '#a1a1aa', marginTop: '0.2rem' }}>Scope: {p.scope}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ACID Constraints & Integrity Rules */}
        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <h3 style={{ margin: '0 0 0.85rem 0', fontSize: '0.9375rem', fontWeight: 600, color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <ShieldCheck size={16} />
            <span>ACID Data Integrity &amp; CHECK Constraints</span>
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {constraints.map((c, idx) => {
              const ruleExpr = c.expression || c.rule || '—';
              const statusStr = String(c.status || 'Unavailable');
              const isEnforced = statusStr === 'ENFORCED';
              const isUnavailable = statusStr.toLowerCase().includes('unavailable') || statusStr.toLowerCase().includes('unknown');
              return (
                <div key={idx} style={{ padding: '0.65rem 0.85rem', backgroundColor: '#fafafa', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#09090b' }}>
                      {(c.name === 'so_tien_duong' ? 'positive_amount' : c.name) || 'Constraint'} &bull; <span style={{ color: '#71717a' }}>{c.table || '—'}</span>
                    </span>
                    <span style={{
                      fontSize: '0.6875rem',
                      fontWeight: 600,
                      color: isEnforced ? '#16a34a' : isUnavailable ? '#71717a' : '#d97706',
                      backgroundColor: isEnforced ? '#f0fdf4' : isUnavailable ? '#f4f4f5' : '#fffbeb',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '4px',
                      border: `1px solid ${isEnforced ? '#dcfce7' : isUnavailable ? '#e4e4e7' : '#fef3c7'}`
                    }}>
                      {c.status || 'Unavailable'}
                    </span>
                  </div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem', color: '#dc2626', backgroundColor: '#fef2f2', padding: '0.2rem 0.4rem', borderRadius: '4px', display: 'inline-block' }}>
                    {ruleExpr}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#71717a', marginTop: '0.25rem' }}>{c.description || '—'}</div>
                  {c.note && (
                    <div style={{ fontSize: '0.6875rem', color: '#71717a', marginTop: '0.25rem', fontStyle: 'italic' }}>
                      * {c.note}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
