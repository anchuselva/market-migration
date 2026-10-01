/**
 * Nexus Exchange - Hybrid Cloud Migration Mission Control
 * Real-time SSE telemetry, interactive chaos injection, and parity auditing
 */

// State
let isStreaming = false;
let isChaosActive = false;
let isCutoverActive = false;
let eventSource = null;

// DOM Elements
const btnStreamToggle = document.getElementById('btn-stream-toggle');
const streamBtnLabel = document.getElementById('stream-btn-label');
const streamIcon = document.getElementById('stream-icon');

const btnChaosToggle = document.getElementById('btn-chaos-toggle');
const chaosBtnLabel = document.getElementById('chaos-btn-label');

const btnReconcile = document.getElementById('btn-reconcile');
const btnCutover = document.getElementById('btn-cutover');
const btnReset = document.getElementById('btn-reset');
const btnClearLog = document.getElementById('btn-clear-log');

const speedRange = document.getElementById('speed-range');
const speedVal = document.getElementById('speed-val');

// Top Badges
const brokerStatus = document.getElementById('broker-status');
const parityPill = document.getElementById('parity-pill');
const parityPillDot = document.getElementById('parity-pill-dot');
const parityPillText = document.getElementById('parity-pill-text');

// KPI Elements
const kpiLegacyCount = document.getElementById('kpi-legacy-count');
const kpiLegacyVol = document.getElementById('kpi-legacy-vol');
const kpiCloudCount = document.getElementById('kpi-cloud-count');
const kpiCloudVol = document.getElementById('kpi-cloud-vol');
const kpiDriftCount = document.getElementById('kpi-drift-count');
const kpiVolDiff = document.getElementById('kpi-vol-diff');
const kpiTps = document.getElementById('kpi-tps');
const driftStatusBadge = document.getElementById('drift-status-badge');
const cloudBadgeStatus = document.getElementById('cloud-badge-status');

// Topology Elements
const topoProducerRate = document.getElementById('topo-producer-rate');
const topoLegacyCount = document.getElementById('topo-legacy-count');
const topoCloudCount = document.getElementById('topo-cloud-count');
const topoCloudNode = document.getElementById('topo-cloud-node');
const topoAuditorNode = document.getElementById('topo-auditor-node');
const topoAuditorDrift = document.getElementById('topo-auditor-drift');
const cloudForkLeg = document.getElementById('cloud-fork-leg');
const cloudNodeBadge = document.getElementById('cloud-node-badge');
const topologyStatusText = document.getElementById('topology-status-text');

// Feed & Console Elements
const tradeTbody = document.getElementById('trade-tbody');
const auditConsole = document.getElementById('audit-console');

// Migrated Core Workload Elements
const repExecutions = document.getElementById('rep-executions');
const repVolume = document.getElementById('rep-volume');
const repAvg = document.getElementById('rep-avg');
const btnExportEod = document.getElementById('btn-export-eod');

// Formatters
const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

const numberFormatter = new Intl.NumberFormat('en-US');

// Initialize SSE Telemetry Stream
function initSSE() {
  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource('/api/events');

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleTelemetryUpdate(data);
    } catch (e) {
      console.error('Error parsing SSE event:', e);
    }
  };

  eventSource.onerror = () => {
    console.warn('SSE connection disconnected. Falling back to status polling.');
    setTimeout(pollStatusFallback, 1500);
  };
}

async function pollStatusFallback() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    handleTelemetryUpdate(data);
  } catch (e) {
    console.error('Status fetch failed:', e);
  }
}

// Handle Incoming Server Telemetry
function handleTelemetryUpdate(data) {
  // Sync state
  isStreaming = data.is_streaming;
  isChaosActive = data.is_chaos_active;
  isCutoverActive = data.is_cutover_active;

  updateControlButtons();

  // Update KPIs
  kpiLegacyCount.textContent = numberFormatter.format(data.legacy_count);
  kpiLegacyVol.textContent = currencyFormatter.format(data.legacy_volume);

  kpiCloudCount.textContent = numberFormatter.format(data.cloud_count);
  kpiCloudVol.textContent = currencyFormatter.format(data.cloud_volume);

  kpiDriftCount.innerHTML = `${numberFormatter.format(data.drift)} <span class="drift-unit">trades</span>`;
  kpiVolDiff.textContent = currencyFormatter.format(data.volume_difference);
  kpiTps.innerHTML = `${data.tps} <span class="drift-unit">TPS</span>`;

  // Topology Update
  topoProducerRate.textContent = `${data.tps} trades/sec`;
  topoLegacyCount.textContent = `${numberFormatter.format(data.legacy_count)} Captured`;
  topoCloudCount.textContent = `${numberFormatter.format(data.cloud_count)} Captured`;
  topoAuditorDrift.textContent = `Drift: ${data.drift}`;

  // Parity Status Evaluation
  if (data.status === 'IN_PARITY') {
    parityPill.classList.remove('drift');
    parityPillDot.className = 'pulse-dot green';
    parityPillText.textContent = '100% IN PARITY (0 DRIFT)';

    driftStatusBadge.className = 'badge-mini drift';
    driftStatusBadge.textContent = 'ZERO DRIFT';

    topoAuditorNode.classList.remove('drift-alert');
    topoAuditorDrift.className = 'node-metric text-green';
  } else {
    parityPill.classList.add('drift');
    parityPillDot.className = 'pulse-dot danger';
    parityPillText.textContent = `DRIFT DETECTED: -${data.drift} TRADES`;

    driftStatusBadge.className = 'badge-mini drift alert';
    driftStatusBadge.textContent = 'DRIFT DETECTED';

    topoAuditorNode.classList.add('drift-alert');
    topoAuditorDrift.className = 'node-metric text-danger';
  }

  // Chaos Visuals in Topology
  if (isChaosActive) {
    cloudForkLeg.classList.add('partitioned');
    topoCloudNode.classList.add('outage');
    cloudNodeBadge.textContent = 'OUTAGE / PARTITIONED';
    cloudBadgeStatus.textContent = 'DROPPING PACKETS';
    cloudBadgeStatus.className = 'badge-mini drift alert';
    topologyStatusText.textContent = '⚠️ AZ-1 Network Partition Active • Dropping Shadow Trades';
    topologyStatusText.className = 'topology-sub text-danger';
  } else {
    cloudForkLeg.classList.remove('partitioned');
    topoCloudNode.classList.remove('outage');
    cloudNodeBadge.textContent = isCutoverActive ? 'CLOUD PRIMARY' : 'CLOUD SHADOW';
    cloudBadgeStatus.textContent = isCutoverActive ? 'MASTER WRITER' : 'SHADOW AZ-1';
    cloudBadgeStatus.className = 'badge-mini cloud';
    topologyStatusText.textContent = isCutoverActive 
      ? '🚀 Cloud Aurora Promoted to Primary • Legacy Decommissioned' 
      : 'Synchronous Dual Fan-out Stream Active';
    topologyStatusText.className = 'topology-sub';
  }

  // Handle Migrated Core Workload Metrics (Trade Reporting)
  if (data.reporting) {
    repExecutions.textContent = `${numberFormatter.format(data.reporting.total_reported_executions)} trades`;
    repVolume.textContent = currencyFormatter.format(data.reporting.total_notional_volume);
    repAvg.textContent = currencyFormatter.format(data.reporting.average_execution_value);
  }

  // Handle Latest Trades in Feed Table
  if (data.latest_trades && data.latest_trades.length > 0) {
    renderTrades(data.latest_trades);
  }

  // Handle Log Messages
  if (data.recent_logs && data.recent_logs.length > 0) {
    data.recent_logs.forEach(log => appendConsoleLog(log.ts, log.type, log.msg));
  }
}

// Render Incoming Trades into Feed
function renderTrades(trades) {
  // Clear placeholder if present
  const emptyRow = tradeTbody.querySelector('.empty-row');
  if (emptyRow) {
    emptyRow.remove();
  }

  trades.forEach(trade => {
    // Check if trade already rendered
    if (document.getElementById(`tr-${trade.trade_id}`)) return;

    const tr = document.createElement('tr');
    tr.id = `tr-${trade.trade_id}`;

    const legacyBadge = `<span class="status-badge-table success">✅ STORED</span>`;
    const cloudBadge = trade.cloud_status === 'STORED'
      ? `<span class="status-badge-table success">✅ SHADOW</span>`
      : `<span class="status-badge-table dropped">❌ DROPPED</span>`;

    tr.innerHTML = `
      <td><strong>${trade.trade_id}</strong></td>
      <td><span class="ticker-tag">${trade.instrument}</span></td>
      <td>$${parseFloat(trade.price).toFixed(2)}</td>
      <td>${trade.quantity}</td>
      <td>$${(parseFloat(trade.price) * parseInt(trade.quantity)).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
      <td>${legacyBadge}</td>
      <td>${cloudBadge}</td>
      <td><small>${trade.timestamp.split('T')[1] || trade.timestamp}</small></td>
    `;

    tradeTbody.insertBefore(tr, tradeTbody.firstChild);
  });

  // Limit table to latest 35 entries
  while (tradeTbody.children.length > 35) {
    tradeTbody.removeChild(tradeTbody.lastChild);
  }
}

// Append Console Log
function appendConsoleLog(ts, type, msg) {
  // Avoid duplicate lines
  const existing = auditConsole.lastElementChild;
  if (existing && existing.dataset.msg === msg) return;

  const div = document.createElement('div');
  div.className = `log-line ${type}`;
  div.dataset.msg = msg;
  div.innerHTML = `<span class="log-ts">[${ts}]</span><span class="log-msg">${msg}</span>`;
  auditConsole.appendChild(div);
  auditConsole.scrollTop = auditConsole.scrollHeight;
}

// Update Control Button Labels & Styles
function updateControlButtons() {
  if (isStreaming) {
    btnStreamToggle.classList.replace('btn-primary', 'btn-outline');
    streamBtnLabel.textContent = 'Pause Stream';
    streamIcon.textContent = '⏸';
  } else {
    btnStreamToggle.classList.replace('btn-outline', 'btn-primary');
    streamBtnLabel.textContent = 'Start Stream';
    streamIcon.textContent = '▶';
  }

  if (isChaosActive) {
    btnChaosToggle.classList.add('active-chaos');
    chaosBtnLabel.textContent = 'Heal Cloud Outage';
  } else {
    btnChaosToggle.classList.remove('active-chaos');
    chaosBtnLabel.textContent = 'Inject Cloud Chaos';
  }

  if (isCutoverActive) {
    btnCutover.textContent = '✓ Cloud Cutover Complete';
    btnCutover.disabled = true;
    btnCutover.style.opacity = '0.6';
  } else {
    btnCutover.innerHTML = '<span class="btn-icon">🚀</span><span>Promote Cutover</span>';
    btnCutover.disabled = false;
    btnCutover.style.opacity = '1';
  }
}

// Action Button Listeners
btnStreamToggle.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/stream/toggle', { method: 'POST' });
    const data = await res.json();
    appendConsoleLog('CMD', 'info', `Stream state changed: ${data.is_streaming ? 'RUNNING' : 'PAUSED'}`);
  } catch (err) {
    console.error(err);
  }
});

btnChaosToggle.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/chaos/toggle', { method: 'POST' });
    const data = await res.json();
    if (data.is_chaos_active) {
      appendConsoleLog('CHAOS', 'alert', '⚡ Simulated transient AWS Aurora AZ network partition! Shadow writes dropping.');
    } else {
      appendConsoleLog('CHAOS', 'success', '🛡️ Network partition healed. Cloud consumer re-connected to Kafka stream.');
    }
  } catch (err) {
    console.error(err);
  }
});

btnReconcile.addEventListener('click', async () => {
  btnReconcile.disabled = true;
  appendConsoleLog('REPLAY', 'audit', 'Initiating out-of-band automatic reconciliation replay from event log...');
  try {
    const res = await fetch('/api/reconcile', { method: 'POST' });
    const data = await res.json();
    appendConsoleLog('REPLAY', 'success', `Reconciliation complete: replayed ${data.replayed} missing trades idempotently.`);
    appendConsoleLog('AUDIT', 'highlight', `New Parity Status: ${data.status} • Zero Data Loss Achieved.`);
  } catch (err) {
    console.error(err);
  } finally {
    btnReconcile.disabled = false;
  }
});

btnCutover.addEventListener('click', async () => {
  if (!confirm('Execute cutover? This will promote Target Cloud Aurora to Primary Master.')) return;
  try {
    const res = await fetch('/api/cutover', { method: 'POST' });
    const data = await res.json();
    appendConsoleLog('CUTOVER', 'success', '🌟 ZERO-DOWNTIME CUTOVER COMPLETE! Cloud DB is now Primary Master.');
  } catch (err) {
    console.error(err);
  }
});

btnReset.addEventListener('click', async () => {
  if (!confirm('Reset simulation? This resets legacy and cloud databases.')) return;
  try {
    const res = await fetch('/api/reset', { method: 'POST' });
    const data = await res.json();
    tradeTbody.innerHTML = `<tr class="empty-row"><td colspan="8">Databases reset. Click "Start Stream" to begin.</td></tr>`;
    appendConsoleLog('SYSTEM', 'info', 'Cleaned databases reset. Fresh domain models loaded.');
  } catch (err) {
    console.error(err);
  }
});

speedRange.addEventListener('input', (e) => {
  const tps = e.target.value;
  speedVal.textContent = `${tps} TPS`;
  fetch('/api/stream/speed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tps: parseInt(tps) })
  });
});

btnClearLog.addEventListener('click', () => {
  auditConsole.innerHTML = '';
});

btnExportEod.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/reports/eod');
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FINRA_CAT_EOD_REPORT_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    appendConsoleLog('REPORT', 'success', 'Downloaded Regulatory EOD Report snapshot.');
  } catch (err) {
    console.error(err);
  }
});

// Boot
window.addEventListener('DOMContentLoaded', () => {
  initSSE();
  // Initial status poll
  pollStatusFallback();
});
