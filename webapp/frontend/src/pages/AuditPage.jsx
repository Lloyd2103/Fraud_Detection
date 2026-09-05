import React, { useState, useEffect } from 'react';
import { fetchTimeTravel, rerunAuditEvaluation } from '../services/api';

export default function AuditPage() {
  const [version, setVersion] = useState(0);
  const [auditData, setAuditData] = useState(null);

  const loadVersion = (v) => {
    fetchTimeTravel(v).then(res => setAuditData(res.data)).catch(console.error);
  };

  useEffect(() => {
    loadVersion(version);
  }, [version]);

  const handleRerun = async () => {
    try {
      const res = await rerunAuditEvaluation(version);
      alert(`Audit verification successful: Precision@200 reached ${(res.data.reproduced_precision_at_200 * 100).toFixed(1)}%`);
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
  };

  return (
    <div style={{ background: '#111827', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h3 style={{ color: '#fff' }}>⏳ Delta Lake Audit (Time Travel VERSION AS OF)</h3>
        <button onClick={handleRerun} style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '0.5rem 1rem', borderRadius: '6px', cursor: 'pointer' }}>
          🔄 Rerun Evaluation
        </button>
      </div>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1.5rem' }}>
        <label style={{ color: '#94a3b8' }}>Select Snapshot Version:</label>
        <select 
          value={version} 
          onChange={e => setVersion(Number(e.target.value))}
          style={{ padding: '0.4rem 0.8rem', background: '#1e293b', color: '#fff', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}
        >
          <option value={3}>Version #3</option>
          <option value={2}>Version #2</option>
          <option value={1}>Version #1</option>
          <option value={0}>Version #0</option>
        </select>
        <span style={{ color: '#10b981', marginLeft: 'auto' }}>
          Total records: <strong>{auditData?.total_records || 0}</strong>
        </span>
      </div>
    </div>
  );
}
