import React from 'react';
import { Search } from 'lucide-react';
import SortPopover from './SortPopover';

export default function AlertFilterBar({
  searchQuery,
  setSearchQuery,
  selectedChannel,
  setSelectedChannel,
  selectedAmountRange,
  setSelectedAmountRange,
  sortCriteria,
  setSortCriteria,
  onResetSort,
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
          id="input-alert-search"
          placeholder="Search Tx ID or Account..."
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

      {/* 4. Priority Sorting Dropdown / Popover Modal */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 500 }}>Sort by:</span>
        <SortPopover
          sortCriteria={sortCriteria}
          setSortCriteria={setSortCriteria}
          onResetSort={onResetSort}
        />
      </div>
    </div>
  );
}

