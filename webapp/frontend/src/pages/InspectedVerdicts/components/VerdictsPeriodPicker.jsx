import React from 'react';
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react';
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';
import { format, parseISO } from 'date-fns';

export default function VerdictsPeriodPicker({
  period,
  setPeriod,
  selectedDate,
  setSelectedDate,
  selectedMonth,
  setSelectedMonth,
  pickerOpen,
  setPickerOpen,
  pickerRef,
  todayVn,
  thisMonthVn,
  monthPickerYear,
  setMonthPickerYear,
  isNextDisabled,
  handlePrev,
  handleNext,
  handleJumpTodayOrThisMonth,
  valueDisplayStr,
  activeRangeLabel,
}) {
  return (
    <div style={{
      padding: '0.85rem 1.25rem',
      backgroundColor: '#ffffff',
      border: '1px solid #e4e4e7',
      borderRadius: '8px',
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '0.75rem'
    }}>
      {/* Unified Control Group: [ Day | Month ] ◀ <value> ▶ [ Today | This Month ] */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#09090b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <Calendar size={15} /> Time Period:
        </span>

        {/* Segmented Button: [ Day | Month ] */}
        <div style={{
          display: 'inline-flex',
          padding: '2px',
          backgroundColor: '#f4f4f5',
          borderRadius: '6px',
          border: '1px solid #e4e4e7',
        }}>
          <button
            type="button"
            id="btn-period-mode-day"
            onClick={() => setPeriod('day')}
            style={{
              padding: '0.3rem 0.75rem',
              fontSize: '0.75rem',
              fontWeight: period === 'day' ? 600 : 500,
              borderRadius: '4px',
              border: 'none',
              backgroundColor: period === 'day' ? '#ffffff' : 'transparent',
              color: period === 'day' ? '#09090b' : '#71717a',
              boxShadow: period === 'day' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            Day
          </button>
          <button
            type="button"
            id="btn-period-mode-month"
            onClick={() => setPeriod('month')}
            style={{
              padding: '0.3rem 0.75rem',
              fontSize: '0.75rem',
              fontWeight: period === 'month' ? 600 : 500,
              borderRadius: '4px',
              border: 'none',
              backgroundColor: period === 'month' ? '#ffffff' : 'transparent',
              color: period === 'month' ? '#09090b' : '#71717a',
              boxShadow: period === 'month' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            Month
          </button>
        </div>

        {/* ◀ Prev Button */}
        <button
          type="button"
          id="btn-period-prev"
          onClick={handlePrev}
          title={period === 'day' ? 'Previous day' : 'Previous month'}
          className="btn-shadcn btn-secondary"
          style={{
            height: '30px',
            width: '30px',
            padding: 0,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '6px'
          }}
        >
          <ChevronLeft size={14} />
        </button>

        {/* <value> with Popover Picker */}
        <div ref={pickerRef} style={{ position: 'relative' }}>
          <button
            type="button"
            id="btn-period-picker-trigger"
            onClick={() => setPickerOpen((prev) => !prev)}
            style={{
              height: '30px',
              padding: '0 0.75rem',
              fontSize: '0.8125rem',
              fontWeight: 600,
              color: '#09090b',
              backgroundColor: '#ffffff',
              border: pickerOpen ? '1px solid #2563eb' : '1px solid #e4e4e7',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
            }}
          >
            <Calendar size={13} color="#2563eb" />
            <span>{valueDisplayStr}</span>
          </button>

          {pickerOpen && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '6px',
              backgroundColor: '#ffffff',
              border: '1px solid #e4e4e7',
              borderRadius: '8px',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)',
              zIndex: 50,
              padding: '0.75rem'
            }}>
              {period === 'day' ? (
                <DayPicker
                  mode="single"
                  selected={parseISO(selectedDate)}
                  onSelect={(date) => {
                    if (date) {
                      const formatted = format(date, 'yyyy-MM-dd');
                      if (formatted <= todayVn) {
                        setSelectedDate(formatted);
                        setPickerOpen(false);
                      }
                    }
                  }}
                  disabled={{ after: parseISO(todayVn) }}
                />
              ) : (
                <div style={{ width: '240px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#09090b' }}>Select Month</span>
                    <select
                      value={monthPickerYear}
                      onChange={(e) => setMonthPickerYear(parseInt(e.target.value, 10))}
                      style={{
                        fontSize: '0.75rem',
                        padding: '0.2rem 0.4rem',
                        borderRadius: '4px',
                        border: '1px solid #e4e4e7',
                        fontWeight: 600
                      }}
                    >
                      <option value={2025}>2025</option>
                      <option value={2026}>2026</option>
                    </select>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.4rem' }}>
                    {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((monthName, idx) => {
                      const m = idx + 1;
                      const mStr = `${monthPickerYear}-${String(m).padStart(2, '0')}`;
                      const isFuture = mStr > thisMonthVn;
                      const isSelected = selectedMonth === mStr;
                      return (
                        <button
                          key={m}
                          type="button"
                          disabled={isFuture}
                          onClick={() => {
                            setSelectedMonth(mStr);
                            setPickerOpen(false);
                          }}
                          style={{
                            padding: '0.4rem 0.2rem',
                            fontSize: '0.75rem',
                            fontWeight: isSelected ? 600 : 500,
                            borderRadius: '4px',
                            border: '1px solid',
                            borderColor: isSelected ? '#2563eb' : '#e4e4e7',
                            backgroundColor: isSelected ? '#eff6ff' : (isFuture ? '#f4f4f5' : '#ffffff'),
                            color: isSelected ? '#2563eb' : (isFuture ? '#a1a1aa' : '#09090b'),
                            cursor: isFuture ? 'not-allowed' : 'pointer',
                          }}
                        >
                          {monthName}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ▶ Next Button */}
        <button
          type="button"
          id="btn-period-next"
          disabled={isNextDisabled}
          onClick={handleNext}
          title={isNextDisabled ? 'Cannot select future date' : (period === 'day' ? 'Next day' : 'Next month')}
          className="btn-shadcn btn-secondary"
          style={{
            height: '30px',
            width: '30px',
            padding: 0,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '6px',
            opacity: isNextDisabled ? 0.4 : 1,
            cursor: isNextDisabled ? 'not-allowed' : 'pointer'
          }}
        >
          <ChevronRight size={14} />
        </button>

        {/* [ Today | This Month ] Button */}
        <button
          type="button"
          id="btn-jump-current-period"
          onClick={handleJumpTodayOrThisMonth}
          disabled={period === 'day' ? selectedDate === todayVn : selectedMonth === thisMonthVn}
          className="btn-shadcn btn-secondary"
          style={{
            height: '30px',
            padding: '0 0.75rem',
            fontSize: '0.75rem',
            fontWeight: 600,
            borderRadius: '6px',
            opacity: (period === 'day' ? selectedDate === todayVn : selectedMonth === thisMonthVn) ? 0.6 : 1,
            cursor: (period === 'day' ? selectedDate === todayVn : selectedMonth === thisMonthVn) ? 'default' : 'pointer'
          }}
        >
          {period === 'day' ? 'Today' : 'This Month'}
        </button>
      </div>

      {/* Viewing: ... */}
      <div style={{ fontSize: '0.8125rem', color: '#09090b', fontWeight: 600 }}>
        Viewing: <span style={{ color: '#2563eb' }}>{activeRangeLabel}</span>
      </div>
    </div>
  );
}

