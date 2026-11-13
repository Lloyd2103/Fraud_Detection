import React, { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import { useAlertsWs } from './hooks/useAlertsWs';
import { useHealth } from './hooks/useHealth';
import LoadingSplash from './components/LoadingSplash';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import PageHeader from './components/PageHeader';
import CommandPalette from './components/CommandPalette';
import LoginPage from './pages/Auth/LoginPage';
import RegisterPage from './pages/Auth/RegisterPage';
import ForgotPasswordPage from './pages/Auth/ForgotPasswordPage';
import {
  AlertQueuePage,
  InspectedVerdictsPage,
  TxDetailPage,
  ModelDashPage,
  FraudSummaryPage,
  AuditPage,
  LatencyPage,
  TeamRolesPage,
  DeltaConfigPage,
} from './router/routes.config';
import { ROLE_ALLOWED_TABS, ROLE_BADGE_STYLE, getDefaultTabForRole } from './constants/roles';
import { TAB_LABELS } from './constants/routes';
import { Sparkles, X, LayoutDashboard, Check, BarChart2, LineChart, History, Activity } from 'lucide-react';

export default function App() {
  const { user, loading, logout } = useAuth();
  const { summary } = useAlertsWs();
  const { checkPipelineHealth } = useHealth();

  const [authView, setAuthView] = useState('login');
  const [prefilledEmail, setPrefilledEmail] = useState('');
  const [selectedTxId, setSelectedTxId] = useState(null);
  const [returnTab, setReturnTab] = useState('alerts');
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandSearch, setCommandSearch] = useState('');
  const [toastMessage, setToastMessage] = useState(null);
  const [pipelineHealth, setPipelineHealth] = useState(null);

  const pendingAlertsCount = summary?.pending_count ?? 0;

  const [activeTab, setActiveTab] = useState(() => {
    const role = user?.role || 'auditor';
    const defaultTab = getDefaultTabForRole(role);
    const hash = window.location.hash.replace(/^#\/?/, '').trim();
    if (hash) {
      const allowed = ROLE_ALLOWED_TABS[role] || ROLE_ALLOWED_TABS.auditor;
      if (allowed.includes(hash)) return hash;
    }
    return defaultTab;
  });

  const changeTab = (tabKey) => {
    window.location.hash = `#${tabKey}`;
    setActiveTab(tabKey);
  };

  useEffect(() => {
    if (!user) return;
    const defaultTab = getDefaultTabForRole(user.role);
    const allowed = ROLE_ALLOWED_TABS[user.role] || ROLE_ALLOWED_TABS.auditor;

    const syncRoute = () => {
      const hash = window.location.hash.replace(/^#\/?/, '').trim();
      if (!hash) {
        window.location.replace(`#${defaultTab}`);
        setActiveTab(defaultTab);
      } else if (allowed.includes(hash)) {
        setActiveTab(hash);
      } else {
        window.location.replace(`#${defaultTab}`);
        setActiveTab(defaultTab);
      }
    };

    syncRoute();
    window.addEventListener('hashchange', syncRoute);
    return () => window.removeEventListener('hashchange', syncRoute);
  }, [user?.role, user?.id]);

  useEffect(() => {
    let isMounted = true;
    const fetchHealth = async () => {
      const data = await checkPipelineHealth();
      if (isMounted && data) setPipelineHealth(data);
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [checkPipelineHealth]);

  const formatAge = (sec) => {
    if (sec == null || isNaN(sec)) return '';
    if (sec < 60) return `${Math.floor(sec)}s ago`;
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return `${Math.floor(sec / 86400)}d ago`;
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setCommandOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (loading) return <LoadingSplash />;

  if (!user) {
    if (authView === 'login') {
      return (
        <LoginPage
          prefilledEmail={prefilledEmail}
          onGoRegister={(email) => {
            if (email) setPrefilledEmail(email);
            setAuthView('register');
          }}
          onGoForgotPassword={(email) => {
            if (email) setPrefilledEmail(email);
            setAuthView('forgot');
          }}
        />
      );
    }
    if (authView === 'register') {
      return (
        <RegisterPage
          defaultEmail={prefilledEmail}
          onGoLogin={(email) => {
            if (email) setPrefilledEmail(email);
            setAuthView('login');
          }}
        />
      );
    }
    if (authView === 'forgot') {
      return (
        <ForgotPasswordPage
          prefilledEmail={prefilledEmail}
          onGoLogin={(email) => {
            if (email) setPrefilledEmail(email);
            setAuthView('login');
          }}
        />
      );
    }
  }

  const handleSelectTx = (txId, sourceTab) => {
    setSelectedTxId(txId);
    setReturnTab(sourceTab || activeTab);
    changeTab('detail');
  };

  const userRole = user?.role || 'auditor';
  const allowedTabs = ROLE_ALLOWED_TABS[userRole] || ROLE_ALLOWED_TABS.auditor;

  const ALL_NAV_ITEMS = [
    { key: 'alerts', icon: LayoutDashboard, label: 'Alert Queue' },
    { key: 'inspected', icon: Check, label: 'Inspected Verdicts' },
    { key: 'fraud-summary', icon: BarChart2, label: 'Fraud Summary' },
    { key: 'models', icon: LineChart, label: 'Model Performance & Drift' },
    { key: 'audit', icon: History, label: 'Delta Time Travel & Audit' },
    { key: 'latency', icon: Activity, label: 'Latency Monitoring (SLA)' },
  ];
  const NAV_ITEMS = ALL_NAV_ITEMS.filter((item) => allowedTabs.includes(item.key));
  const filteredCommands = NAV_ITEMS.filter((item) =>
    item.label.toLowerCase().includes(commandSearch.toLowerCase()),
  );

  const roleStyle = ROLE_BADGE_STYLE[user.role] || ROLE_BADGE_STYLE.auditor;
  const currentTabLabel = TAB_LABELS[activeTab] || 'Dashboard';

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#fafafa',
      color: '#09090b',
      display: 'flex',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    }}>
      <Sidebar
        activeTab={activeTab}
        changeTab={changeTab}
        user={user}
        logout={logout}
        pendingAlertsCount={pendingAlertsCount}
        allowedTabs={allowedTabs}
      />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Header
          setCommandOpen={setCommandOpen}
          pipelineHealth={pipelineHealth}
          user={user}
          logout={logout}
          roleStyle={roleStyle}
        />

        {toastMessage && (
          <div style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            backgroundColor: '#09090b',
            color: '#ffffff',
            padding: '0.75rem 1.25rem',
            borderRadius: '8px',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.25)',
            fontSize: '0.8125rem',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: '0.65rem',
            border: '1px solid #27272a',
          }}>
            <Sparkles size={15} style={{ color: '#eab308' }} />
            <span>{toastMessage}</span>
            <button
              onClick={() => setToastMessage(null)}
              style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: '0 0 0 0.5rem' }}
            >
              <X size={13} />
            </button>
          </div>
        )}

        <PageHeader
          activeTab={activeTab}
          returnTab={returnTab}
          changeTab={changeTab}
          tabLabels={TAB_LABELS}
          currentTabLabel={currentTabLabel}
          pipelineHealth={pipelineHealth}
          formatAge={formatAge}
        />

        <main style={{ flex: 1, padding: '1rem 1.5rem 2rem 1.5rem' }}>
          {allowedTabs.includes(activeTab) ? (
            <React.Suspense fallback={
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '50vh' }}>
                <div style={{ width: '28px', height: '28px', border: '3px solid #e4e4e7', borderTopColor: '#09090b', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              </div>
            }>
              {activeTab === 'alerts' && <AlertQueuePage onSelectTx={(id) => handleSelectTx(id, 'alerts')} onSwitchTab={changeTab} />}
              {activeTab === 'inspected' && <InspectedVerdictsPage onSelectTx={(id) => handleSelectTx(id, 'inspected')} onSwitchTab={changeTab} />}
              {activeTab === 'detail' && (
                <TxDetailPage
                  transactionId={selectedTxId}
                  sourceTab={returnTab}
                  onBack={() => changeTab(returnTab || 'alerts')}
                />
              )}
              {activeTab === 'models' && <ModelDashPage />}
              {activeTab === 'fraud-summary' && <FraudSummaryPage />}
              {activeTab === 'audit' && <AuditPage />}
              {activeTab === 'latency' && <LatencyPage />}
              {activeTab === 'team' && <TeamRolesPage />}
              {activeTab === 'delta-config' && <DeltaConfigPage />}
            </React.Suspense>
          ) : null}
        </main>
      </div>

      <CommandPalette
        commandOpen={commandOpen}
        setCommandOpen={setCommandOpen}
        commandSearch={commandSearch}
        setCommandSearch={setCommandSearch}
        filteredCommands={filteredCommands}
        changeTab={changeTab}
      />
    </div>
  );
}
