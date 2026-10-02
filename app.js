/**
 * Nexus Exchange - Next-Gen Mission Control Dashboard
 * Cyberpunk High-Frequency Trading & Hybrid Cloud Migration Engine
 */

// Application State
let isStreaming = false;
let isChaosActive = false;
let isCutoverActive = false;
let eventSource = null;
let audioEnabled = true;
let currentTps = 20;
let tpsHistory = new Array(30).fill(0);
let latestTradesCache = [];
let audioCtx = null;

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
      // Ascending Arpeggio (C5 -> E5 -> G5)
      const freqs = [523.25, 659.25, 783.99];
      freqs.forEach((freq, idx) => {
        const subOsc = ctx.createOscillator();
        const subGain = ctx.createGain();
        subOsc.connect(subGain);
        subGain.connect(ctx.destination);
        subOsc.type = 'triangle';
        subOsc.frequency.setValueAtTime(freq, now + idx * 0.08);
        subGain.gain.setValueAtTime(0.08, now + idx * 0.08);
        subGain.gain.linearRampToValueAtTime(0, now + idx * 0.08 + 0.12);
        subOsc.start(now + idx * 0.08);
        subOsc.stop(now + idx * 0.08 + 0.12);
      });
    } else if (type === 'cutover') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, now);
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
   Real-Time Server-Sent Events (SSE) Stream
   ========================================================================== */
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
    setTimeout(pollStatusFallback, 1500);
  };
}

async function pollStatusFallback() {
  try {
    const res = await fetch('/api/status');
    if (res.ok) {
      const data = await res.json();
      handleTelemetryUpdate(data);
    }
  } catch (err) {
    console.warn('Status poll offline:', err);
  } finally {
    if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
      setTimeout(pollStatusFallback, 1500);
    }
  }
}

/* ==========================================================================
   Telemetry Processing & UI Updates
   ========================================================================== */
function handleTelemetryUpdate(data) {
  isStreaming = data.is_streaming;
  isChaosActive = data.is_chaos_active;
  isCutoverActive = data.is_cutover_active;
  currentTps = data.tps || 0;

  // Track TPS in history buffer for wave chart
  tpsHistory.push(currentTps);
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
  kpiTps.innerHTML = `${data.tps} <span class="unit">TPS</span>`;

  // Parity Status Badges
  if (data.status === 'IN_PARITY') {
    parityPill.className = 'telemetry-pill parity-pill';
    parityPillDot.className = 'pulse-indicator green';
    parityPillText.textContent = '100% IN PARITY';
    driftStatusBadge.className = 'badge-chip drift';
    driftStatusBadge.textContent = 'ZERO DRIFT';
    driftDot.className = 'kpi-dot drift';
    updateRadialGauge(100, true);
  } else {
    parityPill.className = 'telemetry-pill parity-pill alert';
    parityPillDot.className = 'pulse-indicator red';
    parityPillText.textContent = `DRIFT: ${drift} TRADES`;
    driftStatusBadge.className = 'badge-chip drift alert';
    driftStatusBadge.textContent = `DRIFT (${drift})`;
    driftDot.className = 'kpi-dot drift alert';

    // Calculate sync %
    const total = Math.max(1, data.legacy_count);
    const syncPct = Math.max(0, Math.min(100, (data.cloud_count / total) * 100));
    updateRadialGauge(syncPct, false);
  }

  // Topology Nodes
  topoProducerRate.textContent = isStreaming ? `${data.tps} trades/sec` : '0 trades/sec';
  topoLegacyCount.textContent = `${numberFormatter.format(data.legacy_count)} Captured`;
  topoCloudCount.textContent = `${numberFormatter.format(data.cloud_count)} Captured`;
  topoAuditorDrift.textContent = `Drift: ${drift}`;

  if (isChaosActive) {
    cloudBadgeStatus.textContent = 'PARTITIONED';
    cloudBadgeStatus.className = 'badge-chip cloud alert';
    cloudWireChannel.classList.add('broken');
    cloudWireLabel.textContent = 'DROPPING TRADES';
    topoCloudNode.classList.add('chaos-broken');
    cloudNodeBadge.textContent = 'AZ OUTAGE';
    cloudNodeBadge.style.background = 'rgba(255,0,85,0.3)';
    cloudNodeBadge.style.color = '#ff4d79';
    topologyStatusText.textContent = '⚠️ AZ Network Partition Active: Cloud Worker Dropping Writes!';
    topologyStatusText.className = 'topology-state-pill chaos';
  } else {
    cloudBadgeStatus.textContent = isCutoverActive ? 'PRIMARY MASTER' : 'SHADOW AZ-1';
    cloudBadgeStatus.className = 'badge-chip cloud';
    cloudWireChannel.classList.remove('broken');
    cloudWireLabel.textContent = isCutoverActive ? 'Primary Wire' : 'Shadow Wire';
    topoCloudNode.classList.remove('chaos-broken');
    cloudNodeBadge.textContent = isCutoverActive ? 'PRIMARY MASTER' : 'CLOUD SHADOW';
    cloudNodeBadge.style.background = isCutoverActive ? 'rgba(16,185,129,0.3)' : 'rgba(168,85,247,0.15)';
    cloudNodeBadge.style.color = isCutoverActive ? '#34d399' : '#c084fc';
    topologyStatusText.textContent = isCutoverActive
      ? '🚀 Cloud Aurora Promoted to Primary Master • On-Prem Hot Standby Active'
      : 'Dual Parallel Ingestion Active • Zero Matching Backpressure';
    topologyStatusText.className = 'topology-state-pill';
  }

  // Workload Metrics (Trade Reporting)
  if (data.reporting) {
    repExecutions.textContent = `${numberFormatter.format(data.reporting.total_reported_executions)} trades`;
    repVolume.textContent = currencyFormatter.format(data.reporting.total_notional_volume);
    repAvg.textContent = currencyFormatter.format(data.reporting.average_execution_value);
  }

  // Update Trade Feed Table
  if (data.latest_trades && data.latest_trades.length > 0) {
    latestTradesCache = data.latest_trades;
    renderTrades(data.latest_trades);
  }

  // Update Audit Console Logs
  if (data.recent_logs && data.recent_logs.length > 0) {
    renderConsoleLogs(data.recent_logs);
  }

  // Render Canvas Graphs
  renderWaveChart();
}

/* ==========================================================================
   Radial Synchronizer Gauge Update
   ========================================================================== */
function updateRadialGauge(percentage, inParity) {
  // circumference for r=68 is 2 * PI * 68 ≈ 427.25
  const circumference = 427.25;
  const offset = circumference - (percentage / 100) * circumference;
  gaugeFill.style.strokeDashoffset = offset;

  gaugePct.textContent = `${percentage.toFixed(1)}%`;
  if (inParity) {
    gaugeFill.classList.remove('drift-alert');
    gaugeStatusSub.textContent = 'Zero Drift';
    gaugeStatusSub.style.color = 'var(--neon-green)';
  } else {
    gaugeFill.classList.add('drift-alert');
    gaugeStatusSub.textContent = 'Drift Detected';
    gaugeStatusSub.style.color = 'var(--neon-crimson)';
  }
}

/* ==========================================================================
   Wave Chart (Real-Time Canvas Oscilloscope)
   ========================================================================== */
function renderWaveChart() {
  if (!waveCanvas) return;
  const ctx = waveCanvas.getContext('2d');
  const width = waveCanvas.clientWidth;
  const height = waveCanvas.clientHeight;
  waveCanvas.width = width;
  waveCanvas.height = height;

  ctx.clearRect(0, 0, width, height);

  if (tpsHistory.length < 2) return;

  const maxVal = Math.max(60, ...tpsHistory);
  const step = width / (tpsHistory.length - 1);

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
  ctx.shadowBlur = 8;
  ctx.stroke();
  ctx.shadowBlur = 0;
}

/* ==========================================================================
   Trade Feed Rendering with Modal Inspector
   ========================================================================== */
function renderTrades(trades) {
  const filterVal = (feedFilter.value || '').toUpperCase().trim();
  const filtered = filterVal
    ? trades.filter((t) => t.instrument.toUpperCase().includes(filterVal))
    : trades;

  feedCounter.textContent = `${filtered.length} recent executions`;

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
   Console Log Ledger
   ========================================================================== */
function renderConsoleLogs(logs) {
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
      title: 'Market Feed Producer Engine',
      desc: 'High-throughput securities trade generator delivering continuous Order & Trade domain objects.',
      details: [
        { lbl: 'Feed Rate', val: 'Up to 1,000 executions/sec' },
        { lbl: 'Sanitization Pipeline', val: 'data/cleanse.py (Pandas hygiene)' },
        { lbl: 'Standardization', val: 'ISO-8601 UTC timestamp format' },
        { lbl: 'Clean Domain Validation', val: 'dataclass Trade invariants' }
      ]
    },
    broker: {
      title: 'Decoupled Event Stream (Apache Kafka / AWS MSK)',
      desc: 'Asynchronous message broker providing partitioned consumer group isolation for dual parallel consumption.',
      details: [
        { lbl: 'Active Topic', val: 'market.trades' },
        { lbl: 'Delivery Semantics', val: 'At-least-once with idempotent consumer UPSERT' },
        { lbl: 'Backpressure', val: '0% matching engine lock overhead' },
        { lbl: 'Partition Scaling', val: '3 partitions (simulated memory queue)' }
      ]
    },
    legacy: {
      title: 'Legacy On-Premises Trading Database',
      desc: 'Authoritative matching engine primary store. Retains 100% of trades as hot-standby during migration.',
      details: [
        { lbl: 'Engine', val: 'SQLite 3 (WAL mode) / PostgreSQL 16 Bare-Metal' },
        { lbl: 'Port', val: '5432' },
        { lbl: 'Idempotency DDL', val: 'PRIMARY KEY (trade_id) + INSERT OR IGNORE' },
        { lbl: 'Data Loss Protection', val: '0.00% Zero-Loss Hot Standby' }
      ]
    },
    cloud: {
      title: 'Target Cloud Database (AWS Aurora Multi-AZ PostgreSQL)',
      desc: 'High-availability shadow store promoted to primary master upon cutover verification.',
      details: [
        { lbl: 'Engine', val: 'AWS Aurora PostgreSQL Multi-AZ' },
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
   Command Action Listeners
   ========================================================================== */
btnStreamToggle.addEventListener('click', async () => {
  playSfx('click');
  try {
    const res = await fetch('/api/stream/toggle', { method: 'POST' });
    const data = await res.json();
    isStreaming = data.is_streaming;
    appendConsoleLog('STREAM', 'info', `Stream manually ${isStreaming ? 'STARTED' : 'PAUSED'}.`);
  } catch (err) {
    console.error(err);
  }
});

btnChaosToggle.addEventListener('click', async () => {
  playSfx('chaos');
  try {
    const res = await fetch('/api/chaos/toggle', { method: 'POST' });
    const data = await res.json();
    isChaosActive = data.is_chaos_active;
    appendConsoleLog(
      'CHAOS',
      isChaosActive ? 'alert' : 'success',
      isChaosActive
        ? 'AWS AZ Outage simulated: Cloud worker dropping trades!'
        : 'Network partition healed: Cloud shadow stream restored.'
    );
  } catch (err) {
    console.error(err);
  }
});

btnReconcile.addEventListener('click', async () => {
  playSfx('reconcile');
  try {
    appendConsoleLog('RECON', 'info', 'Triggering out-of-band idempotent catch-up replay...');
    const res = await fetch('/api/reconcile', { method: 'POST' });
    const data = await res.json();
    appendConsoleLog(
      'RECON',
      'success',
      `Reconciled ${data.replayed} missing trades with ON CONFLICT semantics! Store Status: ${data.status}`
    );
  } catch (err) {
    console.error(err);
  }
});

btnCutover.addEventListener('click', async () => {
  playSfx('cutover');
  try {
    appendConsoleLog('CUTOVER', 'info', 'Promoting AWS Aurora Multi-AZ to Primary Master...');
    const res = await fetch('/api/cutover', { method: 'POST' });
    const data = await res.json();
    appendConsoleLog(
      'CUTOVER',
      'success',
      'Production Cutover Successful! Cloud Aurora is now Primary Master with zero downtime.'
    );
  } catch (err) {
    console.error(err);
  }
});

btnRollback.addEventListener('click', async () => {
  playSfx('chaos');
  try {
    appendConsoleLog('ROLLBACK', 'alert', 'Triggering Failback to On-Premise Hot Standby...');
    const res = await fetch('/api/rollback', { method: 'POST' });
    const data = await res.json();
    appendConsoleLog(
      'ROLLBACK',
      'success',
      'Failback Drill Complete: Legacy Hot-Standby resumed primary operations with 0.00% data loss!'
    );
  } catch (err) {
    console.error(err);
  }
});

btnReset.addEventListener('click', async () => {
  playSfx('click');
  try {
    appendConsoleLog('RESET', 'info', 'Resetting demonstration databases to initial state...');
    await fetch('/api/reset', { method: 'POST' });
    appendConsoleLog('RESET', 'success', 'Databases reset to 0 records. Ready for new drill.');
  } catch (err) {
    console.error(err);
  }
});

speedRange.addEventListener('input', async (e) => {
  const tps = parseInt(e.target.value, 10);
  speedVal.textContent = `${tps} TPS`;
  try {
    await fetch('/api/stream/speed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tps: tps })
    });
  } catch (err) {
    console.error(err);
  }
});

btnExportEod.addEventListener('click', async () => {
  playSfx('click');
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
  initSSE();
  renderWaveChart();
  window.addEventListener('resize', renderWaveChart);
});
