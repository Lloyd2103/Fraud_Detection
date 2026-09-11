import React, { useState, useEffect } from 'react';
import { fetchAlerts, fetchAlertSummary, fetchLatencyStats } from '../services/api';
import AlertTable from '../components/AlertTable';

export default function AlertQueuePage({ onSelectTx }) {
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState({});
  const [latency, setLatency] = useState({});
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [alertsRes, summaryRes, latencyRes] = await Promise.all([
        fetchAlerts('all', 50),
        fetchAlertSummary(),
        fetchLatencyStats().catch(() => ({ data: {} }))
      ]);
      setAlerts(alertsRes.data || []);
      setSummary(summaryRes.data || {});
      setLatency(latencyRes.data || {});
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

  const p95Str = latency.p95_latency_ms ? `${(latency.p95_latency_ms / 1000).toFixed(2)} s` : '0.00 s';

  return (
    <div>
      {/* KPI Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '12px', borderLeft: '4px solid #ef4444' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>CHỜ THẨM ĐỊNH (PENDING)</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#ef4444' }}>{summary.pending_count || summary.so_canh_bao_chua_xu_ly || 0}</div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Chỉ tiêu xử lý: 200 cảnh báo/ngày</div>
        </div>
        <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '12px', borderLeft: '4px solid #f59e0b' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>RỦI RO CAO (&gt;80%)</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#f59e0b' }}>{summary.critical_count || summary.so_canh_bao_nghiem_trong || 0}</div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Yêu cầu xử lý ưu tiên</div>
        </div>
        <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '12px', borderLeft: '4px solid #10b981' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>ĐÃ THẨM ĐỊNH (INSPECTED)</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#10b981' }}>{summary.processed_count || summary.so_canh_bao_da_xu_ly || 0}</div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Ghi nhận nhãn phản hồi tuần</div>
        </div>
        <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '12px', borderLeft: '4px solid #06b6d4' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>ĐỘ TRỄ P95 THỰC TẾ</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#06b6d4' }}>{p95Str}</div>
          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Đặc tả SLA &lt; 5s (DeTai2.pdf)</div>
        </div>
      </div>

      {/* Table Card */}
      <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#fff' }}>
            🚨 Hàng Đợi Cảnh Báo Gian Lận Theo Thời Gian Thực (DeTai2.pdf Mục 2.8)
          </h3>
          <button onClick={loadData} style={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '0.4rem 0.8rem', borderRadius: '6px', cursor: 'pointer' }}>
            🔄 Làm mới
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>Đang tải hàng đợi cảnh báo...</div>
        ) : (
          <AlertTable alerts={alerts} onSelectTx={onSelectTx} />
        )}
      </div>
    </div>
  );
}