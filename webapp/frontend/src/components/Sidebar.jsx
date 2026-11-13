import React from 'react';
import {
  Shield,
  LayoutDashboard,
  Check,
  BarChart2,
  LineChart,
  History,
  Activity,
  Users,
  Settings,
  LogOut,
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  changeTab,
  user,
  logout,
  pendingAlertsCount = 0,
  allowedTabs = [],
}) {
  const ALL_MODULES = [
    { key: 'alerts', icon: LayoutDashboard, label: 'Alert Queue', hasBadge: true },
    { key: 'inspected', icon: Check, label: 'Inspected Verdicts' },
    { key: 'fraud-summary', icon: BarChart2, label: 'Fraud Summary' },
    { key: 'models', icon: LineChart, label: 'Model Performance & Drift' },
    { key: 'audit', icon: History, label: 'Delta Time Travel & Audit' },
    { key: 'latency', icon: Activity, label: 'Latency Monitoring (SLA)' },
  ];

  const modules = ALL_MODULES.filter((m) => allowedTabs.includes(m.key));

  return (
    <aside style={{
      width: '240px',
      backgroundColor: '#ffffff',
      borderRight: '1px solid #e4e4e7',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      position: 'sticky',
      top: 0,
      height: '100vh',
    }}>
      {/* Brand Header */}
      <div style={{
        height: '56px',
        borderBottom: '1px solid #e4e4e7',
        padding: '0 1.25rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.65rem',
      }}>
        <div style={{
          width: '26px',
          height: '26px',
          borderRadius: '6px',
          backgroundColor: '#09090b',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Shield size={14} strokeWidth={1.75} />
        </div>
        <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#09090b', letterSpacing: '-0.02em', fontFamily: "'JetBrains Mono', monospace" }}>
          Fraud Detection
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: '0.625rem',
          fontFamily: "'JetBrains Mono', monospace",
          color: '#71717a',
          backgroundColor: '#f4f4f5',
          border: '1px solid #e4e4e7',
          padding: '0.1rem 0.35rem',
          borderRadius: '4px',
        }}>
          v2.4
        </span>
      </div>

      {/* Navigation items */}
      <div style={{ padding: '0.75rem 0.65rem', display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: 1, overflowY: 'auto' }}>
        <div style={{ padding: '0.25rem 0.5rem', fontSize: '0.6875rem', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Modules
        </div>

        {modules.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.key;
          return (
            <button
              key={item.key}
              type="button"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                padding: '0.45rem 0.65rem',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: isActive ? '#f4f4f5' : 'transparent',
                color: isActive ? '#09090b' : '#71717a',
                fontWeight: isActive ? 600 : 500,
                boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                fontSize: '0.8125rem',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
              }}
              onClick={() => changeTab(item.key)}
            >
              <Icon size={16} strokeWidth={1.5} style={{ color: isActive ? '#09090b' : '#a1a1aa' }} />
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.hasBadge && pendingAlertsCount > 0 && (
                <span style={{
                  fontSize: '0.6875rem',
                  fontWeight: 600,
                  backgroundColor: '#fee2e2',
                  color: '#991b1b',
                  padding: '0.1rem 0.4rem',
                  borderRadius: '9999px',
                }}>
                  {pendingAlertsCount}
                </span>
              )}
            </button>
          );
        })}

        {/* System Section for Admin */}
        {user?.role === 'admin' && (
          <>
            <div style={{ padding: '0.75rem 0.5rem 0.25rem 0.5rem', fontSize: '0.6875rem', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              System
            </div>

            <button
              type="button"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                padding: '0.45rem 0.65rem',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: activeTab === 'team' ? '#f4f4f5' : 'transparent',
                color: activeTab === 'team' ? '#09090b' : '#71717a',
                fontWeight: activeTab === 'team' ? 600 : 500,
                boxShadow: activeTab === 'team' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                fontSize: '0.8125rem',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
              }}
              onClick={() => changeTab('team')}
            >
              <Users size={16} strokeWidth={1.5} style={{ color: activeTab === 'team' ? '#4f46e5' : '#a1a1aa' }} />
              <span>Team &amp; Roles</span>
            </button>

            <button
              type="button"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                padding: '0.45rem 0.65rem',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: activeTab === 'delta-config' ? '#f4f4f5' : 'transparent',
                color: activeTab === 'delta-config' ? '#09090b' : '#71717a',
                fontWeight: activeTab === 'delta-config' ? 600 : 500,
                boxShadow: activeTab === 'delta-config' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                fontSize: '0.8125rem',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
              }}
              onClick={() => changeTab('delta-config')}
            >
              <Settings size={16} strokeWidth={1.5} style={{ color: activeTab === 'delta-config' ? '#2563eb' : '#a1a1aa' }} />
              <span>Delta Lake Config</span>
            </button>
          </>
        )}
      </div>

      {/* User profile footer */}
      {user && (
        <div style={{
          borderTop: '1px solid #e4e4e7',
          padding: '0.75rem 1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.65rem',
        }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            backgroundColor: '#09090b',
            color: '#ffffff',
            fontSize: '0.75rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            {(user.full_name || user.email || 'U')[0].toUpperCase()}
          </div>
          <div style={{ overflow: 'hidden', flex: 1 }}>
            <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#09090b', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
              {user.full_name || user.email}
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#71717a', textTransform: 'capitalize' }}>
              {user.role || 'auditor'}
            </div>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            style={{
              background: 'none',
              border: 'none',
              color: '#a1a1aa',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '0.25rem',
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = '#ef4444'}
            onMouseLeave={(e) => e.currentTarget.style.color = '#a1a1aa'}
          >
            <LogOut size={15} strokeWidth={1.5} />
          </button>
        </div>
      )}
    </aside>
  );
}

