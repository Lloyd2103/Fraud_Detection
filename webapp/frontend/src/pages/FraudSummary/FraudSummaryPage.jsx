import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useFraudSummary } from '../../hooks/useFraudSummary';
import { formatVietnamTime } from '../../utils/formatters';
import {
  BarChart2, TrendingUp, AlertTriangle, DollarSign,
  RefreshCw, Layers, CheckCircle2, Activity,
} from 'lucide-react';
import FraudMatrixTable from './components/FraudMatrixTable';
import { fmt, fmtAmount, fmtPct } from './fraudFormat';

const RISK_COLOR = (rate) => {
  if (rate >= 15) return { color: '#dc2626', bg: '#fef2f2', border: '#fecaca' };
  if (rate >= 8) return { color: '#d97706', bg: '#fffbeb', border: '#fde68a' };
  if (rate >= 3) return { color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' };
  return { color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' };
};

const BAR_COLOR = (rate) => {
  if (rate >= 15) return '#ef4444';
  if (rate >= 8) return '#f59e0b';
  if (rate >= 3) return '#3b82f6';
  return '#22c55e';
};

const CHANNEL_ICON = { ONLINE: '\u{1F310}', ATM: '\u{1F3E7}', POS: '\u{1F4B3}', APP: '\u{1F4F1}' };
const TYPE_ICON = { TRANSFER: '->', CASH_OUT: '$', PAYMENT: 'P', CASH_IN: '+', DEBIT: 'D' };

export default function FraudSummaryPage() {
  const { user } = useAuth();
  const { getSummary, recalculate } = useFraudSummary();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [activeView, setActiveView] = useState('channel');
  const [recalcLoading, setRecalcLoading] = useState(false);
  const [recalcMsg, setRecalcMsg] = useState(null);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const json = await getSummary();
      if (json && json.status === 'success') {
        setData(json);
        setLastRefresh(new Date());
      }
    } catch (err) {
      console.error('FraudSummary error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [getSummary]);

  useEffect(() => {
    loadData();
    const t = setInterval(() => loadData(true), 30000);
    return () => clearInterval(t);
  }, [loadData]);

  const handleRecalculate = async () => {
    setRecalcLoading(true);
    setRecalcMsg(null);
    try {
      const json = await recalculate();
      setRecalcMsg({ type: json.status, text: json.message });
      if (json.status === 'success') loadData(true);
    } catch {
      setRecalcMsg({ type: 'error', text: 'Recompute failed.' });
    } finally {
      setRecalcLoading(false);
      setTimeout(() => setRecalcMsg(null), 5000);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ width: 40, height: 40, border: '3px solid #e4e4e7', borderTopColor: '#09090b', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <span style={{ fontSize: '0.875rem', color: '#71717a' }}>Loading fraud summary...</span>
      </div>
    );
  }

  if (!data) return <div style={{ padding: '2rem', color: '#71717a' }}>No data.</div>;

  const overall = data.overall || {};
  const byChannel = data.by_channel || {};
  const byTransType = data.by_trans_type || {};
  const rawRows = data.data || [];

  const activeBreakdown = activeView === 'channel' ? byChannel : byTransType;
  const maxRate = Math.max(...Object.values(activeBreakdown).map((v) => v.fraud_rate_percentage || 0), 0.01);

  return (
    <div style={{ fontFamily: 'Inter, Outfit, sans-serif' }}>
      {/* Top bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <BarChart2 size={22} style={{ color: '#09090b' }} />
            <h1 style={{ margin: 0, fontSize: '1.375rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.02em' }}>
              Fraud Summary Analytics
            </h1>
          </div>
          <p style={{ margin: 0, fontSize: '0.8125rem', color: '#71717a' }}>
            Flagged transactions aggregated by channel and transaction type, from the CockroachDB serving database ({data.count} groups)
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {lastRefresh && (
            <span style={{ fontSize: '0.75rem', color: '#a1a1aa' }}>
              Updated {formatVietnamTime(lastRefresh)}
            </span>
          )}
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="btn-shadcn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', height: '2rem', padding: '0 0.75rem', fontSize: '0.8125rem' }}
          >
            <RefreshCw size={13} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            <span>Refresh</span>
          </button>
          {user?.role === 'admin' && (
            <button
              onClick={handleRecalculate}
              disabled={recalcLoading}
              title="Re-aggregates the CockroachDB fraud_summary table from the transactions table. Does not touch the Delta Gold layer."
              className="btn-shadcn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', height: '2rem', padding: '0 0.75rem', fontSize: '0.8125rem' }}
            >
              <Activity size={13} style={{ animation: recalcLoading ? 'spin 1s linear infinite' : 'none' }} />
              <span>{recalcLoading ? 'Recomputing...' : 'Recompute summary table'}</span>
            </button>
          )}
        </div>
      </div>

      {recalcMsg && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.75rem 1rem',
          borderRadius: 6,
          fontSize: '0.8125rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          backgroundColor: recalcMsg.type === 'success' ? '#f0fdf4' : '#fef2f2',
          border: `1px solid ${recalcMsg.type === 'success' ? '#bbf7d0' : '#fecaca'}`,
          color: recalcMsg.type === 'success' ? '#15803d' : '#b91c1c',
        }}>
          {recalcMsg.type === 'success' ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}
          <span>{recalcMsg.text}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Flagged Transactions', val: fmt(overall.flagged_transactions ?? overall.total_transactions), sub: 'Rows flagged by the model in the serving DB', icon: Layers, color: '#09090b' },
          { label: 'Fraud Cases (verdict, else model label)', val: fmt(overall.total_fraud_cases), sub: `${fmtPct(overall.overall_fraud_rate_percentage ?? overall.fraud_rate_percentage)} of flagged transactions`, icon: AlertTriangle, color: '#dc2626' },
          { label: 'Flagged Amount', val: fmtAmount(overall.total_volume), sub: 'Sum of flagged transaction amounts', icon: DollarSign, color: '#09090b' },
        ].map((kpi, i) => (
          <div key={i} className="shadcn-card" style={{ padding: '1.1rem 1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{kpi.label}</span>
              <kpi.icon size={15} style={{ color: kpi.color }} />
            </div>
            <div style={{ fontSize: '1.45rem', fontWeight: 700, color: kpi.color, letterSpacing: '-0.02em', lineHeight: 1.2 }}>{kpi.val}</div>
            <div style={{ fontSize: '0.72rem', color: '#a1a1aa', marginTop: '0.25rem' }}>{kpi.sub}</div>
          </div>
        ))}
      </div>

      {data.scope_note && (
        <p style={{ margin: '-0.75rem 0 1.5rem', fontSize: '0.75rem', color: '#71717a', lineHeight: 1.5 }}>
          Note: {data.scope_note}
        </p>
      )}

      {/* Breakdown View Toggle & Bars */}
      <div className="shadcn-card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 600, color: '#09090b' }}>
              Fraud Share Comparison
            </h2>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.75rem', color: '#71717a' }}>
              Share of flagged transactions counted as fraud, per dimension (not a rate over all transactions)
            </p>
          </div>
          <div style={{ display: 'flex', border: '1px solid #e4e4e7', borderRadius: 6, overflow: 'hidden' }}>
            <button
              onClick={() => setActiveView('channel')}
              style={{
                padding: '0.35rem 0.85rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                backgroundColor: activeView === 'channel' ? '#09090b' : '#ffffff',
                color: activeView === 'channel' ? '#ffffff' : '#71717a',
              }}
            >
              By Channel
            </button>
            <button
              onClick={() => setActiveView('type')}
              style={{
                padding: '0.35rem 0.85rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                backgroundColor: activeView === 'type' ? '#09090b' : '#ffffff',
                color: activeView === 'type' ? '#ffffff' : '#71717a',
              }}
            >
              By Transaction Type
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {Object.entries(activeBreakdown).map(([k, v]) => {
            const r = v.fraud_rate_percentage || 0;
            const barPct = maxRate > 0 ? (r / maxRate) * 100 : 0;
            const rc = RISK_COLOR(r);
            const icon = activeView === 'channel' ? CHANNEL_ICON[k] || '' : TYPE_ICON[k] || '';

            return (
              <div key={k}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem', fontSize: '0.8125rem' }}>
                  <span style={{ fontWeight: 600, color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span>{icon}</span>
                    <span>{k}</span>
                    <span style={{ fontSize: '0.75rem', color: '#a1a1aa', fontWeight: 400 }}>({fmt(v.total_transactions)} flagged)</span>
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#71717a' }}>{fmt(v.total_fraud_cases)} fraud &bull; Amount: {fmtAmount(v.total_volume)}</span>
                    <span style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      padding: '0.1rem 0.45rem',
                      borderRadius: 4,
                      color: rc.color,
                      backgroundColor: rc.bg,
                      border: `1px solid ${rc.border}`,
                    }}>
                      {fmtPct(r)}
                    </span>
                  </div>
                </div>
                <div style={{ height: 6, width: '100%', backgroundColor: '#f4f4f5', borderRadius: 9999, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(100, Math.max(2, barPct))}%`,
                    backgroundColor: BAR_COLOR(r),
                    borderRadius: 9999,
                    transition: 'width 0.4s ease',
                  }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2D Heatmap: Transaction Type x Channel */}
      <div className="shadcn-card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#09090b', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <TrendingUp size={16} style={{ color: '#dc2626' }} />
          Fraud Share Heatmap &mdash; Transaction Type &times; Channel
        </h3>
        {(() => {
          const types = [...new Set(rawRows.map(r => r.trans_type))].filter(Boolean).sort();
          const channels = [...new Set(rawRows.map(r => r.channel))].filter(Boolean).sort();
          const lookup = {};
          rawRows.forEach(r => { lookup[r.trans_type + '__' + r.channel] = r.fraud_rate_percentage || 0; });
          const maxR = Math.max(...Object.values(lookup), 0.01);
          return (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'separate', borderSpacing: '4px', fontSize: '0.75rem', width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ padding: '0.5rem 0.75rem', color: '#71717a', fontWeight: 600, textAlign: 'left', backgroundColor: '#fafafa', borderRadius: '4px' }}>Type \ Channel</th>
                    {channels.map(ch => (
                      <th key={ch} style={{ padding: '0.5rem 0.75rem', color: '#09090b', fontWeight: 600, textAlign: 'center', backgroundColor: '#fafafa', borderRadius: '4px' }}>{CHANNEL_ICON[ch] || ''} {ch}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {types.map(tt => (
                    <tr key={tt}>
                      <td style={{ padding: '0.5rem 0.75rem', fontWeight: 600, color: '#09090b', whiteSpace: 'nowrap', backgroundColor: '#fafafa', borderRadius: '4px' }}>{tt}</td>
                      {channels.map(ch => {
                        const rate = lookup[tt + '__' + ch];
                        if (rate === undefined) return <td key={ch} style={{ padding: '0.5rem 0.75rem', background: '#f4f4f5', borderRadius: '4px', textAlign: 'center', color: '#a1a1aa' }}>—</td>;
                        const intensity = maxR > 0 ? rate / maxR : 0;
                        const bg = rate > 0 ? `rgba(239, 68, 68, ${Math.max(0.12, (intensity * 0.75)).toFixed(2)})` : '#f4f4f5';
                        const textC = (rate > 0 && intensity > 0.4) ? '#ffffff' : '#09090b';
                        return (
                          <td key={ch} style={{ padding: '0.5rem 0.75rem', background: bg, borderRadius: '4px', textAlign: 'center', color: textC, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", transition: 'background 0.3s' }}>
                            {fmtPct(rate)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })()}
      </div>

      {/* Raw Matrix Table */}
      <FraudMatrixTable rawRows={rawRows} riskColor={RISK_COLOR} />
    </div>
  );
}
