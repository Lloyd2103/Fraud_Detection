import React, { useState, useEffect } from 'react';
import { useModelGovernance } from '../../hooks/useModelGovernance';
import ModelPerformanceCharts from './components/ModelPerformanceCharts';
import CandidateModelsTable from './components/CandidateModelsTable';

// Acceptance targets from the assignment (Precision@200 >= 0.35, PR-AUC >= 0.60).
const TARGET_P200 = 0.35;
const TARGET_PRAUC = 0.60;

const BADGE_OK = { color: '#16a34a', backgroundColor: '#f0fdf4', border: '1px solid #dcfce7' };
const BADGE_BELOW = { color: '#c2410c', backgroundColor: '#fff7ed', border: '1px solid #fed7aa' };
const BADGE_BASE = { fontSize: '0.6875rem', padding: '0.1rem 0.4rem', borderRadius: '4px', fontWeight: 700, whiteSpace: 'nowrap' };

function TargetBadge({ value, target }) {
  if (value === null || value === undefined) return null;
  const met = Number(value) >= target;
  return (
    <span style={{ ...BADGE_BASE, ...(met ? BADGE_OK : BADGE_BELOW) }}>
      {met ? `Meets target (\u2265${target})` : `Below target (\u2265${target})`}
    </span>
  );
}

export default function ModelDashPage() {
  const { getPerformance } = useModelGovernance();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    getPerformance()
      .then((res) => {
        setData(res);
      })
      .catch((err) => {
        console.error(err);
        const detail = err?.response?.data?.detail;
        setLoadError(typeof detail === 'string' ? detail : (err?.message || 'Failed to load model metrics'));
      })
      .finally(() => setLoading(false));
  }, [getPerformance]);

  if (!loading && (loadError || !data || data.available === false)) {
    return (
      <div className="shadcn-card" style={{ padding: '2.5rem', textAlign: 'center', color: '#71717a', fontSize: '0.875rem' }}>
        {loadError || data?.message || 'No model metrics are available.'}
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="shadcn-card" style={{ padding: '3.5rem', textAlign: 'center', color: '#71717a', fontSize: '0.875rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: '28px', height: '28px', border: '3px solid #e4e4e7', borderTopColor: '#09090b', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          <span>Loading model metrics and tracking drift from Lakehouse...</span>
        </div>
      </div>
    );
  }

  const rawHistory = data.training_history || [];
  const trainingHistory = rawHistory.filter((h) =>
    (h.algorithm && h.algorithm.includes('GBT')) || (h.model_version && h.model_version.startsWith('GBT')),
  );

  const p200Pct = data.precision_at_200 !== null && data.precision_at_200 !== undefined
    ? (data.precision_at_200 * 100).toFixed(1) + '%'
    : '—';
  const maxP200Pct = data.theoretical_max_p200
    ? (data.theoretical_max_p200 * 100).toFixed(1) + '%'
    : null;
  const recallPct = data.recall_at_200 !== null && data.recall_at_200 !== undefined
    ? (data.recall_at_200 * 100).toFixed(1) + '%'
    : null;
  const hasTp = data.fraud_detected_in_top200 !== null && data.fraud_detected_in_top200 !== undefined;
  const tpStr = hasTp
    ? (data.total_eval_top200 ? `${data.fraud_detected_in_top200} / ${data.total_eval_top200}` : `${data.fraud_detected_in_top200}`)
    : null;

  const missingRecall = trainingHistory.filter((h) => h.recall_at_200 === null || h.recall_at_200 === undefined || h.recall_at_200 === 0).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* 4 Metric Cards - Active Serving Model */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div className="shadcn-card" style={{ padding: '1.25rem', minWidth: 0, overflow: 'hidden' }}>
          <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Active Serving Model
          </div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#09090b', marginTop: '0.35rem', letterSpacing: '-0.02em', fontFamily: "'JetBrains Mono', monospace" }}>
            {data.current_model || '—'}
          </div>
          <div
            style={{
              fontSize: '0.72rem',
              color: '#71717a',
              marginTop: '0.25rem',
              fontFamily: "'JetBrains Mono', monospace",
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={data.algorithm || ''}
          >
            {data.algorithm || ''}
          </div>
          {data.status && (
            <div style={{ fontSize: '0.72rem', color: '#71717a', marginTop: '0.25rem' }}>Registry status: {data.status}</div>
          )}
        </div>

        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Precision@200 (Pooled)
            </span>
            <TargetBadge value={data.precision_at_200} target={TARGET_P200} />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#09090b', marginTop: '0.35rem', letterSpacing: '-0.02em' }}>
            {p200Pct}
            {maxP200Pct && (
              <span style={{ fontSize: '0.8rem', color: '#71717a', fontWeight: 500, marginLeft: '0.4rem' }}>
                (max: {maxP200Pct})
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.2rem' }}>
            {recallPct && `Recall: ${recallPct}`}{recallPct && tpStr ? ' • ' : ''}{tpStr ? `${tpStr} TP` : ''}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.2rem' }}>
            Target Precision@200 &ge; {TARGET_P200}
          </div>
        </div>

        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              PR-AUC Metric
            </span>
            <TargetBadge value={data.pr_auc} target={TARGET_PRAUC} />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#09090b', marginTop: '0.35rem', letterSpacing: '-0.02em' }}>
            {data.pr_auc !== null && data.pr_auc !== undefined ? data.pr_auc.toFixed(3) : '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.2rem' }}>
            Target PR-AUC &ge; {TARGET_PRAUC}
          </div>
        </div>

        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            ROC-AUC Metric
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#09090b', marginTop: '0.35rem', letterSpacing: '-0.02em' }}>
            {data.roc_auc !== null && data.roc_auc !== undefined ? data.roc_auc.toFixed(3) : '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.2rem' }}>
            Area under the ROC curve
          </div>
        </div>
      </div>

      {missingRecall > 0 && (
        <div style={{ fontSize: '0.75rem', color: '#92400e', backgroundColor: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, padding: '0.5rem 0.75rem' }}>
          Recall@200 is not recorded in model_registry for {missingRecall} of {trainingHistory.length} training runs, so the Recall chart shows fewer points than the Precision chart.
        </div>
      )}

      <ModelPerformanceCharts
        trainingHistory={trainingHistory}
        driftMonitoring={data.drift_monitoring || []}
        featureImportances={data.feature_importances || []}
      />

      <CandidateModelsTable modelsComparison={data.models_comparison || []} />
    </div>
  );
}

