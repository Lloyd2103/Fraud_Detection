import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useAlertsWs } from '../../hooks/useAlertsWs';
import { useAlerts } from '../../hooks/useAlerts';
import { useLatency } from '../../hooks/useLatency';
import AlertTable from '../../components/AlertTable';
import AlertSummaryCards from './components/AlertSummaryCards';
import AlertFilterBar from './components/AlertFilterBar';
import TablePagination from '../../components/TablePagination';
import { RotateCw } from 'lucide-react';

export default function AlertQueuePage({ onSelectTx, onSwitchTab }) {
  const { user } = useAuth();
  const { isLiveWs, summary: wsSummary, lastEvent, alertsList, sendWs } = useAlertsWs();
  const { getAlerts } = useAlerts();
  const { getLatencyStats } = useLatency();

  const [alerts, setAlerts] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(true);
  const [latency, setLatency] = useState(null);

  // Filter & Pagination States
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(50);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChannel, setSelectedChannel] = useState('ALL');
  const [selectedAmountRange, setSelectedAmountRange] = useState('ALL');
  const [sortCriteria, setSortCriteria] = useState([{ field: 'risk_score', order: 'desc' }]);
  const [lastUpdatedTime, setLastUpdatedTime] = useState(null);

  // Poll latency SLA (only for analyst/admin)
  useEffect(() => {
    if (user?.role === 'auditor') return;
    let isMounted = true;
    const fetchLatency = async () => {
      try {
        const res = await getLatencyStats();
        if (isMounted) setLatency(res);
      } catch (_) {}
    };
    fetchLatency();
    const interval = setInterval(fetchLatency, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [user?.role, getLatencyStats]);

  const fetchAlertsData = useCallback(async () => {
    setLoading(true);
    const sortBy = sortCriteria.map((s) => `${s.field}:${s.order}`).join(',');
    const options = {
      page,
      limit,
      search: searchQuery.trim(),
      channel: selectedChannel,
      amountRange: selectedAmountRange,
      sortBy,
      order: sortCriteria[0]?.order || 'desc',
    };

    if (isLiveWs) {
      sendWs({
        action: 'FETCH_ALERTS',
        status: 'PENDING',
        page,
        limit,
        search: searchQuery.trim(),
        channel: selectedChannel,
        amountRange: selectedAmountRange,
        sortBy,
      });
    }

    try {
      const data = await getAlerts(options);
      setAlerts(data.data || []);
      setTotalRecords(data.total || 0);
      setLastUpdatedTime(new Date());
    } catch (err) {
      console.error('Failed to load pending alerts:', err);
    } finally {
      setLoading(false);
    }
  }, [page, limit, searchQuery, selectedChannel, selectedAmountRange, sortCriteria, isLiveWs, sendWs, getAlerts]);

  useEffect(() => {
    fetchAlertsData();
  }, [fetchAlertsData]);

  // Sync WebSocket updates
  useEffect(() => {
    if (!lastEvent) return;
    const { type, alerts: wsAlerts, total } = lastEvent;
    if (type === 'ALERT_LIST' || type === 'HEARTBEAT') {
      if (Array.isArray(wsAlerts)) {
        setAlerts(wsAlerts);
        if (total !== undefined) setTotalRecords(total);
        setLastUpdatedTime(new Date());
      }
    }
  }, [lastEvent]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(totalRecords / limit));
  const hasFilters = Boolean(
    searchQuery.trim() ||
    selectedChannel !== 'ALL' ||
    selectedAmountRange !== 'ALL' ||
    (sortCriteria.length === 1 && (sortCriteria[0].field !== 'risk_score' || sortCriteria[0].order !== 'desc'))
  );

  const resetFilters = () => {
    setSearchQuery('');
    setSelectedChannel('ALL');
    setSelectedAmountRange('ALL');
    setSortCriteria([{ field: 'risk_score', order: 'desc' }]);
    setPage(1);
  };

  const resetSort = () => {
    setSortCriteria([{ field: 'risk_score', order: 'desc' }]);
    setPage(1);
  };

  const handleSortColumn = useCallback((field) => {
    setSortCriteria((prev) => {
      const idx = prev.findIndex((s) => s.field === field);
      if (idx === -1) {
        return [{ field, order: 'desc' }, ...prev.slice(0, 2)];
      } else if (idx === 0) {
        const newOrder = prev[0].order === 'desc' ? 'asc' : 'desc';
        return [{ field, order: newOrder }, ...prev.slice(1)];
      } else {
        const target = prev[idx];
        const others = prev.filter((_, i) => i !== idx);
        return [target, ...others];
      }
    });
    setPage(1);
  }, []);

  const pendingCount = wsSummary?.pending_count ?? totalRecords;
  const criticalCount = wsSummary?.critical_count ?? 0;
  const processedCount = wsSummary?.processed_count ?? 0;
  // Backend returns p95_latency_ms (milliseconds); show seconds only when there are measurements.
  const p95Ms = latency?.p95_latency_ms;
  const hasLatencyData = p95Ms !== undefined && p95Ms !== null && Number(latency?.total_measured_alerts ?? 0) > 0;
  const p95Str = hasLatencyData ? `${(Number(p95Ms) / 1000).toFixed(2)}s` : null;

  return (
    <div>
      {/* 1. Summary Cards */}
      <AlertSummaryCards
        loading={loading}
        summary={wsSummary}
        pendingCount={pendingCount}
        criticalCount={criticalCount}
        processedCount={processedCount}
        p95Str={p95Str}
        latency={latency}
        userRole={user?.role}
      />

      {/* 2. Main Alert Stream Card */}
      <div className="shadcn-card" style={{ overflow: 'hidden' }}>
        {/* Header & Status Toggle */}
        <div style={{
          padding: '1rem 1.25rem',
          borderBottom: '1px solid #e4e4e7',
          backgroundColor: '#ffffff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h3 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 600, color: '#09090b' }}>
                Pending Fraud Alerts Stream
              </h3>
              {isLiveWs && (
                <span style={{
                  fontSize: '0.6875rem',
                  fontWeight: 600,
                  color: '#16a34a',
                  backgroundColor: '#f0fdf4',
                  border: '1px solid #dcfce7',
                  padding: '0.1rem 0.45rem',
                  borderRadius: '4px',
                }}>
                  • WebSocket Live
                </span>
              )}
            </div>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: '#71717a' }}>
              High-risk transactions detected by Spark Streaming &amp; GBT Lakehouse pipeline
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {lastUpdatedTime && (
              <span style={{ fontSize: '0.75rem', color: '#71717a', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <RotateCw size={11} /> Updated at {lastUpdatedTime.toLocaleTimeString('en-US', { hour12: false })}
              </span>
            )}
            <button
              onClick={fetchAlertsData}
              className="btn-shadcn btn-secondary"
              style={{ height: '1.875rem', padding: '0 0.5rem', fontSize: '0.75rem' }}
            >
              Refresh
            </button>

            {/* Toggle to Inspected Verdicts */}
            <div style={{ display: 'inline-flex', padding: '2px', backgroundColor: '#f4f4f5', borderRadius: '6px', border: '1px solid #e4e4e7' }}>
              <button
                type="button"
                style={{
                  padding: '0.25rem 0.65rem',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  borderRadius: '4px',
                  backgroundColor: '#ffffff',
                  color: '#09090b',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                <span>Pending Queue</span>
                <span style={{ fontSize: '0.6875rem', padding: '0.05rem 0.35rem', borderRadius: '9999px', backgroundColor: '#dc2626', color: '#ffffff', fontWeight: 600 }}>
                  {pendingCount}
                </span>
              </button>
              <button
                type="button"
                onClick={() => onSwitchTab ? onSwitchTab('inspected') : (window.location.hash = '#inspected')}
                style={{
                  padding: '0.25rem 0.65rem',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  borderRadius: '4px',
                  backgroundColor: 'transparent',
                  color: '#71717a',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                <span>Inspected Verdicts</span>
                <span style={{ fontSize: '0.6875rem', padding: '0.05rem 0.35rem', borderRadius: '9999px', backgroundColor: '#e4e4e7', color: '#52525b', fontWeight: 600 }}>
                  {processedCount}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Filter Controls */}
        <AlertFilterBar
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          selectedChannel={selectedChannel}
          setSelectedChannel={setSelectedChannel}
          selectedAmountRange={selectedAmountRange}
          setSelectedAmountRange={setSelectedAmountRange}
          sortCriteria={sortCriteria}
          setSortCriteria={setSortCriteria}
          onResetSort={resetSort}
        />

        {/* Table Content */}
        <div style={{ position: 'relative' }}>
          {loading && (
            <div style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: 'rgba(255,255,255,0.7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
            }}>
              <div style={{ width: '24px', height: '24px', border: '2px solid #e4e4e7', borderTopColor: '#09090b', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            </div>
          )}
          <AlertTable
            alerts={alerts}
            onSelectTx={onSelectTx}
            hasFilters={hasFilters}
            onResetFilters={resetFilters}
            isInspectedView={false}
            sortCriteria={sortCriteria}
            onSort={handleSortColumn}
          />
        </div>

        {/* Pagination Bar */}
        <TablePagination
          page={page}
          setPage={setPage}
          limit={limit}
          setLimit={setLimit}
          totalRecords={totalRecords}
          unit="alerts"
        />
      </div>
    </div>
  );
}
