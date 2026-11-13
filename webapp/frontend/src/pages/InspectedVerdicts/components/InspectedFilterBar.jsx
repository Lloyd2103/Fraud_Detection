import React from 'react';
import { Search } from 'lucide-react';

export default function InspectedFilterBar({
  searchQuery,
  setSearchQuery,
  selectedChannel,
  setSelectedChannel,
  selectedAmountRange,
  setSelectedAmountRange,
  auditorScope,
  setAuditorScope,
  teamTotal,
  mineTotal,
  timeScope = 'PERIOD',
  setTimeScope = null,
}) {
  return (
    <div style={{
      padding: '0.75rem 1.25rem',
      borderBottom: '1px solid #e4e4e7',
      backgroundColor: '#ffffff',
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      flexWrap: 'wrap',
    }}>
      {/* 1. Search Box */}
      <div style={{ position: 'relative', width: '260px' }}>
        <Search size={14} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: '#71717a' }} />
        <input
          type="text"
          id="input-inspected-search"
          placeholder="Search ID, auditor, reason..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            width: '100%',
            height: '32px',
            paddingLeft: '30px',
            paddingRight: '10px',
            fontSize: '0.8125rem',
            borderRadius: '6px',
            border: '1px solid #e4e4e7',
            backgroundColor: '#ffffff',
            color: '#09090b',
            outline: 'none',
          }}
        />
      </div>

      {/* 2. Channel Filter Dropdown */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
        <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Channel:</span>
        <select
          value={selectedChannel}
          onChange={(e) => setSelectedChannel(e.target.value)}
          style={{
            height: '32px',
            padding: '0 0.6rem',
            fontSize: '0.8125rem',
            borderRadius: '6px',
            border: '1px solid #e4e4e7',
            backgroundColor: '#ffffff',
            color: selectedChannel !== 'ALL' ? '#09090b' : '#52525b',
            fontWeight: selectedChannel !== 'ALL' ? 600 : 400,
            cursor: 'pointer',
            outline: 'none',
          }}
        >
          <option value="ALL">All Channels</option>
          <option value="ONLINE">ONLINE</option>
          <option value="ATM">ATM</option>
          <option value="POS">POS</option>
          <option value="TRANSFER">TRANSFER</option>
        </select>
      </div>

      {/* 3. Amount Filter Dropdown */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
        <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Amount:</span>
        <select
          value={selectedAmountRange}
          onChange={(e) => setSelectedAmountRange(e.target.value)}
          style={{
            height: '32px',
            padding: '0 0.6rem',
            fontSize: '0.8125rem',
            borderRadius: '6px',
            border: '1px solid #e4e4e7',
            backgroundColor: '#ffffff',
            color: selectedAmountRange !== 'ALL' ? '#09090b' : '#52525b',
            fontWeight: selectedAmountRange !== 'ALL' ? 600 : 400,
            cursor: 'pointer',
            outline: 'none',
          }}
        >
          <option value="ALL">All Amounts</option>
          <option value="LT_1M">&lt; 1M</option>
          <option value="1M_10M">1M - 10M</option>
          <option value="GT_10M">&gt; 10M</option>
        </select>
      </div>

      {/* 4. Auditor Scope Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
        <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Auditor:</span>
        <div style={{
          display: 'inline-flex',
          padding: '2px',
          backgroundColor: '#f4f4f5',
          borderRadius: '6px',
          border: '1px solid #e4e4e7'
        }}>
          <button
            type="button"
            id="btn-scope-all"
            onClick={() => setAuditorScope('ALL')}
            style={{
              height: '26px',
              padding: '0 0.65rem',
              fontSize: '0.75rem',
              fontWeight: auditorScope === 'ALL' ? 600 : 500,
              borderRadius: '4px',
              border: 'none',
              backgroundColor: auditorScope === 'ALL' ? '#ffffff' : 'transparent',
              color: auditorScope === 'ALL' ? '#09090b' : '#71717a',
              boxShadow: auditorScope === 'ALL' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
          >
            👥 Team ({teamTotal ?? 0})
          </button>
          <button
            type="button"
            id="btn-scope-mine"
            onClick={() => setAuditorScope('MINE')}
            style={{
              height: '26px',
              padding: '0 0.65rem',
              fontSize: '0.75rem',
              fontWeight: auditorScope === 'MINE' ? 600 : 500,
              borderRadius: '4px',
              border: 'none',
              backgroundColor: auditorScope === 'MINE' ? '#4f46e5' : 'transparent',
              color: auditorScope === 'MINE' ? '#ffffff' : '#71717a',
              boxShadow: auditorScope === 'MINE' ? '0 1px 2px rgba(79,70,229,0.2)' : 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
          >
            👤 Mine ({mineTotal ?? 0})
          </button>
        </div>
      </div>

      {/* 5. Time Scope Toggle: Selected Period vs All Time */}
      {setTimeScope && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Time:</span>
          <div style={{
            display: 'inline-flex',
            padding: '2px',
            backgroundColor: '#f4f4f5',
            borderRadius: '6px',
            border: '1px solid #e4e4e7'
          }}>
            <button
              type="button"
              id="btn-time-scope-period"
              onClick={() => setTimeScope('PERIOD')}
              style={{
                height: '26px',
                padding: '0 0.65rem',
                fontSize: '0.75rem',
                fontWeight: timeScope === 'PERIOD' ? 600 : 500,
                borderRadius: '4px',
                border: 'none',
                backgroundColor: timeScope === 'PERIOD' ? '#ffffff' : 'transparent',
                color: timeScope === 'PERIOD' ? '#09090b' : '#71717a',
                boxShadow: timeScope === 'PERIOD' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                transition: 'all 0.15s ease'
              }}
              title="Filter by selected Day/Month from picker above"
            >
              📅 Selected Period
            </button>
            <button
              type="button"
              id="btn-time-scope-all"
              onClick={() => setTimeScope('ALL_TIME')}
              style={{
                height: '26px',
                padding: '0 0.65rem',
                fontSize: '0.75rem',
                fontWeight: timeScope === 'ALL_TIME' ? 600 : 500,
                borderRadius: '4px',
                border: 'none',
                backgroundColor: timeScope === 'ALL_TIME' ? '#2563eb' : 'transparent',
                color: timeScope === 'ALL_TIME' ? '#ffffff' : '#71717a',
                boxShadow: timeScope === 'ALL_TIME' ? '0 1px 2px rgba(37,99,235,0.2)' : 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                transition: 'all 0.15s ease'
              }}
              title="Show all transactions across all months and years"
            >
              🌐 All Time
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

