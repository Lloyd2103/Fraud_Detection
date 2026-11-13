import React from 'react';
import 'chart.js/auto';
import { Line, Bar } from 'react-chartjs-2';

const gridColor = '#f4f4f5';
const textColor = '#71717a';

const psiValuePlugin = {
  id: 'psiValueLabels',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    chart.data.datasets.forEach((dataset, i) => {
      const meta = chart.getDatasetMeta(i);
      meta.data.forEach((bar, index) => {
        const val = dataset.data[index];
        if (val !== undefined && val !== null) {
          ctx.save();
          ctx.fillStyle = val >= 0.25 ? '#dc2626' : val >= 0.1 ? '#d97706' : '#52525b';
          ctx.font = '600 9px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(Number(val).toFixed(val >= 0.1 ? 3 : 2), bar.x, bar.y - 3);
          ctx.restore();
        }
      });
    });
  },
};

export default function ModelPerformanceCharts({
  trainingHistory = [],
  driftMonitoring = [],
  featureImportances = [],
}) {
  // 1. History Chart
  const historyLabels = trainingHistory.map((h) => h.date || h.model_version);
  const historyP200 = trainingHistory.map((h) => (h.precision_at_200 * 100).toFixed(1));
  const historyRecall = trainingHistory.map((h) => (h.recall_at_200 ? (h.recall_at_200 * 100).toFixed(1) : null));

  const historyChartData = {
    labels: historyLabels,
    datasets: [
      {
        label: 'Precision@200 (%)',
        data: historyP200,
        borderColor: '#09090b',
        backgroundColor: 'rgba(9, 9, 11, 0.04)',
        borderWidth: 2,
        fill: false,
        tension: 0.25,
        pointBackgroundColor: '#09090b',
        pointRadius: 4,
        pointHoverRadius: 6,
      },
      {
        label: 'Recall@200 (%)',
        data: historyRecall,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.04)',
        borderWidth: 2,
        fill: false,
        tension: 0.25,
        pointBackgroundColor: '#2563eb',
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const historyChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: { font: { size: 12 }, boxWidth: 12 },
      },
      tooltip: { backgroundColor: '#09090b', padding: 8 },
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 11 } } },
      y: { min: 20, max: 100, grid: { color: gridColor }, ticks: { color: textColor, font: { size: 11 }, callback: (v) => `${v}%` } },
    },
  };

  // 2. Drift PSI
  const latestDriftMap = {};
  driftMonitoring.forEach((item) => {
    const existing = latestDriftMap[item.feature_name];
    if (!existing || item.date > existing.date) {
      latestDriftMap[item.feature_name] = item;
    }
  });
  const processedDriftData = Object.values(latestDriftMap).sort((a, b) => b.psi - a.psi);

  const distinctDriftDates = Array.from(new Set(processedDriftData.map((d) => d.date))).sort();
  const formattedDriftDates = distinctDriftDates.map((d) => {
    const parts = d.split('-');
    return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : d;
  });
  const driftDateFootnote = formattedDriftDates.length === 1
    ? `Drift baseline measured on ${formattedDriftDates[0]}`
    : (formattedDriftDates.length > 1
      ? `Drift baseline measured on ${formattedDriftDates.slice(0, -1).join(', ')} and ${formattedDriftDates[formattedDriftDates.length - 1]}`
      : '');

  const driftLabels = processedDriftData.map((d) => d.feature_name);
  const driftValues = processedDriftData.map((d) => d.psi);
  const driftColors = processedDriftData.map((d) => (d.psi >= 0.25 ? '#ef4444' : d.psi >= 0.1 ? '#f59e0b' : '#09090b'));
  const maxDriftVal = driftValues.length > 0 ? Math.max(...driftValues) : 0.3;
  const psiAxisMax = Math.max(0.35, Math.ceil((maxDriftVal + 0.05) * 10) / 10);

  const driftChartData = {
    labels: driftLabels,
    datasets: [
      {
        label: 'Population Stability Index (PSI)',
        data: driftValues,
        backgroundColor: driftColors,
        borderRadius: 4,
        borderWidth: 0,
      },
    ],
  };

  const driftChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#09090b',
        padding: 8,
        callbacks: {
          label: (context) => {
            const item = processedDriftData[context.dataIndex];
            const dParts = item?.date ? item.date.split('-') : [];
            const dStr = dParts.length === 3 ? `${dParts[2]}/${dParts[1]}/${dParts[0]}` : (item?.date || '');
            return [
              `PSI: ${Number(context.parsed.y).toFixed(4)}`,
              dStr ? `Measured on: ${dStr}` : '',
            ].filter(Boolean);
          },
        },
      },
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 11 } } },
      y: {
        min: 0,
        max: psiAxisMax,
        grid: { color: gridColor },
        ticks: {
          color: textColor,
          font: { size: 11 },
          callback: (v) => Number(v).toFixed(2),
        },
      },
    },
  };

  // 3. Feature Importance
  const featLabels = featureImportances.map((f) => f.name || f.feature);
  const featValues = featureImportances.map((f) => (f.importance * 100).toFixed(1));
  const featChartData = {
    labels: featLabels,
    datasets: [
      {
        label: 'Importance (%)',
        data: featValues,
        backgroundColor: '#18181b',
        borderRadius: 4,
      },
    ],
  };

  const featChartOptions = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#09090b', padding: 8 },
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 11 }, callback: (v) => `${v}%` } },
      y: { grid: { color: gridColor }, ticks: { color: '#09090b', font: { size: 11, weight: 500 } } },
    },
  };

  return (
    <>
      {/* Row 1: Training Progression Chart */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <h4 style={{ margin: 0, color: '#09090b', fontSize: '0.9375rem', fontWeight: 600 }}>
          Precision@200 &amp; Recall@200 Across Training Runs
        </h4>
        <p style={{ fontSize: '0.75rem', color: '#71717a', margin: '0.2rem 0 0.85rem 0' }}>
          Model evolution history across recurring training runs (source: model_registry, source='recorded').
        </p>
        <div style={{ height: '240px', width: '100%' }}>
          <Line data={historyChartData} options={historyChartOptions} />
        </div>
      </div>

      {/* Row 2 Charts: Drift PSI & Feature Importances */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1rem' }}>
        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <h4 style={{ margin: 0, color: '#09090b', fontSize: '0.9375rem', fontWeight: 600 }}>
            Concept Drift Tracking (PSI - gold.drift_monitoring)
          </h4>
          <p style={{ fontSize: '0.75rem', color: '#71717a', margin: '0.2rem 0 0.85rem 0' }}>
            Thresholds: &lt;0.1 (Stable), 0.1-0.25 (Warning), &gt;0.25 (Trigger Retraining).
          </p>
          <div style={{ height: '220px', width: '100%' }}>
            {processedDriftData.length === 0 ? (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#71717a', fontSize: '0.8125rem' }}>
                Loading drift data...
              </div>
            ) : (
              <Bar data={driftChartData} options={driftChartOptions} plugins={[psiValuePlugin]} />
            )}
          </div>
          {driftDateFootnote && (
            <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.65rem', marginBottom: 0, textAlign: 'center', fontStyle: 'italic' }}>
              {driftDateFootnote}
            </p>
          )}
        </div>

        <div className="shadcn-card" style={{ padding: '1.25rem' }}>
          <h4 style={{ margin: 0, color: '#09090b', fontSize: '0.9375rem', fontWeight: 600 }}>
            Feature Importance (GBT Feature Importances)
          </h4>
          <p style={{ fontSize: '0.75rem', color: '#71717a', margin: '0.2rem 0 0.85rem 0' }}>
            Top contributing features explaining fraud risk score decisions.
          </p>
          <div style={{ height: '220px', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {featureImportances.length === 0 ? (
              <div style={{ color: '#71717a', fontSize: '0.8125rem', fontStyle: 'italic', textAlign: 'center', padding: '1.5rem' }}>
                not recorded in this training run
              </div>
            ) : (
              <Bar data={featChartData} options={featChartOptions} />
            )}
          </div>
        </div>
      </div>
    </>
  );
}

