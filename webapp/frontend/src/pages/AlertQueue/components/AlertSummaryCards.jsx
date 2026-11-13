import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

export default function AlertSummaryCards({
  loading,
  summary,
  pendingCount,
  criticalCount,
  processedCount,
  p95Str,
  latency,
  userRole,
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
      {/* Card 1: Pending */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Pending Triage Queue
          </span>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.2rem',
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: '#dc2626',
            backgroundColor: '#fef2f2',
            border: '1px solid #fee2e2',
            padding: '0.1rem 0.4rem',
            borderRadius: '4px',
          }}>
            <TrendingUp size={11} strokeWidth={2} /> High Priority
          </span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.03em' }}>
          {loading && !summary ? (
            <span style={{ color: '#a1a1aa', fontSize: '1rem', fontWeight: 500 }}>Loading...</span>
          ) : (
            pendingCount ?? '—'
          )}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.25rem' }}>
          Real-time fraud alerts waiting for auditor inspection
        </p>
      </div>

      {/* Card 2: Critical Alerts */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Critical Risk (&gt;80%)
          </span>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.2rem',
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: '#b45309',
            backgroundColor: '#fffbeb',
            border: '1px solid #fef3c7',
            padding: '0.1rem 0.4rem',
            borderRadius: '4px',
          }}>
            Urgent SLA
          </span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.03em' }}>
          {loading && !summary ? (
            <span style={{ color: '#a1a1aa', fontSize: '1rem', fontWeight: 500 }}>Loading...</span>
          ) : (
            criticalCount ?? '—'
          )}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.25rem' }}>
          Immediate fraud escalation cases
        </p>
      </div>

      {/* Card 3: Processed Alerts */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            TOTAL AUDITED VERDICTS
          </span>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.2rem',
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: '#16a34a',
            backgroundColor: '#f0fdf4',
            border: '1px solid #dcfce7',
            padding: '0.1rem 0.4rem',
            borderRadius: '4px',
          }}>
            <TrendingDown size={11} strokeWidth={2} /> Active Audited
          </span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.03em' }}>
          {loading && !summary ? (
            <span style={{ color: '#a1a1aa', fontSize: '1rem', fontWeight: 500 }}>Loading...</span>
          ) : (
            processedCount ?? '—'
          )}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.25rem' }}>
          Audited feedback saved in Delta Lake
        </p>
      </div>

      {/* Card 4: P95 Latency (SLA) */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            P95 Latency (SLA)
          </span>
          {userRole === 'auditor' ? (
            <span style={{ fontSize: '0.6875rem', color: '#71717a', backgroundColor: '#f4f4f5', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
              Restricted
            </span>
          ) : loading && !latency?.status ? (
            <span style={{ fontSize: '0.6875rem', color: '#a1a1aa' }}>Loading...</span>
          ) : (
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.2rem',
              fontSize: '0.6875rem',
              fontWeight: 600,
              color: latency?.status === 'HEALTHY' ? '#16a34a' : (latency?.status === 'WARNING' ? '#d97706' : (latency?.status && latency.status !== 'NO_DATA' ? '#dc2626' : '#71717a')),
              backgroundColor: latency?.status === 'HEALTHY' ? '#f0fdf4' : (latency?.status === 'WARNING' ? '#fffbeb' : (latency?.status && latency.status !== 'NO_DATA' ? '#fef2f2' : '#f4f4f5')),
              border: `1px solid ${latency?.status === 'HEALTHY' ? '#dcfce7' : (latency?.status === 'WARNING' ? '#fef3c7' : (latency?.status && latency.status !== 'NO_DATA' ? '#fecaca' : '#e4e4e7'))}`,
              padding: '0.1rem 0.4rem',
              borderRadius: '4px',
            }}>
              {latency?.status || '—'}
            </span>
          )}
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.03em' }}>
          {userRole === 'auditor' ? (
            <span style={{ fontSize: '0.875rem', color: '#71717a', fontWeight: 500 }}>Restricted</span>
          ) : loading && !p95Str ? (
            <span style={{ color: '#a1a1aa', fontSize: '1rem', fontWeight: 500 }}>Loading...</span>
          ) : (
            p95Str || '—'
          )}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.25rem' }}>
          {userRole === 'auditor' ? 'Restricted to Analyst & Admin' : 'SLA benchmark: < 2.0s compliance'}
        </p>
      </div>
    </div>
  );
}

