/**
 * Nexus Exchange - Next-Gen Mission Control Dashboard
 * Cyberpunk High-Frequency Trading & Hybrid Cloud Migration Engine
 * Clean Architecture Challenge 1.2 Core
 * Supports both Live Python Backend & Autonomous In-Browser Standalone Simulation
 */

// Application State
let isBackendConnected = false;
let isStreaming = false;
let isChaosActive = false;
let isCutoverActive = false;
let eventSource = null;
let audioEnabled = true;
let currentTps = 20;
let tpsHistory = new Array(30).fill(0);
let latestTradesCache = [];
let audioCtx = null;
let simIntervalId = null;

// Synthetic Data Engine State
const SIM_INSTRUMENTS = [
  { sym: 'NVDA', base: 124.50 },
  { sym: 'AAPL', base: 228.10 },
  { sym: 'MSFT', base: 432.80 },
  { sym: 'AMZN', base: 189.60 },
  { sym: 'TSLA', base: 254.20 },
  { sym: 'GOOGL', base: 178.90 },
  { sym: 'BTC/USD', base: 66420.00 },
  { sym: 'ETH/USD', base: 3510.00 }
];

let simState = {
  legacyCount: 1131,
  cloudCount: 1131,
  legacyVolume: 494719635.93,
  cloudVolume: 494719635.93,
  drift: 0,
  droppedTrades: [],
  recentTrades: [],
  logs: [
    { ts: '09:30:00', type: 'info', msg: 'Hexagonal Core initialized with Ports & Adapters.' },
    { ts: '09:30:01', type: 'success', msg: 'SqliteTradeAdapter bound: Primary On-Prem & Cloud Replica.' },
    { ts: '09:30:02', type: 'audit', msg: 'Out-of-Band Parity Engine active. Topic: market.trades' }
  ]
};

// DOM Elements
const btnStreamToggle = document.getElementById('btn-stream-toggle');
const streamBtnLabel = document.getElementById('stream-btn-label');
const streamIcon = document.getElementById('stream-icon');

const btnChaosToggle = document.getElementById('btn-chaos-toggle');
const chaosBtnLabel = document.getElementById('chaos-btn-label');

const btnReconcile = document.getElementById('btn-reconcile');
const btnCutover = document.getElementById('btn-cutover');
const btnRollback = document.getElementById('btn-rollback');
const btnReset = document.getElementById('btn-reset');
const btnClearLog = document.getElementById('btn-clear-log');
const btnCopyLog = document.getElementById('btn-copy-log');
const btnAudioToggle = document.getElementById('btn-audio-toggle');
const audioIcon = document.getElementById('audio-icon');
const audioText = document.getElementById('audio-text');

const speedRange = document.getElementById('speed-range');
const speedVal = document.getElementById('speed-val');

// Badges
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
const driftDot = document.getElementById('drift-dot');
const cloudBadgeStatus = document.getElementById('cloud-badge-status');

// Topology Elements
const topoProducerRate = document.getElementById('topo-producer-rate');
const topoLegacyCount = document.getElementById('topo-legacy-count');
const topoCloudCount = document.getElementById('topo-cloud-count');
const topoCloudNode = document.getElementById('topo-cloud-node');
const topoAuditorNode = document.getElementById('topo-auditor-node');
const topoAuditorDrift = document.getElementById('topo-auditor-drift');
const cloudWireChannel = document.getElementById('cloud-wire-channel');
const cloudWireLabel = document.getElementById('cloud-wire-label');
const cloudNodeBadge = document.getElementById('cloud-node-badge');
const topologyStatusText = document.getElementById('topology-status-text');

// Gauge & Chart Elements
const gaugeFill = document.getElementById('gauge-fill');
const gaugePct = document.getElementById('gauge-pct');
const gaugeStatusSub = document.getElementById('gauge-status-sub');
const waveCanvas = document.getElementById('live-wave-chart');
const topoCanvas = document.getElementById('topo-canvas');

// Feed & Console Elements
const tradeTbody = document.getElementById('trade-tbody');
const auditConsole = document.getElementById('audit-console');
const feedCounter = document.getElementById('feed-counter');
const feedFilter = document.getElementById('feed-filter');

// Workload Reporting Elements
const repExecutions = document.getElementById('rep-executions');
const repVolume = document.getElementById('rep-volume');
const repAvg = document.getElementById('rep-avg');
const btnExportEod = document.getElementById('btn-export-eod');

// Modals
const tradeModal = document.getElementById('trade-modal');
const modalTradeId = document.getElementById('modal-trade-id');
const modalTradeBody = document.getElementById('modal-trade-body');
const btnCloseModal = document.getElementById('btn-close-modal');

const nodeModal = document.getElementById('node-modal');
const modalNodeTitle = document.getElementById('modal-node-title');
const modalNodeBody = document.getElementById('modal-node-body');
const btnCloseNodeModal = document.getElementById('btn-close-node-modal');

// Formatters
const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

const numberFormatter = new Intl.NumberFormat('en-US');

/* ==========================================================================
   Web Audio API Synthesizer (Sci-Fi Sound FX Engine)
   ========================================================================== */
function getAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

function playSfx(type) {
  if (!audioEnabled) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === 'click') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(800, now);
      osc.frequency.exponentialRampToValueAtTime(400, now + 0.05);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.linearRampToValueAtTime(0, now + 0.05);
      osc.start(now);
      osc.stop(now + 0.05);
    } else if (type === 'chaos') {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(320, now);
      osc.frequency.linearRampToValueAtTime(160, now + 0.25);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.linearRampToValueAtTime(0, now + 0.25);
      osc.start(now);
      osc.stop(now + 0.25);
    } else if (type === 'reconcile') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(523.25, now); // C5
      osc.frequency.setValueAtTime(659.25, now + 0.08); // E5
      osc.frequency.setValueAtTime(783.99, now + 0.16); // G5
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.linearRampToValueAtTime(0, now + 0.26);
      osc.start(now);
      osc.stop(now + 0.26);
    } else if (type === 'cutover') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.35);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.linearRampToValueAtTime(0, now + 0.35);
      osc.start(now);
      osc.stop(now + 0.35);
    }
  } catch (e) {
    // Audio context not allowed or failed silently
  }
}

/* ==========================================================================
   Real-Time Server-Sent Events (SSE) Stream & Hybrid Fallback
   ========================================================================== */
function initSSE() {
  if (eventSource) {
    eventSource.close();
  }

  try {
    eventSource = new EventSource('/api/events');

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        isBackendConnected = true;
        handleTelemetryUpdate(data);
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    };

    eventSource.onerror = () => {
      isBackendConnected = false;
      setTimeout(pollStatusFallback, 1500);
    };
  } catch (err) {
    isBackendConnected = false;
    startAutonomousSimulation();
  }
}

async function pollStatusFallback() {
  try {
    const res = await fetch('/api/status', { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();
      isBackendConnected = true;
      stopAutonomousSimulation();
      handleTelemetryUpdate(data);
      return;
    }
  } catch (err) {
    // Backend unreachable: switch to autonomous client simulation mode
  }

  isBackendConnected = false;
  startAutonomousSimulation();
}

/* ==========================================================================
   Autonomous In-Browser Simulation Engine
   Activated whenever backend API is unreachable (e.g. GitHub Pages or offline)
   ========================================================================== */
function startAutonomousSimulation() {
  if (simIntervalId) return;

  appendConsoleLog('ENGINE', 'info', 'Autonomous Client-Side Simulation active (Zero-Loss Pipeline Online).');

  // Prepopulate initial trades if empty
  if (simState.recentTrades.length === 0) {
    for (let i = 0; i < 15; i++) {
      generateSyntheticTrade(false);
    }
    pushSimTelemetry();
  }

  simIntervalId = setInterval(() => {
    if (isStreaming) {
      generateSyntheticTrade(true);
    }
    pushSimTelemetry();
  }, Math.max(20, Math.floor(1000 / currentTps)));
}

function stopAutonomousSimulation() {
  if (simIntervalId) {
    clearInterval(simIntervalId);
    simIntervalId = null;
  }
}

function generateSyntheticTrade(isLive = true) {
  const item = SIM_INSTRUMENTS[Math.floor(Math.random() * SIM_INSTRUMENTS.length)];
  const variance = (Math.random() * 0.04 - 0.02);
  const price = parseFloat((item.base * (1 + variance)).toFixed(2));
  const qty = Math.floor(Math.random() * 490) + 10;
  const vol = price * qty;
  const hex = Math.random().toString(16).substring(2, 8).toUpperCase();
  const hex2 = Math.random().toString(16).substring(2, 8).toUpperCase();
  const hex3 = Math.random().toString(16).substring(2, 8).toUpperCase();

  const isDropped = isChaosActive;
  const trade = {
    trade_id: `TRD-${hex}${hex2}`,
    instrument: item.sym,
    price: price,
    quantity: qty,
    buy_order_id: `ORD-BUY-${hex}`,
    sell_order_id: `ORD-SELL-${hex3}`,
    timestamp: new Date().toISOString(),
    legacy_status: 'STORED',
    cloud_status: isDropped ? 'DROPPED' : 'STORED'
  };

  if (isLive) {
    simState.legacyCount++;
    simState.legacyVolume += vol;

    if (isDropped) {
      simState.drift++;
      simState.droppedTrades.push(trade);
    } else {
      simState.cloudCount++;
      simState.cloudVolume += vol;
    }

    simState.recentTrades.unshift(trade);
    if (simState.recentTrades.length > 40) simState.recentTrades.pop();
  }
}

function pushSimTelemetry() {
  const volDiff = Math.abs(simState.legacyVolume - simState.cloudVolume);
  const status = simState.drift === 0 ? 'IN_PARITY' : 'DRIFT_DETECTED';

  const snapshot = {
    legacy_count: simState.legacyCount,
    cloud_count: simState.cloudCount,
    drift: simState.drift,
    status: status,
    legacy_volume: simState.legacyVolume,
    cloud_volume: simState.cloudVolume,
    volume_difference: volDiff,
    is_streaming: isStreaming,
    is_chaos_active: isChaosActive,
    is_cutover_active: isCutoverActive,
    tps: isStreaming ? currentTps : 0,
    reporting: {
      workload_name: 'Post-Trade Regulatory Reporting & Surveillance',
      execution_status: isCutoverActive ? 'CLOUD_PRIMARY_ACTIVE' : 'CLOUD_NATIVE_ACTIVE',
      compliance_standard: 'FINRA CAT / MiFID II Compliant',
      total_reported_executions: simState.cloudCount,
      total_notional_volume: simState.cloudVolume,
      average_execution_value: simState.cloudCount > 0 ? (simState.cloudVolume / simState.cloudCount) : 0,
      data_source: isCutoverActive ? 'AWS Aurora Multi-AZ PostgreSQL (Primary Master)' : 'AWS Aurora Multi-AZ PostgreSQL (Shadow Store)',
      offload_impact: '100% of reporting query I/O removed from on-prem matching engine'
    },
    latest_trades: simState.recentTrades,
    recent_logs: simState.logs
  };

  handleTelemetryUpdate(snapshot);
}

/* ==========================================================================
   Telemetry Processing & UI Updates
   ========================================================================== */
function handleTelemetryUpdate(data) {
  isStreaming = data.is_streaming;
  isChaosActive = data.is_chaos_active;
  isCutoverActive = data.is_cutover_active;
  const activeTps = data.tps || 0;

  // Track TPS in history buffer for wave chart
  tpsHistory.push(activeTps);
  if (tpsHistory.length > 30) tpsHistory.shift();

  // Update Controls
  if (isStreaming) {
    streamBtnLabel.textContent = 'Pause Stream';
    streamIcon.textContent = '⏸';
    btnStreamToggle.classList.add('active');
  } else {
    streamBtnLabel.textContent = 'Start Stream';
    streamIcon.textContent = '▶';
    btnStreamToggle.classList.remove('active');
  }

  if (isChaosActive) {
    chaosBtnLabel.textContent = 'Heal Cloud Chaos';
    btnChaosToggle.classList.add('active');
  } else {
    chaosBtnLabel.textContent = 'Inject Cloud Chaos';
    btnChaosToggle.classList.remove('active');
  }

  if (isCutoverActive) {
    btnCutover.classList.add('promoted');
    btnCutover.innerHTML = '<span class="cmd-icon">👑</span><span>Cutover Promoted</span>';
  } else {
    btnCutover.classList.remove('promoted');
    btnCutover.innerHTML = '<span class="cmd-icon">🚀</span><span>Promote Cutover</span>';
  }

  // Update KPIs
  kpiLegacyCount.textContent = numberFormatter.format(data.legacy_count);
  kpiLegacyVol.textContent = currencyFormatter.format(data.legacy_volume);
  kpiCloudCount.textContent = numberFormatter.format(data.cloud_count);
  kpiCloudVol.textContent = currencyFormatter.format(data.cloud_volume);

  const drift = data.drift || 0;
  kpiDriftCount.innerHTML = `${numberFormatter.format(drift)} <span class="unit">trades</span>`;
  kpiVolDiff.textContent = currencyFormatter.format(data.volume_difference);
  kpiTps.innerHTML = `${activeTps} <span class="unit">TPS</span>`;

  // Parity Status Badges
  if (data.status === 'IN_PARITY') {
    parityPill.className = 'telemetry-pill parity-pill';
    parityPillDot.className = 'pulse-indicator green';
    parityPillText.textContent = `100% IN PARITY (0 DRIFT)`;
    driftStatusBadge.className = 'badge-chip drift';
    driftStatusBadge.textContent = 'ZERO DRIFT';
    driftDot.className = 'kpi-dot drift';
    gaugeStatusSub.textContent = 'Zero Drift';
    gaugeStatusSub.style.color = 'var(--neon-green)';
    updateGauge(100.0, false);
  } else {
    parityPill.className = 'telemetry-pill parity-pill alert';
    parityPillDot.className = 'pulse-indicator red';
    parityPillText.textContent = `DRIFT: ${drift} TRADES OUT-OF-BAND`;
    driftStatusBadge.className = 'badge-chip drift alert';
    driftStatusBadge.textContent = 'OUT-OF-BAND DRIFT';
    driftDot.className = 'kpi-dot drift alert';
    gaugeStatusSub.textContent = `${drift} Trades Behind`;
    gaugeStatusSub.style.color = 'var(--neon-crimson)';

    const total = Math.max(data.legacy_count, 1);
    const pct = Math.max(0, Math.min(100, ((data.cloud_count / total) * 100)));
    updateGauge(pct, true);
  }

  // Topology Dynamic Node Status
  topoProducerRate.textContent = `${activeTps} trades/sec`;
  topoLegacyCount.textContent = `${numberFormatter.format(data.legacy_count)} Captured`;
  topoCloudCount.textContent = `${numberFormatter.format(data.cloud_count)} Captured`;
  topoAuditorDrift.textContent = `Drift: ${drift}`;

  if (isChaosActive) {
    topoCloudNode.classList.add('chaos-broken');
    cloudWireChannel.classList.add('broken');
    cloudWireLabel.textContent = 'Broken Wire (Drop)';
    cloudNodeBadge.textContent = 'OUTAGE (DROPPING)';
    cloudBadgeStatus.textContent = 'AZ-1 OUTAGE';
    cloudBadgeStatus.className = 'badge-chip drift alert';
    topologyStatusText.innerHTML = '<span class="text-danger font-semibold">AWS Multi-AZ Outage Active &bull; Shadow Dropping Trades</span>';
    topologyStatusText.classList.add('chaos');
  } else {
    topoCloudNode.classList.remove('chaos-broken');
    cloudWireChannel.classList.remove('broken');
    cloudWireLabel.textContent = 'Shadow Wire';
    cloudNodeBadge.textContent = isCutoverActive ? 'PRIMARY MASTER' : 'CLOUD SHADOW';
    cloudBadgeStatus.textContent = isCutoverActive ? 'PRIMARY MASTER' : 'SHADOW AZ-1';
    cloudBadgeStatus.className = isCutoverActive ? 'badge-chip drift' : 'badge-chip cloud';
    topologyStatusText.innerHTML = isCutoverActive
      ? '<span class="text-green font-semibold">Production Cutover Complete &bull; Cloud Aurora Active Primary</span>'
      : 'Dual Parallel Ingestion Active &bull; Zero Matching Backpressure';
    topologyStatusText.classList.remove('chaos');
  }

  if (isCutoverActive) {
    topoCloudNode.classList.add('promoted-master');
  } else {
    topoCloudNode.classList.remove('promoted-master');
  }

  // Regulatory Reporting Ribbon
  if (data.reporting) {
    repExecutions.textContent = `${numberFormatter.format(data.reporting.total_reported_executions)} trades`;
    repVolume.textContent = currencyFormatter.format(data.reporting.total_notional_volume);
    repAvg.textContent = currencyFormatter.format(data.reporting.average_execution_value);
  }

  // Update Table & Wave
  if (data.latest_trades && data.latest_trades.length > 0) {
    latestTradesCache = data.latest_trades;
    renderTrades(data.latest_trades);
  }

  // Console Logs
  if (data.recent_logs && data.recent_logs.length > 0) {
    renderConsoleLogs(data.recent_logs);
  }

  renderWaveChart();
}

/* ==========================================================================
   Radial Gauge Canvas & SVG Helper
   ========================================================================== */
function updateGauge(percentage, hasDrift) {
  const circumference = 2 * Math.PI * 68; // r=68 => ~427.25
  const offset = circumference - (percentage / 100) * circumference;

  gaugeFill.style.strokeDashoffset = offset;
  gaugePct.textContent = `${percentage.toFixed(1)}%`;

  if (hasDrift) {
    gaugeFill.classList.add('drift-alert');
  } else {
    gaugeFill.classList.remove('drift-alert');
  }
}

/* ==========================================================================
   Real-Time Ingestion Wave Chart (HTML5 Canvas - Zero-Thrash)
   ========================================================================== */
let waveCanvasWidth = 0;
let waveCanvasHeight = 0;

function resizeWaveCanvas() {
  if (!waveCanvas) return;
  const parent = waveCanvas.parentElement;
  const width = parent ? parent.clientWidth : 300;
  const height = 65;
  if (waveCanvas.width !== width || waveCanvas.height !== height) {
    waveCanvas.width = width;
    waveCanvas.height = height;
    waveCanvasWidth = width;
    waveCanvasHeight = height;
  }
}

function renderWaveChart() {
  if (!waveCanvas) return;
  if (waveCanvasWidth === 0) resizeWaveCanvas();
  const width = waveCanvasWidth;
  const height = waveCanvasHeight || 65;
  const ctx = waveCanvas.getContext('2d');

  ctx.clearRect(0, 0, width, height);

  const maxVal = Math.max(60, ...tpsHistory);
  const step = width / Math.max(1, tpsHistory.length - 1);

  // Gradient Fill
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, 'rgba(0, 242, 254, 0.35)');
  gradient.addColorStop(1, 'rgba(0, 242, 254, 0.0)');

  ctx.beginPath();
  tpsHistory.forEach((val, i) => {
    const x = i * step;
    const y = height - (val / maxVal) * (height - 10) - 5;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  // Fill
  ctx.lineTo((tpsHistory.length - 1) * step, height);
  ctx.lineTo(0, height);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Stroke
  ctx.beginPath();
  tpsHistory.forEach((val, i) => {
    const x = i * step;
    const y = height - (val / maxVal) * (height - 10) - 5;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#00f2fe';
  ctx.lineWidth = 2;
  ctx.shadowColor = '#00f2fe';
  ctx.shadowBlur = 6;
  ctx.stroke();
  ctx.shadowBlur = 0;
}

/* ==========================================================================
   Trade Feed Rendering with Modal Inspector (Signature-Cached)
   ========================================================================== */
let lastRenderedTradesSignature = '';

function renderTrades(trades) {
  const filterVal = (feedFilter.value || '').toUpperCase().trim();
  const filtered = filterVal
    ? trades.filter((t) => t.instrument.toUpperCase().includes(filterVal))
    : trades;

  feedCounter.textContent = `${filtered.length} executions`;

  // Compute a lightweight signature to avoid wasteful DOM rebuilds and shaking
  const topTrade = filtered[0];
  const sig = filterVal + '|' + filtered.length + '|' + (topTrade ? (topTrade.trade_id + ':' + topTrade.cloud_status) : 'empty');
  if (sig === lastRenderedTradesSignature) {
    return; // Zero DOM work if content is unchanged
  }
  lastRenderedTradesSignature = sig;

  if (filtered.length === 0) {
    tradeTbody.innerHTML = `
      <tr class="empty-state-row">
        <td colspan="8">
          <div class="empty-feed-box">
            <span class="empty-icon">🔍</span>
            <p>No trades matching filter "<strong>${filterVal}</strong>"</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  const rows = filtered
    .map((trade) => {
      const vol = trade.price * trade.quantity;
      const cloudClass =
        trade.cloud_status === 'STORED'
          ? 'stored'
          : trade.cloud_status === 'DROPPED'
          ? 'dropped'
          : 'replayed';

      return `
        <tr class="trade-row" onclick="openTradeModal('${trade.trade_id}')" title="Click to inspect execution details">
          <td class="mono font-semibold" style="color:var(--neon-cyan);">${trade.trade_id}</td>
          <td><span class="badge-chip legacy" style="font-size:11px;">${trade.instrument}</span></td>
          <td class="mono">$${trade.price.toFixed(2)}</td>
          <td class="mono">${trade.quantity}</td>
          <td class="mono text-green">$${vol.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
          <td><span class="store-pill stored">${trade.legacy_status}</span></td>
          <td><span class="store-pill ${cloudClass}">${trade.cloud_status}</span></td>
          <td class="mono text-dim" style="font-size:11px;">${trade.timestamp.split('T')[1] || trade.timestamp}</td>
        </tr>
      `;
    })
    .join('');

  tradeTbody.innerHTML = rows;
}

/* ==========================================================================
   Console Log Ledger (Smart-Append)
   ========================================================================== */
let lastRenderedLogsCount = 0;
let lastRenderedLogTs = '';

function renderConsoleLogs(logs) {
  if (!logs || logs.length === 0) return;
  const lastLog = logs[logs.length - 1];
  if (logs.length === lastRenderedLogsCount && lastLog && lastLog.ts === lastRenderedLogTs) {
    return; // Already up-to-date, avoid clearing and resetting scroll
  }
  lastRenderedLogsCount = logs.length;
  lastRenderedLogTs = lastLog ? lastLog.ts : '';

  auditConsole.innerHTML = '';
  logs.forEach((log) => {
    const entry = document.createElement('div');
    entry.className = `log-entry ${log.type || 'info'}`;

    const tag = document.createElement('span');
    tag.className = 'log-tag';
    tag.textContent = `[${log.ts}]`;

    const text = document.createElement('span');
    text.className = 'log-text';
    text.textContent = log.msg;

    entry.appendChild(tag);
    entry.appendChild(text);
    auditConsole.appendChild(entry);
  });
  auditConsole.scrollTop = auditConsole.scrollHeight;
}


function appendConsoleLog(tag, type, msg) {
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;

  const ts = new Date().toTimeString().split(' ')[0];
  entry.innerHTML = `<span class="log-tag">[${tag}:${ts}]</span><span class="log-text">${msg}</span>`;
  auditConsole.appendChild(entry);
  auditConsole.scrollTop = auditConsole.scrollHeight;

  simState.logs.push({ ts: `${tag}:${ts}`, type, msg });
  if (simState.logs.length > 50) simState.logs.shift();
}

/* ==========================================================================
   Modal Inspectors (Trade & Topology Node)
   ========================================================================== */
window.openTradeModal = function (tradeId) {
  const trade = latestTradesCache.find((t) => t.trade_id === tradeId);
  if (!trade) return;

  playSfx('click');
  modalTradeId.textContent = trade.trade_id;

  const notional = trade.price * trade.quantity;
  modalTradeBody.innerHTML = `
    <div class="modal-grid-2">
      <div>
        <span class="modal-item-lbl">Financial Instrument</span>
        <div class="modal-item-val text-cyan">${trade.instrument}</div>
      </div>
      <div>
        <span class="modal-item-lbl">Execution Price</span>
        <div class="modal-item-val mono">$${trade.price.toFixed(2)}</div>
      </div>
      <div>
        <span class="modal-item-lbl">Quantity (Contracts)</span>
        <div class="modal-item-val mono">${trade.quantity}</div>
      </div>
      <div>
        <span class="modal-item-lbl">Notional Cash Value</span>
        <div class="modal-item-val mono text-green">${currencyFormatter.format(notional)}</div>
      </div>
      <div>
        <span class="modal-item-lbl">Buy Order ID</span>
        <div class="modal-item-val mono" style="font-size:12px;">${trade.buy_order_id}</div>
      </div>
      <div>
        <span class="modal-item-lbl">Sell Order ID</span>
        <div class="modal-item-val mono" style="font-size:12px;">${trade.sell_order_id}</div>
      </div>
    </div>
    <div style="margin-bottom:8px;">
      <span class="modal-item-lbl">JSON Execution Envelope</span>
    </div>
    <pre class="modal-code-box"><code>${JSON.stringify(trade, null, 2)}</code></pre>
  `;
  tradeModal.classList.add('open');
};

function closeTradeModal() {
  tradeModal.classList.remove('open');
}

function openNodeModal(nodeType) {
  playSfx('click');
  const nodeSpecs = {
    producer: {
      title: 'Market Feed / Ingestion Engine',
      desc: 'Simulated multi-asset liquidity feed streaming dirty trades with validation filter.',
      details: [
        { lbl: 'Input File', val: 'data/raw_trades.csv (1,000 dirty records)' },
        { lbl: 'Filter Pipeline', val: 'data/cleanse.py (Sanitization rules)' },
        { lbl: 'Rejected Artifacts', val: 'Negative price, negative qty, null values' },
        { lbl: 'Throughput', val: `${currentTps} TPS (Adjustable via slider)` }
      ]
    },
    broker: {
      title: 'Decoupled Event Bus (Kafka MSK)',
      desc: 'Asynchronous event stream with multi-partition fan-out preventing engine backpressure.',
      details: [
        { lbl: 'Topic', val: 'market.trades' },
        { lbl: 'Partitions', val: '0, 1, 2' },
        { lbl: 'Wire Decoupling', val: 'Zero matching engine latency impact' },
        { lbl: 'Delivery Guarantee', val: 'At-Least-Once with Idempotent Consumer' }
      ]
    },
    legacy: {
      title: 'Legacy On-Premise Core Database',
      desc: 'Production PostgreSQL cluster currently fulfilling primary matching transactions.',
      details: [
        { lbl: 'Engine', val: 'PostgreSQL 15 (Legacy Node)' },
        { lbl: 'Port', val: '5432' },
        { lbl: 'Role', val: isCutoverActive ? 'Hot Standby Replica' : 'Primary Master' },
        { lbl: 'Idempotency DDL', val: 'ON CONFLICT (trade_id) DO NOTHING' }
      ]
    },
    cloud: {
      title: 'Modern AWS Aurora Cloud Database',
      desc: 'Target Multi-AZ PostgreSQL cluster operating in zero-downtime shadow mode.',
      details: [
        { lbl: 'Engine', val: 'AWS Aurora PostgreSQL 15 Multi-AZ' },
        { lbl: 'Port', val: '5433' },
        { lbl: 'Idempotency DDL', val: 'ON CONFLICT (trade_id) DO NOTHING' },
        { lbl: 'Offload Benefit', val: '100% of regulatory query I/O removed from on-prem' }
      ]
    },
    auditor: {
      title: 'Out-of-Band Parity Auditor & Reconciliation Engine',
      desc: 'Continuous non-blocking background auditor computing count drift and volume delta.',
      details: [
        { lbl: 'Audit Interval', val: 'Continuous polling (out-of-band thread)' },
        { lbl: 'Reconciliation', val: 'Automated idempotent replay from backlog' },
        { lbl: 'Compliance', val: 'FINRA CAT & MiFID II compliant transaction proof' },
        { lbl: 'Verification Speed', val: '< 5ms delta assessment' }
      ]
    }
  };

  const spec = nodeSpecs[nodeType];
  if (!spec) return;

  modalNodeTitle.textContent = spec.title;
  modalNodeBody.innerHTML = `
    <p style="color:var(--text-dim); margin-bottom:16px;">${spec.desc}</p>
    <div class="modal-grid-2">
      ${spec.details
        .map(
          (d) => `
        <div>
          <span class="modal-item-lbl">${d.lbl}</span>
          <div class="modal-item-val mono text-cyan">${d.val}</div>
        </div>
      `
        )
        .join('')}
    </div>
  `;
  nodeModal.classList.add('open');
}

function closeNodeModal() {
  nodeModal.classList.remove('open');
}

/* ==========================================================================
   Command Action Listeners (Hybrid: Backend API with Instant Client Fallback)
   ========================================================================== */
btnStreamToggle.addEventListener('click', async () => {
  playSfx('click');
  let handled = false;
  if (isBackendConnected) {
    try {
      const res = await fetch('/api/stream/toggle', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        isStreaming = data.is_streaming;
        appendConsoleLog('STREAM', 'info', `Market stream ${isStreaming ? 'RESUMED' : 'PAUSED'}.`);
        handled = true;
      }
    } catch (e) {}
  }

  if (!handled) {
    isStreaming = !isStreaming;
    appendConsoleLog('STREAM', 'info', `Market stream ${isStreaming ? 'RESUMED' : 'PAUSED'}.`);
    pushSimTelemetry();
  }
});

btnChaosToggle.addEventListener('click', async () => {
  playSfx('chaos');
  let handled = false;
  if (isBackendConnected) {
    try {
      const res = await fetch('/api/chaos/toggle', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        isChaosActive = data.is_chaos_active;
        appendConsoleLog(
          'CHAOS',
          isChaosActive ? 'alert' : 'success',
          isChaosActive ? 'AWS AZ Outage simulated: Cloud worker dropping trades!' : 'Outage HEALED.'
        );
        handled = true;
      }
    } catch (e) {}
  }

  if (!handled) {
    isChaosActive = !isChaosActive;
    appendConsoleLog(
      'CHAOS',
      isChaosActive ? 'alert' : 'success',
      isChaosActive ? 'AWS AZ Outage simulated: Cloud worker dropping trades!' : 'Outage HEALED.'
    );
    pushSimTelemetry();
  }
});

btnReconcile.addEventListener('click', async () => {
  playSfx('reconcile');
  let handled = false;
  if (isBackendConnected) {
    try {
      appendConsoleLog('RECON', 'info', 'Triggering out-of-band idempotent catch-up replay...');
      const res = await fetch('/api/reconcile', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        appendConsoleLog(
          'RECON',
          'success',
          `Reconciled ${data.replayed} missing trades with ON CONFLICT semantics! Store Status: ${data.status}`
        );
        handled = true;
      }
    } catch (e) {}
  }

  if (!handled) {
    const replayedCount = simState.droppedTrades.length;
    simState.droppedTrades.forEach((t) => {
      t.cloud_status = 'STORED';
      simState.cloudCount++;
      simState.cloudVolume += (t.price * t.quantity);
    });
    simState.droppedTrades = [];
    simState.drift = 0;
    appendConsoleLog(
      'RECON',
      'success',
      `Idempotent replay restored ${replayedCount} missing trades. Parity: IN_PARITY.`
    );
    pushSimTelemetry();
  }
});

btnCutover.addEventListener('click', async () => {
  playSfx('cutover');
  let handled = false;
  if (isBackendConnected) {
    try {
      appendConsoleLog('CUTOVER', 'info', 'Promoting AWS Aurora Multi-AZ to Primary Master...');
      const res = await fetch('/api/cutover', { method: 'POST' });
      if (res.ok) {
        isCutoverActive = true;
        appendConsoleLog('CUTOVER', 'success', 'Production Cutover Successful! Cloud Aurora is Primary Master.');
        handled = true;
      }
    } catch (e) {}
  }

  if (!handled) {
    isCutoverActive = true;
    appendConsoleLog('CUTOVER', 'success', 'Production Cutover Successful! Cloud Aurora is Primary Master.');
    pushSimTelemetry();
  }
});

btnRollback.addEventListener('click', async () => {
  playSfx('chaos');
  let handled = false;
  if (isBackendConnected) {
    try {
      appendConsoleLog('ROLLBACK', 'alert', 'Triggering Failback to On-Premise Hot Standby...');
      const res = await fetch('/api/rollback', { method: 'POST' });
      if (res.ok) {
        isCutoverActive = false;
        isChaosActive = false;
        appendConsoleLog('ROLLBACK', 'success', 'Failback drill complete: Legacy Hot-Standby resumed primary matching (0.00% data loss).');
        handled = true;
      }
    } catch (e) {}
  }

  if (!handled) {
    isCutoverActive = false;
    isChaosActive = false;
    appendConsoleLog('ROLLBACK', 'alert', 'Failback drill complete: Legacy Hot-Standby resumed primary matching (0.00% data loss).');
    pushSimTelemetry();
  }
});

btnReset.addEventListener('click', async () => {
  playSfx('click');
  let handled = false;
  if (isBackendConnected) {
    try {
      appendConsoleLog('RESET', 'info', 'Resetting demonstration databases to initial state...');
      const res = await fetch('/api/reset', { method: 'POST' });
      if (res.ok) {
        appendConsoleLog('RESET', 'success', 'Databases reset to initial state.');
        handled = true;
      }
    } catch (e) {}
  }

  if (!handled) {
    simState.legacyCount = 0;
    simState.cloudCount = 0;
    simState.legacyVolume = 0.0;
    simState.cloudVolume = 0.0;
    simState.drift = 0;
    simState.droppedTrades = [];
    simState.recentTrades = [];
    appendConsoleLog('RESET', 'success', 'Databases reset to initial state.');
    pushSimTelemetry();
  }
});

speedRange.addEventListener('input', async (e) => {
  const tps = parseInt(e.target.value, 10);
  currentTps = tps;
  speedVal.textContent = `${tps} TPS`;

  if (isBackendConnected) {
    try {
      await fetch('/api/stream/speed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tps: tps })
      });
    } catch (e) {}
  } else if (simIntervalId) {
    // Reset interval timer to new rate
    stopAutonomousSimulation();
    startAutonomousSimulation();
  }
});

btnExportEod.addEventListener('click', async () => {
  playSfx('click');
  let reportData = null;

  if (isBackendConnected) {
    try {
      const res = await fetch('/api/reports/eod');
      if (res.ok) {
        reportData = await res.json();
      }
    } catch (e) {}
  }

  if (!reportData) {
    reportData = {
      report_id: `FINRA_CAT_EOD_${Date.now()}`,
      generated_at: new Date().toISOString(),
      compliance_standard: 'FINRA CAT Section 6800 / MiFID II RTS 22',
      migration_architecture: 'Hexagonal Clean Architecture (Challenge 1.2)',
      source_database: 'AWS Aurora Multi-AZ Cloud PostgreSQL',
      total_executed_trades: simState.cloudCount,
      aggregate_notional_volume: simState.cloudVolume,
      average_trade_value: simState.cloudCount > 0 ? (simState.cloudVolume / simState.cloudCount) : 0,
      data_loss_percentage: 0.0,
      on_prem_engine_impact: '0% CPU (100% Query I/O Offloaded to Cloud)',
      verified_by: 'Out-of-Band Parity Checker Engine'
    };
  }

  const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `FINRA_CAT_EOD_REPORT_${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  appendConsoleLog('REPORT', 'success', 'Downloaded Regulatory EOD Report snapshot.');
});

btnClearLog.addEventListener('click', () => {
  playSfx('click');
  auditConsole.innerHTML = '';
});

btnCopyLog.addEventListener('click', () => {
  playSfx('click');
  const text = auditConsole.innerText;
  navigator.clipboard.writeText(text);
  appendConsoleLog('LOG', 'info', 'Copied audit console logs to clipboard.');
});

btnAudioToggle.addEventListener('click', () => {
  audioEnabled = !audioEnabled;
  audioIcon.textContent = audioEnabled ? '🔊' : '🔇';
  audioText.textContent = `SFX: ${audioEnabled ? 'ON' : 'OFF'}`;
  playSfx('click');
});

feedFilter.addEventListener('input', () => {
  if (latestTradesCache.length > 0) {
    renderTrades(latestTradesCache);
  }
});

// Modal Close Listeners
btnCloseModal.addEventListener('click', closeTradeModal);
tradeModal.addEventListener('click', (e) => {
  if (e.target === tradeModal) closeTradeModal();
});

btnCloseNodeModal.addEventListener('click', closeNodeModal);
nodeModal.addEventListener('click', (e) => {
  if (e.target === nodeModal) closeNodeModal();
});

// Setup Topology Node Click Listeners
document.querySelectorAll('.topo-card').forEach((card) => {
  card.addEventListener('click', () => {
    const nodeType = card.getAttribute('data-node');
    if (nodeType) openNodeModal(nodeType);
  });
});

/* ==========================================================================
   Boot Application
   ========================================================================== */
window.addEventListener('DOMContentLoaded', () => {
  resizeWaveCanvas();
  renderWaveChart();
  window.addEventListener('resize', () => {
    resizeWaveCanvas();
    renderWaveChart();
  });

  // Attempt backend connection, with immediate simulation warmup
  initSSE();

  // If backend doesn't answer within 800ms, start simulation immediately so UI is vibrant
  setTimeout(() => {
    if (!isBackendConnected) {
      startAutonomousSimulation();
    }
  }, 800);
});
