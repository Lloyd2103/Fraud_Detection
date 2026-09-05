import React, { useState, useEffect } from 'react';
import { fetchModelPerformance } from '../services/api';

export default function ModelDashPage() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchModelPerformance().then(res => setData(res.data)).catch(console.error);
  }, []);

  if (!data) {
    return <div style={{ color: '#94a3b8', padding: '2rem' }}>Loading model performance metrics...</div>;
  }

  return (
    <div>
      <h3 style={{ color: '#fff', marginBottom: '1.25rem' }}>📊 Model Performance & Drift Tracking</h3>
      
      {/* 3 Models Comparison Table */}
      <div style={{ background: '#111827', padding: '1.5rem', borderRadius: '12px', marginBottom: '1.5rem', border: '1px solid rgba(255,255,255,0.08)' }}>
        <h4 style={{ color: '#fff', marginBottom: '1rem' }}>⚖️ Multi-Model Evaluation Comparison (GBT vs Random Forest vs Logistic Regression)</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ color: '#94a3b8', borderBottom: '1px solid rgba(255,255,255,0.1)', fontSize: '0.8rem' }}>
              <th style={{ padding: '0.6rem' }}>Algorithm</th>
              <th style={{ padding: '0.6rem' }}>Precision@200</th>
              <th style={{ padding: '0.6rem' }}>PR-AUC</th>
              <th style={{ padding: '0.6rem' }}>ROC-AUC</th>
              <th style={{ padding: '0.6rem' }}>Detected (Top 200)</th>
            </tr>
          </thead>
          <tbody>
            {(data.models_comparison || []).map((m, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.75rem', fontWeight: 600, color: '#fff' }}>{m.algorithm}</td>
                <td style={{ padding: '0.75rem', color: '#10b981', fontWeight: 700 }}>{(m.precision_at_200 * 100).toFixed(2)}%</td>
                <td style={{ padding: '0.75rem' }}>{(m.pr_auc * 100).toFixed(2)}%</td>
                <td style={{ padding: '0.75rem' }}>{(m.roc_auc * 100).toFixed(2)}%</td>
                <td style={{ padding: '0.75rem' }}>{m.fraud_detected_in_top200}/200</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
