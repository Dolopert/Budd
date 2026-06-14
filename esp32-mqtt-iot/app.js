// ── Default Config ──────────────────────────────────────────────
const DEFAULTS = {
  broker:    'wss://broker.hivemq.com:8884/mqtt',
  clientId:  'dashboard_' + Math.random().toString(36).slice(2, 7),
  username:  '',
  password:  '',
  topicTemp: 'esp32/sensor/dht',
  topicLight:'esp32/light/switch',
  topicBright:'esp32/light/brightness',
};

// ── State ────────────────────────────────────────────────────────
let cfg = loadConfig();
let client = null;
let lightOn = false;
let brightness = 0;
let connectedAt = null;
let uptimeTimer = null;
let espLastSeen = null;

// ── Init ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  populateTopicLabels();
  document.getElementById('settingsBtn').onclick = openSettings;
  updateSliderTrack(0);
  connect();
});

// ── Config Persistence ───────────────────────────────────────────
function loadConfig() {
  try {
    const saved = localStorage.getItem('esp32_cfg');
    return saved ? { ...DEFAULTS, ...JSON.parse(saved) } : { ...DEFAULTS };
  } catch { return { ...DEFAULTS }; }
}

function saveConfig(obj) {
  localStorage.setItem('esp32_cfg', JSON.stringify(obj));
}

// ── MQTT Connection ──────────────────────────────────────────────
function connect() {
  if (client) {
    try { client.end(true); } catch {}
  }

  setStatus('connecting');
  log('info', 'กำลังเชื่อมต่อ', cfg.broker);

  const opts = {
    clientId: cfg.clientId,
    clean: true,
    reconnectPeriod: 5000,
    connectTimeout: 10000,
  };
  if (cfg.username) opts.username = cfg.username;
  if (cfg.password) opts.password = cfg.password;

  try {
    client = mqtt.connect(cfg.broker, opts);
  } catch (e) {
    setStatus('disconnected');
    log('err', 'เชื่อมต่อไม่ได้', e.message);
    return;
  }

  client.on('connect', onConnect);
  client.on('reconnect', () => { setStatus('connecting'); log('warn', 'กำลังเชื่อมต่อใหม่...', ''); });
  client.on('error', (e) => { log('err', 'MQTT Error', e.message); });
  client.on('offline', () => { setStatus('disconnected'); log('warn', 'Broker ออฟไลน์', ''); });
  client.on('close', () => { setStatus('disconnected'); });
  client.on('message', onMessage);
}

function onConnect() {
  setStatus('connected');
  connectedAt = Date.now();
  startUptimeTimer();
  log('ok', 'เชื่อมต่อสำเร็จ', cfg.broker);
  client.subscribe(cfg.topicTemp, { qos: 1 }, (err) => {
    if (err) log('err', 'Subscribe ล้มเหลว', cfg.topicTemp);
    else log('ok', 'Subscribe', cfg.topicTemp);
  });
}

function onMessage(topic, payload) {
  const msg = payload.toString().trim();
  log('info', 'RX', `[${topic}] ${msg}`);
  espLastSeen = Date.now();
  updateEspStatus();

  if (topic === cfg.topicTemp) {
    parseEnvData(msg);
  }
}

function reconnect() {
  log('info', 'ผู้ใช้กด', 'เชื่อมต่อใหม่');
  connect();
}

// ── Parse Sensor Data ────────────────────────────────────────────
// รองรับ JSON: {"temp":28.5,"humid":65} หรือ plain: "28.5,65"
function parseEnvData(msg) {
  let temp = null, humid = null;
  try {
    const obj = JSON.parse(msg);
    temp  = parseFloat(obj.temp  ?? obj.temperature ?? obj.t);
    humid = parseFloat(obj.humid ?? obj.humidity    ?? obj.h);
  } catch {
    const parts = msg.split(',');
    temp  = parseFloat(parts[0]);
    humid = parseFloat(parts[1]);
  }

  if (!isNaN(temp)) {
    document.getElementById('tempValue').textContent = temp.toFixed(1);
    const pct = Math.max(0, Math.min(100, (temp / 50) * 100));
    document.getElementById('tempBar').style.width = pct + '%';
  }
  if (!isNaN(humid)) {
    document.getElementById('humidVal').textContent = humid.toFixed(0) + '%';
  }
  document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString('th-TH');
}

// ── Light Controls ───────────────────────────────────────────────
function toggleLight(on) {
  lightOn = on;
  updateBulbVisual();
  document.getElementById('lightState').textContent = on ? 'เปิด' : 'ปิด';
  document.getElementById('lightState').style.color = on ? 'var(--yellow)' : 'var(--text3)';

  if (!on) {
    // ปิดไฟ → dim brightness ด้วย
    document.getElementById('brightnessSlider').value = 0;
    onBrightnessInput(0);
  }

  publish(cfg.topicLight, on ? '1' : '0');
  log('ok', 'Light', on ? 'เปิดหลอดไฟ' : 'ปิดหลอดไฟ');
}

function onBrightnessInput(val) {
  brightness = parseInt(val);
  document.getElementById('brightnessValue').textContent = brightness + '%';
  updateSliderTrack(brightness);
  updateBulbVisual();
  updatePresetHighlight(brightness);
}

function publishBrightness(val) {
  brightness = parseInt(val);
  if (brightness > 0 && !lightOn) {
    lightOn = true;
    document.getElementById('lightToggle').checked = true;
    document.getElementById('lightState').textContent = 'เปิด';
    document.getElementById('lightState').style.color = 'var(--yellow)';
    publish(cfg.topicLight, '1');
  }
  publish(cfg.topicBright, String(brightness));
  log('ok', 'Brightness', brightness + '%');
}

function setPreset(val) {
  document.getElementById('brightnessSlider').value = val;
  onBrightnessInput(val);
  publishBrightness(val);
}

function updateBulbVisual() {
  const on = lightOn && brightness > 0;
  const glow = document.getElementById('bulbGlow');
  const svg  = document.getElementById('bulbSvg');
  const body = document.getElementById('bulbBody');

  glow.classList.toggle('on', on);
  svg.classList.toggle('on', on);

  const alpha = brightness / 100;
  if (on) {
    body.setAttribute('fill', `url(#bulbGrad)`);
    body.style.opacity = 0.4 + alpha * 0.6;
    glow.style.opacity = alpha * 0.8;
  } else {
    body.setAttribute('fill', 'url(#bulbGradOff)');
    body.style.opacity = '';
    glow.style.opacity = '0';
  }
}

function updateSliderTrack(val) {
  const slider = document.getElementById('brightnessSlider');
  slider.style.setProperty('--pct', val + '%');
}

function updatePresetHighlight(val) {
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.classList.toggle('active', parseInt(btn.textContent) === val);
  });
}

// ── Publish ──────────────────────────────────────────────────────
function publish(topic, payload) {
  if (!client || !client.connected) {
    log('warn', 'ไม่ได้เชื่อมต่อ', 'ไม่สามารถส่งข้อมูล');
    return;
  }
  client.publish(topic, payload, { qos: 1 }, (err) => {
    if (err) log('err', 'Publish ล้มเหลว', topic);
    else log('ok', 'TX', `[${topic}] ${payload}`);
  });
}

// ── Status Helpers ───────────────────────────────────────────────
function setStatus(state) {
  const pill = document.getElementById('statusPill');
  const dot  = document.getElementById('statusDot');
  const txt  = document.getElementById('statusText');
  const mqttBadge = document.getElementById('mqttBadge');
  const mqttInd   = document.getElementById('mqttIndicator');

  pill.className = 'status-pill';
  mqttBadge.dataset.state = 'off';
  mqttInd.className = 'status-indicator';

  if (state === 'connected') {
    pill.classList.add('connected');
    txt.textContent = 'เชื่อมต่อแล้ว';
    mqttBadge.dataset.state = 'on';
    mqttInd.classList.add('on');
    document.getElementById('mqttDetail').textContent = cfg.broker;
  } else if (state === 'disconnected') {
    pill.classList.add('disconnected');
    txt.textContent = 'ไม่ได้เชื่อมต่อ';
    document.getElementById('mqttDetail').textContent = 'ไม่ได้เชื่อมต่อ';
    stopUptimeTimer();
  } else {
    txt.textContent = 'กำลังเชื่อมต่อ...';
    mqttBadge.dataset.state = 'warn';
    mqttInd.classList.add('warn');
    document.getElementById('mqttDetail').textContent = 'กำลังเชื่อมต่อ...';
  }
}

function updateEspStatus() {
  const badge = document.getElementById('espBadge');
  const ind   = document.getElementById('espIndicator');
  const detail = document.getElementById('espDetail');
  badge.dataset.state = 'on';
  ind.className = 'status-indicator on';
  detail.textContent = 'อัปเดตล่าสุด: ' + new Date().toLocaleTimeString('th-TH');
}

// ── Topics Display ───────────────────────────────────────────────
function populateTopicLabels() {
  document.getElementById('topicTemp').textContent   = cfg.topicTemp;
  document.getElementById('topicLight').textContent  = cfg.topicLight;
  document.getElementById('topicBright').textContent = cfg.topicBright;
}

// ── Uptime ───────────────────────────────────────────────────────
function startUptimeTimer() {
  stopUptimeTimer();
  uptimeTimer = setInterval(() => {
    if (!connectedAt) return;
    const sec = Math.floor((Date.now() - connectedAt) / 1000);
    const m = Math.floor(sec / 60), s = sec % 60;
    document.getElementById('uptimeVal').textContent =
      (m > 0 ? m + 'น ' : '') + s + 'ว';
  }, 1000);
}
function stopUptimeTimer() {
  if (uptimeTimer) { clearInterval(uptimeTimer); uptimeTimer = null; }
  document.getElementById('uptimeVal').textContent = '--';
}

// ── Activity Log ─────────────────────────────────────────────────
function log(type, tag, msg) {
  const body = document.getElementById('logBody');
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  const time = new Date().toLocaleTimeString('th-TH', { hour12: false });
  entry.innerHTML = `
    <span class="log-time">${time}</span>
    <span class="log-tag log-tag--${type}">${tag}</span>
    <span class="log-msg">${escHtml(String(msg))}</span>
  `;
  body.appendChild(entry);
  body.scrollTop = body.scrollHeight;
  // Keep max 120 entries
  while (body.children.length > 120) body.removeChild(body.firstChild);
}

function clearLog() {
  document.getElementById('logBody').innerHTML = '';
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Settings Modal ───────────────────────────────────────────────
function openSettings() {
  const m = document.getElementById('modalOverlay');
  document.getElementById('cfgBroker').value    = cfg.broker;
  document.getElementById('cfgClientId').value  = cfg.clientId;
  document.getElementById('cfgUsername').value  = cfg.username;
  document.getElementById('cfgPassword').value  = cfg.password;
  document.getElementById('cfgTopicTemp').value  = cfg.topicTemp;
  document.getElementById('cfgTopicLight').value = cfg.topicLight;
  document.getElementById('cfgTopicBright').value= cfg.topicBright;
  m.classList.add('open');
}

function closeSettings(e) {
  if (e && e.target !== document.getElementById('modalOverlay')) return;
  document.getElementById('modalOverlay').classList.remove('open');
}

function saveSettings() {
  cfg = {
    broker:      document.getElementById('cfgBroker').value.trim()     || DEFAULTS.broker,
    clientId:    document.getElementById('cfgClientId').value.trim()   || DEFAULTS.clientId,
    username:    document.getElementById('cfgUsername').value.trim(),
    password:    document.getElementById('cfgPassword').value,
    topicTemp:   document.getElementById('cfgTopicTemp').value.trim()  || DEFAULTS.topicTemp,
    topicLight:  document.getElementById('cfgTopicLight').value.trim() || DEFAULTS.topicLight,
    topicBright: document.getElementById('cfgTopicBright').value.trim()|| DEFAULTS.topicBright,
  };
  saveConfig(cfg);
  populateTopicLabels();
  document.getElementById('modalOverlay').classList.remove('open');
  connect();
}

function resetDefaults() {
  cfg = { ...DEFAULTS, clientId: 'dashboard_' + Math.random().toString(36).slice(2, 7) };
  document.getElementById('cfgBroker').value    = cfg.broker;
  document.getElementById('cfgClientId').value  = cfg.clientId;
  document.getElementById('cfgUsername').value  = '';
  document.getElementById('cfgPassword').value  = '';
  document.getElementById('cfgTopicTemp').value  = cfg.topicTemp;
  document.getElementById('cfgTopicLight').value = cfg.topicLight;
  document.getElementById('cfgTopicBright').value= cfg.topicBright;
}
