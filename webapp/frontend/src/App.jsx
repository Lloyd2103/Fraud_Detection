import React, { useState } from 'react';
import AlertQueuePage from './pages/AlertQueuePage';
import TxDetailPage from './pages/TxDetailPage';
import ModelDashPage from './pages/ModelDashPage';
import AuditPage from './pages/AuditPage';

export default function App() {
  const [activeTab, setActiveTab] = useState('alerts');
  const [selectedTxId, setSelectedTxId] = useState(null);

  const handleSelectTx = (txId) => {
    setSelectedTxId(txId);
    setActiveTab('detail');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0a0e17', color: '#f8fafc', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{ background: '#111827', borderBottom: '1px solid rgba(255,255,255,0.08)', padding: '0.75rem 2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.5rem' }}>🛡️</span>
          <div>
            <h1 style={{ fontSize: '1.1rem', fontWeight: 700 }}>FRAUD SENTINEL AI</h1>
            <p style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Lakehouse Delta Platform</p>
          </div>
        </div>

        <nav style={{ display: 'flex', gap: '0.5rem', background: '#0a0e17', padding: '0.25rem', borderRadius: '8px' }}>
          <button 
            onClick={() => setActiveTab('alerts')}
            style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: 'none', background: activeTab === 'alerts' ? '#3b82f6' : 'transparent', color: '#fff', cursor: 'pointer' }}
          >
            🚨 Alert Queue
          </button>
          <button 
            onClick={() => setActiveTab('detail')}
            style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: 'none', background: activeTab === 'detail' ? '#3b82f6' : 'transparent', color: '#fff', cursor: 'pointer' }}
          >
            🔍 Details & Inspection
          </button>
          <button 
            onClick={() => setActiveTab('models')}
            style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: 'none', background: activeTab === 'models' ? '#3b82f6' : 'transparent', color: '#fff', cursor: 'pointer' }}
          >
            📊 Model Performance
          </button>
          <button 
            onClick={() => setActiveTab('audit')}
            style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: 'none', background: activeTab === 'audit' ? '#3b82f6' : 'transparent', color: '#fff', cursor: 'pointer' }}
          >
            ⏳ Delta Time Travel
          </button>
        </nav>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '1.5rem 2rem', maxWidth: '1600px', width: '100%', margin: '0 auto' }}>
        {activeTab === 'alerts' && <AlertQueuePage onSelectTx={handleSelectTx} />}
        {activeTab === 'detail' && <TxDetailPage transactionId={selectedTxId} onBack={() => setActiveTab('alerts')} />}
        {activeTab === 'models' && <ModelDashPage />}
        {activeTab === 'audit' && <AuditPage />}
      </main>

      {/* Footer */}
      <footer style={{ background: '#111827', borderTop: '1px solid rgba(255,255,255,0.08)', padding: '0.8rem 2rem', fontSize: '0.75rem', color: '#64748b', display: 'flex', justifyContent: 'space-between' }}>
        <span>Big Data Capstone</span>
        <span>HDFS: labsoe-17:9000 • Spark 3.5 • Kafka: 192.168.80.200:9092</span>
      </footer>
    </div>
  );
}
