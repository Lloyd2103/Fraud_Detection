import React from 'react';
import { Search, Bell, LogOut } from 'lucide-react';

export default function Header({
  setCommandOpen,
  pipelineHealth,
  user,
  logout,
  roleStyle,
}) {
  return (
    <header style={{
      height: '56px',
      backgroundColor: '#ffffff',
      borderBottom: '1px solid #e4e4e7',
      padding: '0 1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem',
      position: 'sticky',
      top: 0,
      zIndex: 40,
    }}>
      {/* Top Bar Search with ⌘+K */}
      <div
        onClick={() => setCommandOpen(true)}
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          width: '100%',
          maxWidth: '320px',
          height: '32px',
          backgroundColor: '#fafafa',
          border: '1px solid #e4e4e7',
          borderRadius: '6px',
          padding: '0 0.65rem',
          cursor: 'pointer',
          color: '#71717a',
          fontSize: '0.8125rem',
          gap: '0.5rem',
        }}
      >
        <Search size={14} strokeWidth={1.5} style={{ color: '#a1a1aa' }} />
        <span style={{ flex: 1, color: '#a1a1aa' }}>Search transactions, metrics...</span>
        <kbd style={{
          fontSize: '0.625rem',
          fontFamily: "'JetBrains Mono', monospace",
          backgroundColor: '#ffffff',
          border: '1px solid #e4e4e7',
          padding: '0.1rem 0.35rem',
          borderRadius: '4px',
          color: '#71717a',
        }}>
          ⌘K
        </kbd>
      </div>

      {/* Right Header Status & Signal */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        {/* Live Streaming Signal */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.45rem',
          backgroundColor: '#ffffff',
          border: '1px solid #e4e4e7',
          padding: '0.25rem 0.65rem',
          borderRadius: '6px',
          fontSize: '0.75rem',
          color: '#27272a',
        }}>
          <span className="pulsing-signal" style={{
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            backgroundColor: pipelineHealth?.kafka_reachable ? '#10b981' : '#ef4444',
          }} />
          <span style={{ fontWeight: 500 }}>
            Kafka: {pipelineHealth?.kafka_reachable ? 'Active' : 'Down'} &bull; Pipeline: {pipelineHealth?.detector_state || 'IDLE'}
          </span>
        </div>

        {/* Notification Bell */}
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            border: '1px solid #e4e4e7',
            backgroundColor: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#71717a',
          }}
          title="Notifications"
        >
          <Bell size={15} strokeWidth={1.5} />
        </div>

        {/* Role Badge */}
        {user && (
          <span style={{
            fontSize: '0.6875rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            padding: '0.2rem 0.5rem',
            borderRadius: '4px',
            backgroundColor: roleStyle?.bg || '#f4f4f5',
            color: roleStyle?.color || '#09090b',
            border: `1px solid ${roleStyle?.border || '#e4e4e7'}`,
          }}>
            {user.role || 'auditor'}
          </span>
        )}

        {/* Sign Out Button */}
        <button
          onClick={logout}
          title="Sign out of the system"
          style={{
            height: '32px',
            padding: '0 0.65rem',
            borderRadius: '6px',
            border: '1px solid #fee2e2',
            backgroundColor: '#ffffff',
            color: '#dc2626',
            fontSize: '0.75rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#fef2f2';
            e.currentTarget.style.borderColor = '#fca5a5';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#ffffff';
            e.currentTarget.style.borderColor = '#fee2e2';
          }}
        >
          <LogOut size={13} strokeWidth={1.75} />
          <span>Sign Out</span>
        </button>
      </div>
    </header>
  );
}

