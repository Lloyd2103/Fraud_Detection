import React from 'react';
import { ChevronRight } from 'lucide-react';

export default function PageHeader({
  activeTab,
  returnTab,
  changeTab,
  tabLabels,
  currentTabLabel,
  pipelineHealth,
  formatAge,
}) {
  const state = pipelineHealth?.detector_state || 'IDLE';
  const isUp = state === 'ACTIVE';
  const isIdle = state === 'IDLE';
  const badgeColor = isUp ? '#16a34a' : isIdle ? '#d97706' : '#dc2626';
  const badgeBg = isUp ? '#dcfce7' : isIdle ? '#fef3c7' : '#fee2e2';
  const ageStr = pipelineHealth?.last_alert_age_seconds ? ` (last alert ${formatAge(pipelineHealth.last_alert_age_seconds)})` : '';

  return (
    <div style={{
      padding: '1.25rem 1.5rem 0.5rem 1.5rem',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
    }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: '#71717a' }}>
          <span style={{ cursor: 'pointer' }} onClick={() => changeTab('alerts')}>Home</span>
          <ChevronRight size={12} strokeWidth={1.5} />
          <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>Fraud Detection</span>
          <ChevronRight size={12} strokeWidth={1.5} />
          {activeTab === 'detail' ? (
            <>
              <span
                style={{ cursor: 'pointer', color: '#71717a', textDecoration: 'underline' }}
                onClick={() => changeTab(returnTab || 'alerts')}
              >
                {tabLabels[returnTab] || 'Alert Queue'}
              </span>
              <ChevronRight size={12} strokeWidth={1.5} />
              <span style={{ color: '#09090b', fontWeight: 600 }}>Details &amp; Inspection</span>
            </>
          ) : (
            <span style={{ color: '#09090b', fontWeight: 500 }}>{currentTabLabel}</span>
          )}
        </div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.03em', marginTop: '0.25rem', fontFamily: "'JetBrains Mono', monospace" }}>
          Fraud Detection
        </h1>
        <p style={{ fontSize: '0.8125rem', color: '#71717a' }}>
          Real-Time Credit Card Fraud Telemetry &amp; AI Drift Governance
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.75rem', color: badgeColor, background: badgeBg, padding: '0.25rem 0.625rem', borderRadius: '9999px', fontWeight: 500 }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: badgeColor }} />
          Pipeline: {state}{ageStr}
        </span>
      </div>
    </div>
  );
}

