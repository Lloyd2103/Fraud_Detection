import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useVerdicts } from '../../hooks/useVerdicts';
import { useAlertsWs } from '../../hooks/useAlertsWs';
import AlertTable from '../../components/AlertTable';
import TablePagination from '../../components/TablePagination';
import VerdictsPeriodPicker from './components/VerdictsPeriodPicker';
import VerdictsKpiCards from './components/VerdictsKpiCards';
import VerdictsBarChart from './components/VerdictsBarChart';
import InspectorBreakdownTable from './components/InspectorBreakdownTable';
import InspectedFilterBar from './components/InspectedFilterBar';
import InspectedHeader from './components/InspectedHeader';
import { format, parseISO, addDays, subDays, addMonths, subMonths } from 'date-fns';

function getVietnamToday() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(new Date());
}

function getVietnamMonth() {
  return getVietnamToday().slice(0, 7);
}

export default function InspectedVerdictsPage({ onSelectTx, onSwitchTab }) {
  const { user } = useAuth();
  const { getInspected, getStats } = useVerdicts();
  const { summary: wsSummary } = useAlertsWs();

  // Period filter states
  const [period, setPeriod] = useState('day');
  const [selectedDate, setSelectedDate] = useState(() => getVietnamToday());
  const [selectedMonth, setSelectedMonth] = useState(() => getVietnamMonth());
  const [pickerOpen, setPickerOpen] = useState(false);
  const [monthPickerYear, setMonthPickerYear] = useState(() => parseInt(getVietnamToday().slice(0, 4), 10));
  const pickerRef = useRef(null);

  // Verdict stats & inspected alerts data
  const [verdictStats, setVerdictStats] = useState(null);
  const [verdictStatsLoading, setVerdictStatsLoading] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(true);

  // Table filters & pagination
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(50);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChannel, setSelectedChannel] = useState('ALL');
  const [selectedAmountRange, setSelectedAmountRange] = useState('ALL');
  const [auditorScope, setAuditorScope] = useState('ALL');
  const [timeScope, setTimeScope] = useState('PERIOD');
  const [lastUpdatedTime, setLastUpdatedTime] = useState(null);

  const todayVn = useMemo(() => getVietnamToday(), []);
  const thisMonthVn = useMemo(() => getVietnamMonth(), []);

  // Close date picker when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (pickerRef.current && !pickerRef.current.contains(event.target)) {
        setPickerOpen(false);
      }
    }
    if (pickerOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [pickerOpen]);

  // Load stats
  const fetchStats = useCallback(async () => {
    if (!user) return;
    setVerdictStatsLoading(true);
    try {
      const params = { period };
      if (period === 'day') params.date = selectedDate;
      if (period === 'month') params.month = selectedMonth;
      const data = await getStats(params);
      setVerdictStats(data);
    } catch (err) {
      console.error('Failed to load verdict stats:', err);
    } finally {
      setVerdictStatsLoading(false);
    }
  }, [period, selectedDate, selectedMonth, user, getStats]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Load Inspected alerts table data
  const fetchTableData = useCallback(async () => {
    setLoading(true);
    const options = {
      page,
      limit,
      search: searchQuery.trim(),
      channel: selectedChannel,
      amountRange: selectedAmountRange,
      inspectorId: auditorScope === 'MINE' ? user?.id : null,
    };

    if (timeScope === 'PERIOD') {
      if (period === 'day' && selectedDate) {
        options.from = `${selectedDate}T00:00:00`;
        options.to = `${selectedDate}T23:59:59`;
      } else if (period === 'month' && selectedMonth) {
        options.from = `${selectedMonth}-01T00:00:00`;
        options.to = `${selectedMonth}-31T23:59:59`;
      }
    }

    try {
      const data = await getInspected(options);
      let list = data.data || [];
      let total = data.total || 0;

      // Client-side date guard: ensure records strictly match the selected Day/Month in Vietnam time
      if (timeScope === 'PERIOD') {
        if (period === 'day' && selectedDate) {
          list = list.filter((tx) => {
            const decTime = tx.decision_timestamp || tx.inspected_at || tx.timestamp;
            if (!decTime) return false;
            try {
              const d = new Date(decTime);
              const vnDate = new Intl.DateTimeFormat('en-CA', {
                timeZone: 'Asia/Ho_Chi_Minh',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
              }).format(d);
              return vnDate === selectedDate;
            } catch (_) {
              return false;
            }
          });
          total = list.length;
        } else if (period === 'month' && selectedMonth) {
          list = list.filter((tx) => {
            const decTime = tx.decision_timestamp || tx.inspected_at || tx.timestamp;
            if (!decTime) return false;
            try {
              const d = new Date(decTime);
              const vnMonth = new Intl.DateTimeFormat('en-CA', {
                timeZone: 'Asia/Ho_Chi_Minh',
                year: 'numeric',
                month: '2-digit',
              }).format(d).slice(0, 7);
              return vnMonth === selectedMonth;
            } catch (_) {
              return false;
            }
          });
          total = list.length;
        }
      }

      setAlerts(list);
      setTotalRecords(total);
      setLastUpdatedTime(new Date());
    } catch (err) {
      console.error('Failed to load inspected alerts:', err);
    } finally {
      setLoading(false);
    }
  }, [page, limit, searchQuery, selectedChannel, selectedAmountRange, auditorScope, timeScope, period, selectedDate, selectedMonth, user?.id, getInspected]);

  useEffect(() => {
    fetchTableData();
  }, [fetchTableData]);

  // Date navigation handlers
  const isNextDisabled = period === 'day' ? selectedDate >= todayVn : selectedMonth >= thisMonthVn;

  const handlePrev = () => {
    if (period === 'day') {
      const prev = subDays(parseISO(selectedDate), 1);
      setSelectedDate(format(prev, 'yyyy-MM-dd'));
    } else {
      const [y, m] = selectedMonth.split('-').map(Number);
      const prev = subMonths(new Date(y, m - 1, 1), 1);
      setSelectedMonth(format(prev, 'yyyy-MM'));
    }
  };

  const handleNext = () => {
    if (isNextDisabled) return;
    if (period === 'day') {
      const nxt = addDays(parseISO(selectedDate), 1);
      const nxtStr = format(nxt, 'yyyy-MM-dd');
      if (nxtStr <= todayVn) setSelectedDate(nxtStr);
    } else {
      const [y, m] = selectedMonth.split('-').map(Number);
      const nxt = addMonths(new Date(y, m - 1, 1), 1);
      const nxtStr = format(nxt, 'yyyy-MM');
      if (nxtStr <= thisMonthVn) setSelectedMonth(nxtStr);
    }
  };

  const handleJumpTodayOrThisMonth = () => {
    if (period === 'day') setSelectedDate(todayVn);
    else setSelectedMonth(thisMonthVn);
  };

  const activeRangeLabel = useMemo(() => {
    if (period === 'day') {
      const [y, m, d] = selectedDate.split('-');
      return `Day ${d}/${m}/${y}`;
    }
    const [y, m] = selectedMonth.split('-');
    return `Month ${m}/${y}`;
  }, [period, selectedDate, selectedMonth]);

  const valueDisplayStr = useMemo(() => {
    if (period === 'day') {
      const [y, m, d] = selectedDate.split('-');
      return `${d}/${m}/${y}`;
    }
    const [y, m] = selectedMonth.split('-');
    return `Month ${m}/${y}`;
  }, [period, selectedDate, selectedMonth]);

  const hasFilters = Boolean(searchQuery.trim() || selectedChannel !== 'ALL' || selectedAmountRange !== 'ALL' || auditorScope !== 'ALL');

  return (
    <div>
      {/* Period Picker Bar */}
      <VerdictsPeriodPicker
        period={period}
        setPeriod={setPeriod}
        selectedDate={selectedDate}
        setSelectedDate={setSelectedDate}
        selectedMonth={selectedMonth}
        setSelectedMonth={setSelectedMonth}
        pickerOpen={pickerOpen}
        setPickerOpen={setPickerOpen}
        pickerRef={pickerRef}
        todayVn={todayVn}
        thisMonthVn={thisMonthVn}
        monthPickerYear={monthPickerYear}
        setMonthPickerYear={setMonthPickerYear}
        isNextDisabled={isNextDisabled}
        handlePrev={handlePrev}
        handleNext={handleNext}
        handleJumpTodayOrThisMonth={handleJumpTodayOrThisMonth}
        valueDisplayStr={valueDisplayStr}
        activeRangeLabel={activeRangeLabel}
      />

      {/* KPI Cards */}
      <VerdictsKpiCards
        verdictStatsLoading={verdictStatsLoading}
        verdictStats={verdictStats}
        activeRangeLabel={activeRangeLabel}
      />

      {/* Bar Chart */}
      <VerdictsBarChart
        period={period}
        verdictStats={verdictStats}
        activeRangeLabel={activeRangeLabel}
        userRole={user?.role}
      />

      {/* Inspector Performance Table for Admin */}
      {user?.role === 'admin' && verdictStats?.per_inspector && (
        <InspectorBreakdownTable
          verdictStats={verdictStats}
          activeRangeLabel={activeRangeLabel}
          period={period}
          selectedDate={selectedDate}
          selectedMonth={selectedMonth}
        />
      )}

      {/* Main Table Card */}
      <div className="shadcn-card" style={{ overflow: 'hidden' }}>
        <InspectedHeader
          lastUpdatedTime={lastUpdatedTime}
          fetchTableData={fetchTableData}
          onSwitchTab={onSwitchTab}
          pendingCount={wsSummary?.pending_count}
          totalRecords={totalRecords}
        />

        <InspectedFilterBar
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          selectedChannel={selectedChannel}
          setSelectedChannel={setSelectedChannel}
          selectedAmountRange={selectedAmountRange}
          setSelectedAmountRange={setSelectedAmountRange}
          auditorScope={auditorScope}
          setAuditorScope={setAuditorScope}
          teamTotal={verdictStats?.team?.total}
          mineTotal={verdictStats?.mine?.total}
          timeScope={timeScope}
          setTimeScope={setTimeScope}
        />

        <div style={{ position: 'relative' }}>
          {loading && (
            <div style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: 'rgba(255,255,255,0.7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
            }}>
              <div style={{ width: '24px', height: '24px', border: '2px solid #e4e4e7', borderTopColor: '#09090b', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            </div>
          )}
          <AlertTable
            alerts={alerts}
            onSelectTx={onSelectTx}
            hasFilters={hasFilters}
            onResetFilters={() => {
              setSearchQuery('');
              setSelectedChannel('ALL');
              setSelectedAmountRange('ALL');
              setAuditorScope('ALL');
              setPage(1);
            }}
            isInspectedView={true}
          />
        </div>

        <TablePagination
          page={page}
          setPage={setPage}
          limit={limit}
          setLimit={setLimit}
          totalRecords={totalRecords}
          unit="inspected transactions"
        />
      </div>
    </div>
  );
}
