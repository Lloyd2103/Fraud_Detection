import React from 'react';
import 'chart.js/auto';
import { Bar } from 'react-chartjs-2';

export default function VerdictsBarChart({
  period,
  verdictStats,
  activeRangeLabel,
  userRole,
}) {
  const isAdmin = userRole === 'admin';

  if (period === 'day') {
    const hourlyData = verdictStats?.hourly || [];
    return (
      <div className="shadcn-card" style={{ padding: '1.25rem', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h4 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 600, color: '#09090b' }}>
              Decisions by Hour ({activeRangeLabel})
            </h4>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: '#71717a' }}>
              {isAdmin ? 'Comparison of your decisions vs team by hour (0:00 - 23:00 VN)' : 'Your decisions by hour (0:00 - 23:00 VN)'}
            </p>
          </div>
        </div>
        <div style={{ height: '220px', position: 'relative' }}>
          <Bar
            data={{
              labels: hourlyData.map((h) => `${h.hour}h`),
              datasets: [
                {
                  label: 'Mine',
                  data: hourlyData.map((h) => h.mine),
                  backgroundColor: '#2563eb',
                  borderRadius: 4,
                },
                ...(isAdmin
                  ? [
                      {
                        label: 'Team',
                        data: hourlyData.map((h) => h.team),
                        backgroundColor: '#93c5fd',
                        borderRadius: 4,
                      },
                    ]
                  : []),
              ],
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  display: isAdmin,
                  position: 'top',
                  labels: { boxWidth: 12, font: { size: 11 } },
                },
                tooltip: {
                  callbacks: {
                    title: (items) => {
                      const idx = items[0]?.dataIndex;
                      return `Hour ${idx}:00 - ${idx}:59`;
                    },
                  },
                },
              },
              scales: {
                x: {
                  grid: { display: false },
                  ticks: { font: { size: 10 } },
                },
                y: {
                  beginAtZero: true,
                  ticks: { precision: 0, font: { size: 11 } },
                  grid: { color: '#f4f4f5' },
                },
              },
            }}
          />
        </div>
      </div>
    );
  }

  // Month mode
  const dailyData = verdictStats?.daily || [];
  return (
    <div className="shadcn-card" style={{ padding: '1.25rem', marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 600, color: '#09090b' }}>
            Decisions by Day of Month ({activeRangeLabel})
          </h4>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: '#71717a' }}>
            {isAdmin ? 'Comparison of your decisions vs team by day' : 'Your decisions by day'}
          </p>
        </div>
      </div>
      <div style={{ height: '220px', position: 'relative' }}>
        <Bar
          data={{
            labels: dailyData.map((d) => d.date.split('-')[2]),
            datasets: [
              {
                label: 'Mine',
                data: dailyData.map((d) => d.mine),
                backgroundColor: '#2563eb',
                borderRadius: 4,
              },
              ...(isAdmin
                ? [
                    {
                      label: 'Team',
                      data: dailyData.map((d) => d.team),
                      backgroundColor: '#93c5fd',
                      borderRadius: 4,
                    },
                  ]
                : []),
            ],
          }}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: isAdmin,
                position: 'top',
                labels: { boxWidth: 12, font: { size: 11 } },
              },
              tooltip: {
                callbacks: {
                  title: (items) => {
                    const idx = items[0]?.dataIndex;
                    const item = dailyData[idx];
                    return item ? `Date: ${item.date}` : '';
                  },
                },
              },
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { font: { size: 11 } },
              },
              y: {
                beginAtZero: true,
                ticks: { precision: 0, font: { size: 11 } },
                grid: { color: '#f4f4f5' },
              },
            },
          }}
        />
      </div>
    </div>
  );
}

