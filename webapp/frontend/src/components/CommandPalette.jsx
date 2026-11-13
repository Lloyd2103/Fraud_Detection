import React from 'react';
import { Search } from 'lucide-react';

export default function CommandPalette({
  commandOpen,
  setCommandOpen,
  commandSearch,
  setCommandSearch,
  filteredCommands = [],
  changeTab,
}) {
  if (!commandOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.4)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '15vh',
        zIndex: 100,
      }}
      onClick={() => setCommandOpen(false)}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '540px',
          backgroundColor: '#ffffff',
          border: '1px solid #e4e4e7',
          borderRadius: '8px',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Command search input */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0.75rem 1rem',
          borderBottom: '1px solid #e4e4e7',
          gap: '0.65rem',
        }}>
          <Search size={16} strokeWidth={1.5} style={{ color: '#a1a1aa' }} />
          <input
            type="text"
            autoFocus
            value={commandSearch}
            onChange={(e) => setCommandSearch(e.target.value)}
            placeholder="Type a command or search..."
            style={{
              width: '100%',
              border: 'none',
              outline: 'none',
              fontSize: '0.875rem',
              color: '#09090b',
            }}
          />
          <kbd style={{
            fontSize: '0.6875rem',
            fontFamily: "'JetBrains Mono', monospace",
            backgroundColor: '#f4f4f5',
            border: '1px solid #e4e4e7',
            padding: '0.1rem 0.35rem',
            borderRadius: '4px',
            color: '#71717a',
          }}>
            ESC
          </kbd>
        </div>

        {/* Results list */}
        <div style={{ padding: '0.5rem', maxHeight: '280px', overflowY: 'auto' }}>
          <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#a1a1aa', padding: '0.35rem 0.5rem', textTransform: 'uppercase' }}>
            Navigation
          </div>
          {filteredCommands.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.key}
                onClick={() => {
                  changeTab(item.key);
                  setCommandOpen(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.65rem',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.8125rem',
                  color: '#09090b',
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f4f4f5'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <Icon size={16} strokeWidth={1.5} style={{ color: '#71717a' }} />
                <span>Go to {item.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

