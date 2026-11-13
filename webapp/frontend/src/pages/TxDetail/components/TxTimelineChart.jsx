import React from 'react';
import 'chart.js/auto';
import { Line } from 'react-chartjs-2';

export default function TxTimelineChart({ tx, timelinePoints = [] }) {
  const sortedPoints = [...timelinePoints].sort((a, b) => (a.time || '').localeCompare(b.time || ''));

  const timelineLabels = sortedPoints.map((p, idx) => {
    if (p.time && p.time.includes(' ')) {
      return p.time.split(' ')[1] || p.time;
    }
    return `T-${sortedPoints.length - idx}`;
  });

  const timelineAmounts = sortedPoints.map((p) => p.amount);
  const pointBgColors = sortedPoints.map((p) => (p.is_current ? '#dc2626' : '#09090b'));
  const pointBorderColors = sortedPoints.map((p) => (p.is_current ? '#fee2e2' : '#ffffff'));
  const pointRadii = sortedPoints.map((p) => (p.is_current ? 7 : 3.5));
  const pointHoverRadii = sortedPoints.map((p) => (p.is_current ? 9 : 5));

  const chartData = {
    labels: timelineLabels,
    datasets: [
      {
        label: 'Transaction Amount (VND)',
        data: timelineAmounts,
        borderColor: '#09090b',
        backgroundColor: 'rgba(9, 9, 11, 0.03)',
        borderWidth: 1.75,
        fill: true,
        tension: 0.25,
        pointBackgroundColor: pointBgColors,
        pointBorderColor: pointBorderColors,
        pointBorderWidth: 1.5,
        pointRadius: pointRadii,
        pointHoverRadius: pointHoverRadii,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#09090b',
        callbacks: {
          label: (ctx) => {
            const val = ctx.parsed.y || 0;
            const isCurrent = sortedPoints[ctx.dataIndex]?.is_current;
            return `${isCurrent ? 'CURRENT TX: ' : ''}${new Intl.NumberFormat('en-US', {
              style: 'currency',
              currency: 'VND',
              maximumFractionDigits: 0,
            }).format(val)}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { color: '#f4f4f5' },
        ticks: { color: '#71717a', font: { size: 11 } },
      },
      y: {
        grid: { color: '#f4f4f5' },
        ticks: {
          color: '#71717a',
          font: { size: 11 },
          callback: (value) => {
            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
            if (value >= 1000) return `${(value / 1000).toFixed(0)}k`;
            return `${value} ₫`;
          },
        },
      },
    },
  };

  return (
    <div className="shadcn-card" style={{ padding: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h3 style={{ margin: 0, color: '#09090b', fontSize: '0.9375rem', fontWeight: 600 }}>
          Transaction Trajectory Over Time
        </h3>
        <span style={{ fontSize: '0.75rem', color: '#dc2626', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#dc2626' }}></span>
          Red marker = Current event
        </span>
      </div>
      <p style={{ fontSize: '0.75rem', color: '#71717a', margin: '0 0 0.85rem 0' }}>
        Visual inspection of spending curve for account <code style={{ color: '#09090b' }}>{tx.source_account}</code>.
      </p>
      <div style={{ height: '200px', width: '100%' }}>
        <Line data={chartData} options={chartOptions} />
      </div>
    </div>
  );
}

