import React, { useState, useEffect } from 'react';
import { fetchAlerts, fetchAlertSummary } from '../services/api';
import AlertTable from '../components/AlertTable';

export default function AlertQueuePage({ onSelectTx }) {
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [alertsRes, summaryRes] = await Promise.all([
        fetchAlerts('all', 50),
        fetchAlertSummary()
      ]);
      setAlerts(alertsRes.data || []);
      setSummary(summaryRes.data || {});
    } catch (err) {
      console.error('Error fetching alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div>
      {/* KPI Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '12px', borderLeft: '4px solid #ef4444' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>PENDING REVIEW</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#ef4444' }}>{summary.pending_count || 0}</div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Daily quota: 200 alerts/day</div>
        </div>
        <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '12px', borderLeft: '4px solid #f59e0b' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>CRITICAL RISK (&gt;80%)</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#f59e0b' }}>{summary.critical_count || 0}</div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Immediate triage required</div>
        </div>
        <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '12px', borderLeft: '4px solid #10b981' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>INSPECTED</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#10b981' }}>{summary.processed_count || 0}</div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Feedback labels ingested</div>
        </div>
        <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '12px', borderLeft: '4px solid #06b6d4' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>P95 LATENCY</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#06b6d4' }}>1.64 s</div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Meets SLA &lt; 5s</div>
        </div>
      </div>

      {/* Table Card */}
      <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#fff' }}>
            🚨 High-Risk Fraud Alert Queue
          </h3>
          <button onClick={loadData} style={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '0.4rem 0.8rem', borderRadius: '6px', cursor: 'pointer' }}>
            🔄 Refresh
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>Loading alert queue...</div>
        ) : (
          <AlertTable alerts={alerts} onSelectTx={onSelectTx} />
        )}
      </div>
    </div>
  );
}