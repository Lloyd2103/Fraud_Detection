import React from 'react';
import { User, Users, TrendingUp, Clock } from 'lucide-react';

export default function VerdictsKpiCards({
  verdictStatsLoading,
  verdictStats,
  activeRangeLabel,
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
      {/* Card 1: My Verdicts */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            MY VERDICTS
          </span>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.2rem',
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: '#2563eb',
            backgroundColor: '#eff6ff',
            border: '1px solid #dbeafe',
            padding: '0.1rem 0.4rem',
            borderRadius: '4px',
          }}>
            <User size={11} strokeWidth={2} /> Personal
          </span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.03em' }}>
          {verdictStatsLoading ? (
            <span style={{ color: '#a1a1aa', fontSize: '1rem', fontWeight: 500 }}>Loading...</span>
          ) : (
            verdictStats?.mine?.total ?? 0
          )}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.25rem' }}>
          Decisions processed ({activeRangeLabel})
        </p>
      </div>

      {/* Card 2: Breakdown FRAUD / LEGIT */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            BREAKDOWN
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
            <TrendingUp size={11} strokeWidth={2} /> Classification
          </span>
        </div>
        <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.02em', display: 'flex', alignItems: 'baseline', gap: '0.4rem', flexWrap: 'wrap' }}>
          {verdictStatsLoading ? (
            <span style={{ color: '#a1a1aa', fontSize: '1rem', fontWeight: 500 }}>Loading...</span>
          ) : (
            <>
              <span style={{ color: '#dc2626' }}>{verdictStats?.mine?.fraud ?? 0} <span style={{ fontSize: '0.8125rem', fontWeight: 600 }}>FRAUD</span></span>
              <span style={{ color: '#d4d4d8', fontSize: '1rem' }}>/</span>
              <span style={{ color: '#16a34a' }}>{verdictStats?.mine?.legit ?? 0} <span style={{ fontSize: '0.8125rem', fontWeight: 600 }}>LEGIT</span></span>
            </>
          )}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.25rem' }}>
          Your decisions ({activeRangeLabel})
        </p>
      </div>

      {/* Card 3: Team Verdicts */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            TEAM VERDICTS
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
            <Users size={11} strokeWidth={2} /> All Team
          </span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.03em' }}>
          {verdictStatsLoading ? (
            <span style={{ color: '#a1a1aa', fontSize: '1rem', fontWeight: 500 }}>Loading...</span>
          ) : (
            verdictStats?.team?.total ?? 0
          )}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.25rem' }}>
          {verdictStatsLoading ? 'Loading...' : `${verdictStats?.team?.fraud ?? 0} FRAUD · ${verdictStats?.team?.legit ?? 0} LEGIT (${activeRangeLabel})`}
        </p>
      </div>

      {/* Card 4: My Avg Processing Time */}
      <div className="shadcn-card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            MY AVG PROCESSING TIME
          </span>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.2rem',
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: '#7c3aed',
            backgroundColor: '#f5f3ff',
            border: '1px solid #ede9fe',
            padding: '0.1rem 0.4rem',
            borderRadius: '4px',
          }}>
            <Clock size={11} strokeWidth={2} /> Efficiency
          </span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.03em' }}>
          {verdictStatsLoading ? (
            <span style={{ color: '#a1a1aa', fontSize: '1rem', fontWeight: 500 }}>Loading...</span>
          ) : (
            verdictStats?.mine?.avg_processing_time
              ? `${Number(verdictStats.mine.avg_processing_time).toFixed(1)}s`
              : '—'
          )}
        </div>
        <p style={{ fontSize: '0.75rem', color: '#71717a', marginTop: '0.25rem' }}>
          Average time per decision ({activeRangeLabel})
        </p>
      </div>
    </div>
  );
}

