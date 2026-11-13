import React from 'react';

export default function CandidateModelsTable({ modelsComparison = [] }) {
  return (
    <div className="shadcn-card" style={{ overflow: 'hidden' }}>
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e4e4e7', backgroundColor: '#ffffff' }}>
        <h4 style={{ color: '#09090b', margin: 0, fontSize: '0.9375rem', fontWeight: 600 }}>
          Model Comparison in Same Training Run (GBT vs Random Forest vs Logistic Regression)
        </h4>
        <p style={{ fontSize: '0.75rem', color: '#71717a', margin: '0.2rem 0 0 0' }}>
          Algorithms evaluated in the same run as the active model (from model_registry).
        </p>
      </div>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <table className="shadcn-table">
          <thead>
            <tr>
              <th>Model Version</th>
              <th>Algorithm</th>
              <th>Precision@200</th>
              <th>Recall@200</th>
              <th>PR-AUC</th>
              <th>ROC-AUC</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {modelsComparison.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: '#71717a', fontStyle: 'italic' }}>
                  no data available
                </td>
              </tr>
            ) : (
              modelsComparison.map((m, i) => (
                <tr key={i}>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: '#09090b' }}>
                    {m.model_version}
                  </td>
                  <td style={{ fontWeight: 500, color: '#09090b' }}>
                    {m.algorithm}
                  </td>
                  <td style={{ color: '#16a34a', fontWeight: 700 }}>
                    {m.precision_at_200 !== null && m.precision_at_200 !== undefined ? `${(m.precision_at_200 * 100).toFixed(2)}%` : '—'}
                  </td>
                  <td style={{ color: '#2563eb', fontWeight: 600 }}>
                    {m.recall_at_200 !== null && m.recall_at_200 !== undefined ? `${(m.recall_at_200 * 100).toFixed(2)}%` : '—'}
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    {m.pr_auc !== null && m.pr_auc !== undefined ? m.pr_auc.toFixed(4) : '—'}
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    {m.roc_auc !== null && m.roc_auc !== undefined ? m.roc_auc.toFixed(4) : '—'}
                  </td>
                  <td>
                    <span style={{
                      display: 'inline-block',
                      padding: '0.15rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.6875rem',
                      fontWeight: 700,
                      backgroundColor: m.is_active ? '#f0fdf4' : '#f4f4f5',
                      color: m.is_active ? '#16a34a' : '#71717a',
                      border: `1px solid ${m.is_active ? '#bbf7d0' : '#e4e4e7'}`,
                    }}>
                      {m.is_active ? 'ACTIVE' : (m.promotion_decision?.toUpperCase() || 'BENCHMARK')}
                    </span>
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

