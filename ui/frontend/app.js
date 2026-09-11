// Human-in-the-Loop Fraud Review Console Frontend JS Logic
const API_BASE = `${window.location.protocol}//${window.location.host}/api`;

let selectedTxId = null;
let inspectionTimer = null;
let timerSeconds = 0;
let autoRefreshInterval = null;
let isAutoRefresh = true;

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

function initApp() {
    checkApiHealth();
    fetchPendingAlerts();

    // Event listeners
    document.getElementById("btnAutoRefresh").addEventListener("click", toggleAutoRefresh);
    document.getElementById("searchInput").addEventListener("input", filterAlerts);

    // Auto refresh queue every 5s
    startAutoRefresh();
}

// 1. API Connectivity Health Check
async function checkApiHealth() {
    const badge = document.getElementById("apiStatusBadge");
    const text = document.getElementById("apiStatusText");
    const dot = badge.querySelector(".status-dot");

    try {
        const res = await fetch(`${window.location.protocol}//${window.location.host}/health`);
        if (res.ok) {
            dot.className = "status-dot online";
            text.textContent = `API Connected (${window.location.host})`;
        } else {
            throw new Error("API status non-200");
        }
    } catch (err) {
        dot.className = "status-dot offline";
        text.textContent = "API Disconnected";
    }
}

// 2. Fetch Pending Alerts Queue
async function fetchPendingAlerts() {
    try {
        const response = await fetch(`${API_BASE}/alerts?status=PENDING&limit=50`);
        if (!response.ok) throw new Error("Failed to fetch alerts");

        const alerts = await response.json();
        renderAlertsList(alerts);
    } catch (err) {
        console.error("Error fetching alerts:", err);
    }
}

// Render Alerts List
function renderAlertsList(alerts) {
    const listContainer = document.getElementById("alertsList");
    const pendingCount = document.getElementById("pendingCount");

    pendingCount.textContent = `${alerts.length} Pending`;

    if (!alerts || alerts.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-state">
                <p>🎉 No pending fraud alerts in queue.</p>
            </div>`;
        return;
    }

    listContainer.innerHTML = alerts.map(item => `
        <div class="alert-item ${selectedTxId === item.transaction_id ? 'selected' : ''}" 
             onclick="selectTransaction('${item.transaction_id}')">
            <div class="alert-item-header">
                <span class="tx-id">${item.transaction_id}</span>
                <span class="score-badge high">${item.risk_score.toFixed(1)}% RISK</span>
            </div>
            <div class="alert-item-body">
                <span>Model: ${item.model_version || 'GBT_v1.0'}</span>
                <span>Latency: ${item.latency_ms || 120}ms</span>
            </div>
        </div>
    `).join('');
}

// Filter alerts by search term
function filterAlerts() {
    const query = document.getElementById("searchInput").value.toLowerCase();
    const items = document.querySelectorAll(".alert-item");

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(query) ? "block" : "none";
    });
}

// 3. Select Transaction & Load Deep Inspection Details
async function selectTransaction(txId) {
    selectedTxId = txId;
    
    // Highlight active alert card
    document.querySelectorAll(".alert-item").forEach(el => el.classList.remove("selected"));
    const selectedEl = Array.from(document.querySelectorAll(".alert-item"))
        .find(el => el.querySelector(".tx-id").textContent === txId);
    if (selectedEl) selectedEl.classList.add("selected");

    // Toggle Workspace UI
    document.getElementById("noSelectionState").classList.add("hidden");
    document.getElementById("inspectionWorkspace").classList.remove("hidden");
    document.getElementById("activeTxBadge").classList.remove("hidden");
    document.getElementById("activeTxBadge").textContent = `INSPECTING: ${txId}`;

    // Reset feedback alert banner
    hideSubmissionAlert();

    // Start timer
    resetInspectionTimer();

    try {
        const res = await fetch(`${API_BASE}/transactions/${txId}`);
        if (!res.ok) throw new Error("Transaction details not found");

        const data = await res.json();
        renderTransactionDetails(data);
    } catch (err) {
        console.error("Error loading transaction details:", err);
    }
}

// Render Transaction Details
function renderTransactionDetails(data) {
    document.getElementById("detailRiskScore").textContent = `${data.risk_score.toFixed(1)}%`;
    
    const formattedAmount = data.amount 
        ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(data.amount)
        : "N/A";
    document.getElementById("detailAmount").textContent = formattedAmount;

    document.getElementById("detailTypeChannel").textContent = `${data.trans_type || 'TRANSFER'} • ${data.channel || 'ONLINE'}`;
    document.getElementById("detailModelLatency").textContent = `${data.model_version || 'GBT_v1.0'} (${data.latency_ms || 120} ms)`;

    document.getElementById("detailSrcAcc").textContent = data.source_account || "N/A";
    document.getElementById("detailDstAcc").textContent = data.dest_account || "N/A";

    // Render XAI Risk Factors Progress Bars
    const factorsContainer = document.getElementById("riskFactorsContainer");
    if (!data.top_risk_factors || data.top_risk_factors.length === 0) {
        factorsContainer.innerHTML = `<p class="text-muted">No specific risk contribution factors recorded.</p>`;
    } else {
        factorsContainer.innerHTML = data.top_risk_factors.map(factor => {
            const pct = Math.min(Math.max(factor.contribution * 100, 10), 100).toFixed(0);
            return `
                <div class="risk-factor-row">
                    <div class="factor-info">
                        <span class="factor-name">${factor.name}</span>
                        <span>Contribution: ${factor.contribution.toFixed(4)}</span>
                    </div>
                    <div class="factor-bar-bg">
                        <div class="factor-bar-fill" style="width: ${pct}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }
}

// 4. Submit Auditor Verdict (Feedback Loop Action)
async function submitVerdict(decisionLabel) {
    if (!selectedTxId) return;

    const auditor = document.getElementById("auditorInput").value.trim() || "auditor_admin";
    const reason = document.getElementById("reasonInput").value;

    const payload = {
        decision: decisionLabel,
        auditor: auditor,
        reason: reason,
        handling_time_seconds: timerSeconds
    };

    try {
        const res = await fetch(`${API_BASE}/transactions/${selectedTxId}/verdict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Failed to submit verdict");
        }

        const result = await res.json();
        
        // Show success alert
        const verdictText = decisionLabel === 1 ? "🚨 CONFIRMED FRAUD" : "✅ CLEARED LEGITIMATE";
        showSubmissionAlert(`Success! Transaction ${selectedTxId} registered as ${verdictText}. Feedback written to silver.inspection_decisions.`, "success");

        // Add to History Table
        addHistoryRow(selectedTxId, decisionLabel, auditor, reason, timerSeconds);

        // Refresh Pending Queue
        fetchPendingAlerts();

        // Reset workspace selection
        setTimeout(() => {
            document.getElementById("noSelectionState").classList.remove("hidden");
            document.getElementById("inspectionWorkspace").classList.add("hidden");
            document.getElementById("activeTxBadge").classList.add("hidden");
            selectedTxId = null;
        }, 1500);

    } catch (err) {
        showSubmissionAlert(`Error submitting verdict: ${err.message}`, "error");
    }
}

// Timer Functions
function resetInspectionTimer() {
    clearInterval(inspectionTimer);
    timerSeconds = 0;
    updateTimerDisplay();

    inspectionTimer = setInterval(() => {
        timerSeconds++;
        updateTimerDisplay();
    }, 1000);
}

function updateTimerDisplay() {
    const mins = Math.floor(timerSeconds / 60).toString().padStart(2, '0');
    const secs = (timerSeconds % 60).toString().padStart(2, '0');
    document.getElementById("timerDisplay").textContent = `${mins}:${secs}`;
}

function showSubmissionAlert(msg, type) {
    const box = document.getElementById("submissionAlert");
    box.className = `submission-alert ${type}`;
    box.textContent = msg;
    box.classList.remove("hidden");
}

function hideSubmissionAlert() {
    const box = document.getElementById("submissionAlert");
    box.classList.add("hidden");
}

// Add row to Feedback History Table
function addHistoryRow(txId, decision, auditor, reason, durationSec) {
    const tbody = document.getElementById("historyTableBody");
    const emptyRow = tbody.querySelector(".empty-row");
    if (emptyRow) emptyRow.remove();

    const verdictBadge = decision === 1 
        ? `<span class="badge-verdict-fraud">CONFIRMED FRAUD</span>`
        : `<span class="badge-verdict-legit">CLEARED LEGITIMATE</span>`;

    const nowStr = new Date().toLocaleTimeString();

    const row = document.createElement("tr");
    row.innerHTML = `
        <td class="mono">${txId}</td>
        <td>${verdictBadge}</td>
        <td>${auditor}</td>
        <td>${reason}</td>
        <td>${durationSec}s</td>
        <td class="text-muted">${nowStr}</td>
    `;

    tbody.insertBefore(row, tbody.firstChild);
}

// Auto Refresh Toggle
function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        if (isAutoRefresh) {
            fetchPendingAlerts();
            checkApiHealth();
        }
    }, 5000);
}

function toggleAutoRefresh() {
    isAutoRefresh = !isAutoRefresh;
    const btn = document.getElementById("btnAutoRefresh");
    if (isAutoRefresh) {
        btn.innerHTML = `<span class="pulse-icon">🔄</span> Auto Refresh (5s)`;
        btn.className = "btn btn-secondary btn-sm";
    } else {
        btn.innerHTML = `⏸️ Paused`;
        btn.className = "btn btn-secondary btn-sm opacity-50";
    }
}
