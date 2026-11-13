import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, ArrowUpDown, Check, RotateCcw, X, ArrowUp, ArrowDown } from 'lucide-react';

const ALL_SORT_FIELDS = [
  { id: 'risk_score', label: 'Risk Score', icon: '🔥', defaultOrder: 'desc' },
  { id: 'amount', label: 'Amount', icon: '💰', defaultOrder: 'desc' },
  { id: 'timestamp', label: 'Event Time', icon: '🕒', defaultOrder: 'desc' },
];

export default function SortPopover({ sortCriteria, setSortCriteria, onResetSort }) {
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (popoverRef.current && !popoverRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const isDefault =
    sortCriteria.length === 1 &&
    sortCriteria[0].field === 'risk_score' &&
    sortCriteria[0].order === 'desc';

  // Format button label
  const getButtonLabel = () => {
    if (isDefault) {
      return '🔥 Highest Risk First (Default)';
    }
    if (sortCriteria.length === 1) {
      const s = sortCriteria[0];
      if (s.field === 'amount' && s.order === 'desc') return '💰 Highest Amount First';
      if (s.field === 'timestamp' && s.order === 'desc') return '🕒 Most Recent First';
      const f = ALL_SORT_FIELDS.find((item) => item.id === s.field);
      return `${f?.icon || ''} ${f?.label || s.field} ${s.order === 'desc' ? '↓' : '↑'}`;
    }
    return `⚡ Multi-Level (${sortCriteria.map((s) => {
      const f = ALL_SORT_FIELDS.find((item) => item.id === s.field);
      const name = f ? (f.id === 'risk_score' ? 'Risk' : f.id === 'amount' ? 'Amount' : 'Time') : s.field;
      return `${name} ${s.order === 'desc' ? '↓' : '↑'}`;
    }).join(' + ')})`;
  };

  const applyPreset = (field, order) => {
    setSortCriteria([{ field, order }]);
  };

  const handleToggleField = (fieldId) => {
    const idx = sortCriteria.findIndex((s) => s.field === fieldId);
    if (idx !== -1) {
      if (sortCriteria.length === 1) {
        const currentOrder = sortCriteria[0].order;
        setSortCriteria([{ field: fieldId, order: currentOrder === 'desc' ? 'asc' : 'desc' }]);
      } else {
        setSortCriteria(sortCriteria.filter((s) => s.field !== fieldId));
      }
    } else {
      setSortCriteria([...sortCriteria, { field: fieldId, order: 'desc' }]);
    }
  };

  const handleToggleOrder = (fieldId, e) => {
    e.stopPropagation();
    const idx = sortCriteria.findIndex((s) => s.field === fieldId);
    if (idx !== -1) {
      setSortCriteria(
        sortCriteria.map((s) =>
          s.field === fieldId ? { ...s, order: s.order === 'desc' ? 'asc' : 'desc' } : s
        )
      );
    } else {
      setSortCriteria([...sortCriteria, { field: fieldId, order: 'asc' }]);
    }
  };

  const handleMovePriority = (fieldId, direction, e) => {
    e.stopPropagation();
    const idx = sortCriteria.findIndex((s) => s.field === fieldId);
    if (idx === -1) return;
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= sortCriteria.length) return;
    const newCriteria = [...sortCriteria];
    const temp = newCriteria[idx];
    newCriteria[idx] = newCriteria[targetIdx];
    newCriteria[targetIdx] = temp;
    setSortCriteria(newCriteria);
  };

  const handleReset = () => {
    if (onResetSort) {
      onResetSort();
    } else {
      setSortCriteria([{ field: 'risk_score', order: 'desc' }]);
    }
  };

  return (
    <div style={{ position: 'relative' }} ref={popoverRef}>
      {/* Trigger Button & Reset Button */}
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
        <button
          type="button"
          id="btn-sort-popover"
          onClick={() => setIsOpen(!isOpen)}
          style={{
            height: '32px',
            padding: '0 0.65rem',
            fontSize: '0.8125rem',
            borderRadius: '6px',
            border: `1px solid ${!isDefault ? '#93c5fd' : '#e4e4e7'}`,
            backgroundColor: !isDefault ? '#eff6ff' : '#ffffff',
            color: !isDefault ? '#1d4ed8' : '#09090b',
            fontWeight: 600,
            cursor: 'pointer',
            outline: 'none',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            transition: 'all 0.15s ease',
          }}
        >
          <ArrowUpDown size={13} style={{ color: !isDefault ? '#2563eb' : '#71717a' }} />
          <span>{getButtonLabel()}</span>
          <ChevronDown size={13} style={{ color: '#71717a', transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }} />
        </button>

        {/* Dedicated Quick Reset Button */}
        {!isDefault && (
          <button
            type="button"
            id="btn-quick-reset-sort"
            onClick={handleReset}
            title="Reset sort to default (Highest Risk First)"
            style={{
              height: '32px',
              padding: '0 0.55rem',
              fontSize: '0.75rem',
              fontWeight: 600,
              borderRadius: '6px',
              border: '1px solid #fecaca',
              backgroundColor: '#fef2f2',
              color: '#dc2626',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              transition: 'all 0.15s ease',
            }}
          >
            <RotateCcw size={12} />
            <span>Reset Sort</span>
          </button>
        )}
      </div>

      {/* Popover Modal Dropdown */}
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 6px)',
          left: 0,
          width: '330px',
          backgroundColor: '#ffffff',
          borderRadius: '8px',
          border: '1px solid #e4e4e7',
          boxShadow: '0 10px 25px -5px rgba(0,0,0,0.12), 0 8px 10px -6px rgba(0,0,0,0.08)',
          zIndex: 100,
          padding: '0.85rem',
          fontSize: '0.8125rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.65rem',
        }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f4f4f5', paddingBottom: '0.5rem' }}>
            <div>
              <div style={{ fontWeight: 700, color: '#09090b', fontSize: '0.875rem' }}>Sort Configuration</div>
              <div style={{ fontSize: '0.72rem', color: '#71717a' }}>Select preset or build multi-level priority</div>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#71717a', padding: '2px' }}
            >
              <X size={15} />
            </button>
          </div>

          {/* Quick Presets */}
          <div>
            <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
              Quick Presets
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {[
                { label: '🔥 Highest Risk First (Default)', field: 'risk_score', order: 'desc' },
                { label: '💰 Highest Amount First', field: 'amount', order: 'desc' },
                { label: '🕒 Most Recent First', field: 'timestamp', order: 'desc' },
              ].map((preset) => {
                const isActive =
                  sortCriteria.length === 1 &&
                  sortCriteria[0].field === preset.field &&
                  sortCriteria[0].order === preset.order;
                return (
                  <button
                    key={`${preset.field}_${preset.order}`}
                    type="button"
                    onClick={() => applyPreset(preset.field, preset.order)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.35rem 0.55rem',
                      borderRadius: '5px',
                      border: 'none',
                      backgroundColor: isActive ? '#eff6ff' : 'transparent',
                      color: isActive ? '#1d4ed8' : '#334155',
                      fontWeight: isActive ? 600 : 400,
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '0.78125rem',
                    }}
                  >
                    <span>{preset.label}</span>
                    {isActive && <Check size={14} color="#2563eb" strokeWidth={2.5} />}
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ height: '1px', backgroundColor: '#f4f4f5' }} />

          {/* Multi-Level Priority Customization */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#71717a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Multi-Level Priority
              </span>
              <span style={{ fontSize: '0.6875rem', color: '#a1a1aa' }}>
                Click to add / reorder
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              {ALL_SORT_FIELDS.map((field) => {
                const activeIdx = sortCriteria.findIndex((s) => s.field === field.id);
                const isActive = activeIdx !== -1;
                const priority = activeIdx + 1;
                const currentOrder = isActive ? sortCriteria[activeIdx].order : 'desc';

                return (
                  <div
                    key={field.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.35rem 0.5rem',
                      borderRadius: '6px',
                      backgroundColor: isActive ? '#f8fafc' : '#ffffff',
                      border: `1px solid ${isActive ? (priority === 1 ? '#bfdbfe' : '#e2e8f0') : '#f1f5f9'}`,
                    }}
                  >
                    {/* Left: Priority Badge & Field Name */}
                    <div
                      onClick={() => handleToggleField(field.id)}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', cursor: 'pointer', flex: 1 }}
                    >
                      <span
                        style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.6875rem',
                          fontWeight: 700,
                          backgroundColor: isActive ? (priority === 1 ? '#2563eb' : '#64748b') : '#e2e8f0',
                          color: isActive ? '#ffffff' : '#94a3b8',
                          transition: 'all 0.15s ease',
                        }}
                        title={isActive ? `Priority #${priority}` : 'Click to add to sort'}
                      >
                        {isActive ? priority : '+'}
                      </span>
                      <span style={{ fontWeight: isActive ? 600 : 400, color: isActive ? '#09090b' : '#64748b' }}>
                        {field.icon} {field.label}
                      </span>
                    </div>

                    {/* Right: Order Direction & Reorder arrows */}
                    {isActive && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {/* Direction Toggle */}
                        <button
                          type="button"
                          onClick={(e) => handleToggleOrder(field.id, e)}
                          title={`Currently ${currentOrder === 'desc' ? 'Descending' : 'Ascending'}. Click to toggle.`}
                          style={{
                            height: '24px',
                            padding: '0 0.4rem',
                            fontSize: '0.7rem',
                            fontWeight: 600,
                            borderRadius: '4px',
                            border: `1px solid ${currentOrder === 'desc' ? '#bfdbfe' : '#fecaca'}`,
                            backgroundColor: currentOrder === 'desc' ? '#eff6ff' : '#fef2f2',
                            color: currentOrder === 'desc' ? '#1d4ed8' : '#b91c1c',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '2px',
                          }}
                        >
                          {currentOrder === 'desc' ? '↓ High' : '↑ Low'}
                        </button>

                        {/* Reorder Arrows (if multi-level) */}
                        {sortCriteria.length > 1 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                            <button
                              type="button"
                              disabled={activeIdx === 0}
                              onClick={(e) => handleMovePriority(field.id, 'up', e)}
                              title="Move priority up"
                              style={{
                                padding: '1px',
                                border: 'none',
                                background: 'transparent',
                                cursor: activeIdx === 0 ? 'default' : 'pointer',
                                color: activeIdx === 0 ? '#cbd5e1' : '#64748b',
                                lineHeight: 1,
                              }}
                            >
                              <ArrowUp size={11} />
                            </button>
                            <button
                              type="button"
                              disabled={activeIdx === sortCriteria.length - 1}
                              onClick={(e) => handleMovePriority(field.id, 'down', e)}
                              title="Move priority down"
                              style={{
                                padding: '1px',
                                border: 'none',
                                background: 'transparent',
                                cursor: activeIdx === sortCriteria.length - 1 ? 'default' : 'pointer',
                                color: activeIdx === sortCriteria.length - 1 ? '#cbd5e1' : '#64748b',
                                lineHeight: 1,
                              }}
                            >
                              <ArrowDown size={11} />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ height: '1px', backgroundColor: '#f4f4f5' }} />

          {/* Footer Actions */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '0.15rem' }}>
            <button
              type="button"
              onClick={handleReset}
              className="btn-shadcn btn-secondary"
              style={{
                height: '28px',
                padding: '0 0.55rem',
                fontSize: '0.75rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                color: '#64748b',
              }}
            >
              <RotateCcw size={12} />
              <span>Reset to Default</span>
            </button>

            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="btn-shadcn btn-primary"
              style={{
                height: '28px',
                padding: '0 0.85rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor: '#09090b',
                color: '#ffffff',
                borderRadius: '5px',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

