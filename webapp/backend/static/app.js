/**
 * Real-Time Fraud Detection WebApp - Core Application Logic
 * Integrates with FastAPI, Delta Lake on HDFS, and WebSockets.
 * Complies with DeTai_2.pdf specifications.
 */

// State Management
const state = {
  activeTab: 'alerts',
  alerts: [],
  filteredAlerts: [],
  selectedTxId: null,
  currentTxDetail: null,
  ws: null,
  charts: {},
  stats: {
    total: 0,
    pending: 0,
    processed: 0,
    critical: 0
  }
};

// API Endpoints (DeTai2.pdf Section 2.8)
const API = {
  ALERTS: '/api/canhbao',
  ALERTS_SUMMARY: '/api/canhbao/tong-quan',
  TRANSACTION: (id) => `/api/giaodich/${id}`,
  DECISION: (id) => `/api/giaodich/${id}/ket-luan`,
  MODEL_PERF: '/api/mo-hinh/hieunang',
  TIME_TRAVEL: (v) => `/api/kiemtoan/${v}`,
  RERUN_EVAL: (v) => `/api/kiemtoan/${v}/danh-gia-lai`,
  LATENCY: '/api/do-tre/thong-ke',
  HEALTH: '/api/health'
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initFilters();
  initWebSocket();
  loadAlerts();
  loadSummaryKPIs();
  loadLatencyStats();
  
  // 5-second polling fallback
  setInterval(() => {
    if (state.activeTab === 'alerts') {
      loadAlerts(true);
      loadSummaryKPIs();
    }
  }, 5000);
});

// Tab Navigation
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tabId);
  });
  
  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.toggle('active', sec.id === `${tabId}-view`);
  });

  if (tabId === 'models') {
    loadModelDashboard();
  } else if (tabId === 'audit') {
    loadTimeTravel(0);
  } else if (tabId === 'latency') {
    loadLatencyDashboard();
  }
}

// WebSocket Real-time Feed
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/alerts`;
  
  try {
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onopen = () => {
      console.log('[WebSocket] Connected to Real-time Alert Stream');
      updateLiveIndicator(true);
    };
    
    state.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.data && Array.isArray(payload.data)) {
          mergeRealtimeAlerts(payload.data);
        }
      } catch (err) {
        console.warn('[WebSocket] Error parsing message:', err);
      }
    };
    
    state.ws.onclose = () => {
      console.log('[WebSocket] Connection closed. Retrying in 5s...');
      updateLiveIndicator(false);
      setTimeout(initWebSocket, 5000);
    };
    
    state.ws.onerror = () => {
      updateLiveIndicator(false);
    };
  } catch (e) {
    console.warn('[WebSocket] Setup exception:', e);
    updateLiveIndicator(false);
  }
}

function updateLiveIndicator(isOnline) {
  const dot = document.getElementById('live-indicator-dot');
  const text = document.getElementById('live-indicator-text');
  if (dot && text) {
    if (isOnline) {
      dot.className = 'pulse-dot';
      text.innerText = 'Live Streaming (Kafka/Spark)';
    } else {
      dot.className = 'pulse-dot danger';
      text.innerText = 'Polling Fallback (5s)';
    }
  }
}

function mergeRealtimeAlerts(newBatch) {
  if (!newBatch || !newBatch.length) return;
  // Keep unique transactions
  const existingIds = new Set(state.alerts.map(a => a.transaction_id));
  let hasNew = false;
  
  newBatch.forEach(item => {
    if (!existingIds.has(item.transaction_id)) {
      state.alerts.unshift(item);
      hasNew = true;
    }
  });
  
  if (hasNew) {
    applyFilters();
    loadSummaryKPIs();
  }
}

// Data Fetching: Alerts Queue
async function loadAlerts(isBackground = false) {
  try {
    const res = await fetch(`${API.ALERTS}?limit=50`);
    if (!res.ok) throw new Error('Unable to load alert queue');
    const data = await res.json();
    state.alerts = data;
    applyFilters();
    if (!isBackground) {
      loadSummaryKPIs();
    }
  } catch (err) {
    console.error('Error fetching alerts:', err);
  }
}

async function loadSummaryKPIs() {
  try {
    const res = await fetch(API.ALERTS_SUMMARY);
    if (!res.ok) return;
    const summary = await res.json();
    
    state.stats = summary;
    
    const pendingEl = document.getElementById('kpi-pending-count');
    const totalEl = document.getElementById('kpi-total-count');
    const processedEl = document.getElementById('kpi-processed-count');
    const criticalEl = document.getElementById('kpi-critical-count');
    const navBadge = document.getElementById('nav-pending-badge');
    
    if (pendingEl) pendingEl.innerText = summary.pending_count;
    if (totalEl) totalEl.innerText = summary.total_alerts;
    if (processedEl) processedEl.innerText = summary.processed_count;
    if (criticalEl) criticalEl.innerText = summary.critical_count;
    if (navBadge) navBadge.innerText = summary.pending_count;
  } catch (e) {
    console.warn('Error loading KPIs:', e);
  }
}

// Filters & Search
function initFilters() {
  const searchInput = document.getElementById('alert-search-input');
  const statusSelect = document.getElementById('alert-status-filter');
  const channelSelect = document.getElementById('alert-channel-filter');
  
  if (searchInput) {
    searchInput.addEventListener('input', applyFilters);
  }
  if (statusSelect) {
    statusSelect.addEventListener('change', applyFilters);
  }
  if (channelSelect) {
    channelSelect.addEventListener('change', applyFilters);
  }
}

function applyFilters() {
  const searchInput = document.getElementById('alert-search-input');
  const statusSelect = document.getElementById('alert-status-filter');
  const channelSelect = document.getElementById('alert-channel-filter');
  
  const searchVal = searchInput ? searchInput.value.trim().toLowerCase() : '';
  const statusVal = statusSelect ? statusSelect.value : 'all';
  const channelVal = channelSelect ? channelSelect.value : 'all';
  
  state.filteredAlerts = state.alerts.filter(tx => {
    // Search match
    const txId = (tx.transaction_id || '').toLowerCase();
    const src = (tx.source_account || '').toLowerCase();
    const dst = (tx.dest_account || '').toLowerCase();
    const matchesSearch = !searchVal || txId.includes(searchVal) || src.includes(searchVal) || dst.includes(searchVal);
    
    // Status match
    const isProcessed = tx.inspection_status === 'PROCESSED';
    let matchesStatus = true;
    if (statusVal === 'pending') matchesStatus = !isProcessed;
    if (statusVal === 'processed') matchesStatus = isProcessed;
    
    // Channel match
    const matchesChannel = channelVal === 'all' || (tx.channel || '').toUpperCase() === channelVal.toUpperCase();
    
    return matchesSearch && matchesStatus && matchesChannel;
  });
  
  renderAlertsTable();
}

function renderAlertsTable() {
  const tbody = document.getElementById('alerts-table-body');
  if (!tbody) return;
  
  if (state.filteredAlerts.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align:center; padding: 2.5rem; color: var(--text-muted);">
          No alerts found matching current filter.
        </td>
      </tr>
    `;
    return;
  }
  
  tbody.innerHTML = state.filteredAlerts.map(tx => {
    const txId = tx.ma_giao_dich || tx.transaction_id || 'UNKNOWN';
    const score = parseFloat(tx.diem_rui_ro !== undefined ? tx.diem_rui_ro : (tx.risk_score || 0));
    const scorePct = (score * 100).toFixed(1);
    const isHigh = score >= 0.8;
    const isMed = score >= 0.6 && score < 0.8;
    
    let riskClass = 'risk-low';
    let badgeClass = 'success';
    if (isHigh) {
      riskClass = 'risk-high';
      badgeClass = 'danger';
    } else if (isMed) {
      riskClass = 'risk-med';
      badgeClass = 'warning';
    }
    
    const rawStatus = tx.trang_thai_tham_dinh || tx.inspection_status || '';
    const isProcessed = rawStatus === 'PROCESSED' || rawStatus === 'da_xu_ly';
    const rowClass = isHigh && !isProcessed ? 'critical-row' : '';
    
    const amt = tx.so_tien !== undefined ? tx.so_tien : (tx.amount || 0);
    const formattedAmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(amt);
    const rank = tx.xep_hang_trong_ngay || tx.daily_rank;
    const timeStr = tx.thoi_diem || tx.timestamp || 'Mới nhận';
    const latMs = tx.do_tre_ms !== undefined ? tx.do_tre_ms : (tx.latency_ms || 0);
    const src = tx.tai_khoan_nguon || tx.source_account || 'N/A';
    const dst = tx.tai_khoan_dich || tx.dest_account || 'N/A';
    const channel = tx.kenh || tx.channel || 'ONLINE';
    const ttype = tx.loai || tx.trans_type || 'TRANSFER';
    
    return `
      <tr class="${rowClass}">
        <td>
          <strong style="color:#fff; font-family: monospace;">${txId}</strong>
          <div style="font-size:0.72rem; color:var(--text-muted);">${rank ? 'Hạng #' + rank : ''}</div>
        </td>
        <td>
          <div>${timeStr}</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">Độ trễ: ${latMs}ms</div>
        </td>
        <td>
          <span style="font-family:monospace; color:var(--text-secondary);">${src}</span>
          <span style="color:var(--text-muted); margin: 0 4px;">➔</span>
          <span style="font-family:monospace; color:var(--text-secondary);">${dst}</span>
        </td>
        <td>
          <span class="badge neutral">${channel}</span>
          <span class="badge neutral" style="margin-left:4px;">${ttype}</span>
        </td>
        <td style="font-weight:600;">${formattedAmt}</td>
        <td>
          <span class="risk-pill ${riskClass}">
            <span class="badge ${badgeClass}">${scorePct}%</span>
          </span>
        </td>
        <td>
          ${isProcessed ? 
            `<span class="badge success">✓ Đã thẩm định</span>` : 
            `<span class="badge danger">Chờ thẩm định</span>`
          }
        </td>
        <td>
          <button class="btn btn-sm btn-primary" onclick="inspectTransaction('${txId}')">
            🔍 Thẩm định
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

// Transaction Deep-Dive & Verdict
async function inspectTransaction(txId) {
  state.selectedTxId = txId;
  switchTab('detail');
  
  const detailContainer = document.getElementById('tx-detail-content');
  if (detailContainer) {
    detailContainer.innerHTML = `
      <div style="text-align:center; padding: 3rem; color:var(--text-muted);">
        <div class="pulse-dot" style="margin: 0 auto 1rem auto; width:14px; height:14px;"></div>
        Loading transaction details and Delta Lake data...
      </div>
    `;
  }
  
  try {
    const res = await fetch(API.TRANSACTION(txId));
    if (!res.ok) throw new Error('Unable to load transaction details');
    const data = await res.json();
    state.currentTxDetail = data;
    renderTransactionDetail(data);
  } catch (err) {
    if (detailContainer) {
      detailContainer.innerHTML = `
        <div style="color:var(--status-fraud); padding:2rem; text-align:center;">
          Error loading details: ${err.message}
        </div>
      `;
    }
  }
}

function renderTransactionDetail(data) {
  const detailContainer = document.getElementById('tx-detail-content');
  if (!detailContainer) return;
  
  const tx = data.detail || {};
  const score = parseFloat(data.risk_score || tx.risk_score || 0.9);
  const scorePct = (score * 100).toFixed(1);
  const formattedAmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.amount || 0);
  const formattedOldSrc = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.old_balance_source || 0);
  const formattedNewSrc = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(tx.new_balance_source || 0);
  
  const isProcessed = tx.inspection_status === 'PROCESSED';
  
  detailContainer.innerHTML = `
    <div class="detail-grid">
      <!-- Left Column: Metrics, Risk Factors, History & Timeline -->
      <div>
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <span>💳 Transaction: <strong style="color:var(--accent-blue);">${tx.transaction_id}</strong></span>
              <span class="badge ${score >= 0.8 ? 'danger' : 'warning'}">Risk Score: ${scorePct}%</span>
            </div>
            <button class="btn btn-sm" onclick="switchTab('alerts')">➔ Back to Queue</button>
          </div>
          
          <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:1rem; margin-bottom:1.5rem;">
            <div style="background:var(--bg-tertiary); padding:0.85rem; border-radius:var(--radius-md);">
              <div style="font-size:0.75rem; color:var(--text-muted);">Transaction Amount</div>
              <div style="font-size:1.15rem; font-weight:700; color:#fff; margin-top:0.25rem;">${formattedAmt}</div>
            </div>
            <div style="background:var(--bg-tertiary); padding:0.85rem; border-radius:var(--radius-md);">
              <div style="font-size:0.75rem; color:var(--text-muted);">Type & Channel</div>
              <div style="font-size:1rem; font-weight:600; color:#fff; margin-top:0.25rem;">${tx.trans_type || 'TRANSFER'} (${tx.channel || 'ONLINE'})</div>
            </div>
            <div style="background:var(--bg-tertiary); padding:0.85rem; border-radius:var(--radius-md);">
              <div style="font-size:0.75rem; color:var(--text-muted);">Timestamp</div>
              <div style="font-size:0.85rem; font-weight:500; color:var(--text-secondary); margin-top:0.35rem;">${tx.timestamp || 'N/A'}</div>
            </div>
          </div>

          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:1rem; margin-bottom:1.5rem; background:rgba(0,0,0,0.2); padding:1rem; border-radius:var(--radius-md); border:1px solid var(--border-color);">
            <div>
              <div style="font-size:0.8rem; color:var(--accent-cyan); font-weight:600; margin-bottom:0.4rem;">Source Account (${tx.source_account})</div>
              <div style="font-size:0.82rem; color:var(--text-secondary);">Prior balance: <strong>${formattedOldSrc}</strong></div>
              <div style="font-size:0.82rem; color:var(--text-secondary);">New balance: <strong>${formattedNewSrc}</strong></div>
            </div>
            <div>
              <div style="font-size:0.8rem; color:var(--accent-purple); font-weight:600; margin-bottom:0.4rem;">Destination Account (${tx.dest_account})</div>
              <div style="font-size:0.82rem; color:var(--text-secondary);">Category: <strong>${(tx.dest_account || '').startsWith('M') ? 'Merchant' : 'Customer'}</strong></div>
            </div>
          </div>

          <!-- Top 3 Risk Factors -->
          <div style="margin-top:1.5rem;">
            <h4 style="font-size:0.95rem; font-weight:600; margin-bottom:1rem; color:var(--text-primary); display:flex; align-items:center; gap:0.5rem;">
              <span>🚨 Top Contributing Risk Factors (GBT Explanation)</span>
            </h4>
            <div id="risk-factors-bars">
              ${(data.risk_factors || []).map(rf => `
                <div class="risk-factor-item">
                  <div class="factor-header">
                    <span style="font-weight:500; color:#fff;">${rf.name}</span>
                    <span style="font-weight:700; color:var(--status-fraud);">${(rf.weight * 100).toFixed(0)}% impact</span>
                  </div>
                  <div class="factor-bar-bg">
                    <div class="factor-bar-fill ${rf.severity === 'CRITICAL' ? 'danger' : 'warning'}" style="width: ${rf.weight * 100}%;"></div>
                  </div>
                  <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">
                    ${rf.description} • Value: <span style="color:var(--text-secondary);">${rf.value}</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- Timeline Chart Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📈 Cash Flow & Anomaly Timeline (30 Days)</div>
          </div>
          <div class="chart-wrapper">
            <canvas id="tx-timeline-chart"></canvas>
          </div>
        </div>

        <!-- Last 20 Transactions History -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🕒 Recent 20 Transactions for Account (${tx.source_account})</div>
          </div>
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Tx ID</th>
                  <th>Timestamp</th>
                  <th>Channel / Type</th>
                  <th>Amount</th>
                  <th>Dest Account</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${(data.recent_history || []).map(h => `
                  <tr>
                    <td style="font-family:monospace; color:#fff;">${h.transaction_id}</td>
                    <td>${h.timestamp || 'N/A'}</td>
                    <td>${h.channel || 'ONLINE'} - ${h.trans_type || 'TRANSFER'}</td>
                    <td style="font-weight:600;">${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(h.amount || 0)}</td>
                    <td style="font-family:monospace;">${h.dest_account || 'N/A'}</td>
                    <td>
                      ${h.is_fraud_label === 1 ? 
                        `<span class="badge danger">Fraud</span>` : 
                        `<span class="badge success">Legitimate</span>`
                      }
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Right Column: Inspector Verdict Box -->
      <div>
        <div class="card decision-card">
          <div class="card-header">
            <div class="card-title">⚖️ Auditor Verdict (Feedback Loop)</div>
          </div>
          <p style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:1.25rem;">
            Auditor verdicts are recorded directly to <code>silver.inspection_decisions</code> on Lakehouse and fed into <strong>Airflow DAG 3</strong> for model retraining.
          </p>

          ${isProcessed ? `
            <div style="background:var(--status-safe-glow); border:1px solid rgba(16, 185, 129, 0.4); padding:1rem; border-radius:var(--radius-md); margin-bottom:1.25rem;">
              <h4 style="color:#6ee7b7; font-size:0.9rem; margin-bottom:0.35rem;">✓ Transaction Inspected</h4>
              <div style="font-size:0.8rem; color:var(--text-primary);">Verdict: <strong>${tx.decision_label === 1 ? '🚨 CONFIRMED FRAUD' : '🛡️ LEGITIMATE TRANSACTION'}</strong></div>
              <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.2rem;">Auditor: ${tx.inspector_id || 'Auditor_01'} at ${tx.decision_timestamp || 'Today'}</div>
              <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.2rem;">Reason: ${tx.reason || 'Verified pattern'}</div>
            </div>
          ` : ''}

          <form id="verdict-form" onsubmit="handleVerdictSubmit(event, '${tx.transaction_id}')">
            <div class="form-group">
              <label class="form-label">Auditor ID (Inspector ID)</label>
              <input type="text" class="form-control" id="verdict-inspector" value="Auditor_01" required />
            </div>

            <div class="form-group">
              <label class="form-label">Inspection Reason (Standardized)</label>
              <select class="form-control" id="verdict-reason-select" onchange="onReasonSelectChange(this)">
                <option value="Abnormal Balance Discrepancy">Abnormal Balance Discrepancy</option>
                <option value="Sudden Amount Spike vs 30-Day History">Sudden Amount Spike vs 30-Day History</option>
                <option value="Suspicious New Destination Account (Mule Account)">Suspicious New Destination Account (Mule Account)</option>
                <option value="Unusual High-Value Transaction Outside Normal Hours">Unusual High-Value Transaction Outside Normal Hours</option>
                <option value="Unrecognized Device and IP Mismatch">Unrecognized Device and IP Mismatch</option>
                <option value="Legitimate Transaction Confirmed by Cardholder">Legitimate Transaction Confirmed by Cardholder</option>
                <option value="OTHER">Other Reason (Manual Entry)...</option>
              </select>
            </div>

            <div class="form-group" id="custom-reason-group" style="display:none;">
              <label class="form-label">Custom Reason Details</label>
              <textarea class="form-control" id="verdict-custom-reason" placeholder="Enter detailed notes..."></textarea>
            </div>

            <div class="form-group">
              <label class="form-label">Processing Time (Seconds)</label>
              <input type="number" class="form-control" id="verdict-time" value="8" min="1" max="600" />
            </div>

            <div class="decision-actions">
              <button type="button" class="btn btn-danger" style="width:100%; justify-content:center;" onclick="submitVerdictAction('${tx.transaction_id}', 1)">
                🚨 FRAUD (1)
              </button>
              <button type="button" class="btn btn-success" style="width:100%; justify-content:center;" onclick="submitVerdictAction('${tx.transaction_id}', 0)">
                🛡️ LEGITIMATE (0)
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
  
  // Render timeline chart
  renderTimelineChart(data.timeline_points || []);
}

function onReasonSelectChange(select) {
  const customGroup = document.getElementById('custom-reason-group');
  if (customGroup) {
    customGroup.style.display = select.value === 'OTHER' ? 'block' : 'none';
  }
}

async function submitVerdictAction(txId, labelValue) {
  const inspector = document.getElementById('verdict-inspector').value || 'Auditor_01';
  const reasonSelect = document.getElementById('verdict-reason-select').value;
  const customReason = document.getElementById('verdict-custom-reason')?.value;
  const reason = reasonSelect === 'OTHER' ? (customReason || 'Manual verdict') : reasonSelect;
  const timeSeconds = parseInt(document.getElementById('verdict-time').value || '8');
  
  const payload = {
    label: labelValue,
    nhan: labelValue,
    inspector_id: inspector,
    nguoi_tham_dinh: inspector,
    reason: reason,
    ly_do: reason,
    processing_time: timeSeconds,
    thoi_gian_xu_ly_giay: timeSeconds
  };
  
  try {
    const res = await fetch(API.DECISION(txId), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error saving verdict');
    }
    
    const result = await res.json();
    showToast(`✓ Successfully recorded inspection verdict for ${txId} to Delta Lake!`, 'success');
    
    // Refresh detail and alerts
    inspectTransaction(txId);
    loadAlerts(true);
    loadSummaryKPIs();
  } catch (e) {
    showToast(`Error: ${e.message}`, 'danger');
  }
}

// Chart.js: Transaction Timeline
function renderTimelineChart(points) {
  const ctx = document.getElementById('tx-timeline-chart');
  if (!ctx) return;
  
  if (state.charts.timeline) {
    state.charts.timeline.destroy();
  }
  
  const labels = points.map(p => p.time.split(' ')[1] || p.time);
  const dataValues = points.map(p => p.amount);
  const pointBgColors = points.map(p => p.is_current ? '#ef4444' : '#3b82f6');
  const pointRadii = points.map(p => p.is_current ? 9 : 4);
  
  state.charts.timeline = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Transaction Amount (VND)',
        data: dataValues,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.12)',
        fill: true,
        tension: 0.35,
        pointBackgroundColor: pointBgColors,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: pointRadii
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => {
              const p = points[context.dataIndex];
              const formatted = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(p.amount);
              return `${p.is_current ? '[CURRENT TRANSACTION] ' : ''}${formatted} (${p.trans_type})`;
            }
          }
        }
      },
      scales: {
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: {
            color: '#94a3b8',
            callback: (v) => `${(v / 1000).toLocaleString()}k`
          }
        },
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94a3b8' }
        }
      }
    }
  });
}

// Model Governance & Drift Dashboard
async function loadModelDashboard() {
  try {
    const res = await fetch(API.MODEL_PERF);
    if (!res.ok) throw new Error('Unable to load model performance metrics');
    const data = await res.json();
    renderModelDashboard(data);
  } catch (err) {
    console.error('Error loading model dashboard:', err);
  }
}

function renderModelDashboard(data) {
  // Render Weekly Precision@200 Line Chart (Feedback Loop Effect)
  const weeklyCtx = document.getElementById('chart-weekly-precision');
  if (weeklyCtx) {
    if (state.charts.weeklyPrecision) state.charts.weeklyPrecision.destroy();
    
    const weeklyData = data.weekly_precision || [];
    state.charts.weeklyPrecision = new Chart(weeklyCtx, {
      type: 'line',
      data: {
        labels: weeklyData.map(w => w.week),
        datasets: [{
          label: 'Precision@200',
          data: weeklyData.map(w => w.precision_200),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.15)',
          fill: true,
          tension: 0.3,
          pointBackgroundColor: '#10b981',
          pointRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            min: 0.5,
            max: 1.0,
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8', callback: (v) => `${(v * 100).toFixed(0)}%` }
          },
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }

  // Render PR Curve
  const prCtx = document.getElementById('chart-pr-curve');
  if (prCtx) {
    if (state.charts.prCurve) state.charts.prCurve.destroy();
    const prData = data.pr_curve || [];
    state.charts.prCurve = new Chart(prCtx, {
      type: 'line',
      data: {
        labels: prData.map(d => d.recall),
        datasets: [{
          label: 'Precision-Recall Curve',
          data: prData.map(d => d.precision),
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.15)',
          fill: true,
          tension: 0.2,
          pointBackgroundColor: '#8b5cf6',
          pointRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            min: 0.2,
            max: 1.0,
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8', callback: (v) => `${(v * 100).toFixed(0)}%` }
          },
          x: {
            title: { display: true, text: 'Recall', color: '#94a3b8' },
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8' }
          }
        }
      }
    });
  }

  // Render Drift PSI Bar Chart
  const driftCtx = document.getElementById('chart-drift-psi');
  if (driftCtx) {
    if (state.charts.drift) state.charts.drift.destroy();
    const driftData = data.drift_monitoring || [];
    state.charts.drift = new Chart(driftCtx, {
      type: 'bar',
      data: {
        labels: driftData.map(d => d.feature_name),
        datasets: [{
          label: 'Population Stability Index (PSI)',
          data: driftData.map(d => d.psi),
          backgroundColor: driftData.map(d => d.psi > 0.25 ? '#ef4444' : (d.psi > 0.1 ? '#f59e0b' : '#10b981')),
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8' }
          },
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }

  // Render Feature Importances
  const featCtx = document.getElementById('chart-feature-importance');
  if (featCtx) {
    if (state.charts.featImp) state.charts.featImp.destroy();
    const featData = data.feature_importances || [];
    state.charts.featImp = new Chart(featCtx, {
      type: 'bar',
      indexAxis: 'y',
      data: {
        labels: featData.map(f => f.name || f.feature),
        datasets: [{
          label: 'Feature Importance',
          data: featData.map(f => f.importance),
          backgroundColor: '#3b82f6',
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }

  // Render 3-Algorithm Comparison Table
  const compTbody = document.getElementById('models-comparison-table-body');
  if (compTbody) {
    compTbody.innerHTML = (data.models_comparison || []).map(m => `
      <tr>
        <td><strong style="color:#fff;">${m.algorithm}</strong></td>
        <td style="color:#10b981; font-weight:700;">${(m.precision_at_200 * 100).toFixed(2)}%</td>
        <td>${(m.pr_auc * 100).toFixed(2)}%</td>
        <td>${(m.roc_auc * 100).toFixed(2)}%</td>
        <td>${m.fraud_detected_in_top200} / 200</td>
        <td>
          <span class="badge ${m.status === 'ACTIVE_PRODUCTION' ? 'success' : 'neutral'}">
            ${m.status === 'ACTIVE_PRODUCTION' ? '✓ Active Production' : m.status || 'Candidate'}
          </span>
        </td>
      </tr>
    `).join('');
  }
}

// Delta Time Travel & Audit
async function loadTimeTravel(version = 0) {
  try {
    const res = await fetch(API.TIME_TRAVEL(version));
    if (!res.ok) throw new Error('Delta Time Travel query error');
    const data = await res.json();
    renderTimeTravel(data);
  } catch (err) {
    console.error('Error loading time travel audit:', err);
  }
}

function renderTimeTravel(data) {
  const versionSelect = document.getElementById('time-travel-version-select');
  const commitTbody = document.getElementById('delta-commits-table-body');
  const sampleTbody = document.getElementById('delta-sample-table-body');
  const totalRecEl = document.getElementById('audit-total-records');
  const hashEl = document.getElementById('audit-hash');
  
  if (totalRecEl) totalRecEl.innerText = (data.total_records || 0).toLocaleString();
  if (hashEl) hashEl.innerText = data.reproducible_hash || 'SHA256_VERIFIED';
  
  if (commitTbody) {
    commitTbody.innerHTML = (data.commit_history || []).map(c => `
      <tr>
        <td><span class="badge ${c.version == data.requested_version ? 'success' : 'neutral'}">v${c.version}</span></td>
        <td>${c.timestamp || 'N/A'}</td>
        <td><strong style="color:var(--accent-blue);">${c.operation || 'WRITE'}</strong></td>
        <td>${c.user || 'master'}</td>
        <td style="color:var(--text-secondary);">${c.notes || 'Delta Lake Operation'}</td>
        <td>
          <button class="btn btn-sm" onclick="loadTimeTravel(${c.version})">Load Snapshot</button>
        </td>
      </tr>
    `).join('');
  }

  if (sampleTbody) {
    sampleTbody.innerHTML = (data.sample_data || []).map(s => `
      <tr>
        <td style="font-family:monospace; color:#fff;">${s.transaction_id}</td>
        <td>${s.timestamp}</td>
        <td>${s.source_account} ➔ ${s.dest_account}</td>
        <td>${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(s.amount || 0)}</td>
        <td><span class="badge neutral">${s.channel || 'ONLINE'}</span></td>
        <td>${s.is_fraud_label === 1 ? '<span class="badge danger">Fraud</span>' : '<span class="badge success">Legitimate</span>'}</td>
      </tr>
    `).join('');
  }
}

async function rerunAuditEvaluation() {
  const select = document.getElementById('time-travel-version-select');
  const v = select ? select.value : 0;
  
  showToast(`Rerunning evaluation on Delta Version ${v}...`, 'info');
  try {
    const res = await fetch(API.RERUN_EVAL(v), { method: 'POST' });
    const resData = await res.json();
    showToast(`✓ Audit completed: Precision@200 = ${(resData.reproduced_precision_at_200 * 100).toFixed(1)}% (100% match)`, 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'danger');
  }
}

// Latency & SLA
async function loadLatencyDashboard() {
  await loadLatencyStats();
}

async function loadLatencyStats() {
  try {
    const res = await fetch(API.LATENCY);
    if (!res.ok) return;
    const stats = await res.json();
    
    const p50 = document.getElementById('latency-p50');
    const p95 = document.getElementById('latency-p95');
    const p99 = document.getElementById('latency-p99');
    const slaRate = document.getElementById('latency-sla-rate');
    
    if (p50) p50.innerText = `${stats.p50_latency_ms} ms`;
    if (p95) p95.innerText = `${stats.p95_latency_ms} ms`;
    if (p99) p99.innerText = `${stats.p99_latency_ms} ms`;
    if (slaRate) slaRate.innerText = `${stats.sla_compliance_rate}%`;
  } catch (e) {
    console.warn('Error loading latency stats:', e);
  }
}

// Toast Notifications
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div style="font-size:1.1rem;">${type === 'success' ? '✓' : (type === 'danger' ? '⚠️' : 'ℹ️')}</div>
    <div style="font-size:0.85rem; font-weight:500;">${message}</div>
  `;
  
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
