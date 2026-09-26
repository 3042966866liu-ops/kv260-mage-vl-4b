const $ = (selector) => document.querySelector(selector);
const video = $('#source-video');
const canvas = $('#capture-canvas');
const camera = $('#camera');
const fileInput = $('#video-file');
const fileButton = document.querySelector('.file-button');
const stop = $('#stop');
const form = $('#prompt-form');
const run = $('#run');
const answer = $('#answer');
const health = $('#health');
const badge = $('#proof-badge');
const sourceStatus = $('#source-status');
const sourceProof = $('#source-proof');

let media = null;
let fileUrl = null;
let sourceMode = 'unselected';
let sourceLabel = '';
let captureTimer = null;
let eventStream = null;
let started = false;
let sending = false;
let lastComplete = null;
let currentWindowStartedAt = null;

function setText(selector, value) {
  const node = $(selector);
  if (node) node.textContent = value;
}

function setSource(mode, label, message) {
  sourceMode = mode;
  sourceLabel = label;
  sourceProof.textContent = mode === 'browser-camera'
    ? '浏览器摄像头（实时现场源）'
    : `${label}（本地循环回放）`;
  sourceStatus.textContent = message;
  video.classList.add('visible');
  stop.disabled = false;
}

function releaseVisualSource() {
  media?.getTracks().forEach((track) => track.stop());
  media = null;
  video.pause();
  video.srcObject = null;
  video.removeAttribute('src');
  video.load();
  if (fileUrl) URL.revokeObjectURL(fileUrl);
  fileUrl = null;
  fileInput.value = '';
  sourceMode = 'unselected';
  sourceLabel = '';
  sourceProof.textContent = '未选择';
}

function stage(name, state = '', detail = '') {
  const item = [...document.querySelectorAll('#stages li')]
    .find((candidate) => candidate.dataset.stage === name);
  if (!item) return;
  item.className = state;
  if (detail) item.querySelector('span').textContent = detail;
}

function setAlarm(state, detail, kicker = '最近窗口状态') {
  const normalized = ['ALARM', 'SAFE', 'REVIEW'].includes(state) ? state : 'REVIEW';
  const labels = { ALARM: '检测到刀具', SAFE: '暂未检测到刀具', REVIEW: '需要复核' };
  const icons = { ALARM: '⚠', SAFE: '✓', REVIEW: '?' };
  const card = $('#alarm-card');
  card.className = `alarm-card ${normalized.toLowerCase()}`;
  setText('#alarm-icon', icons[normalized]);
  setText('#alarm-kicker', kicker);
  setText('#alarm-title', labels[normalized]);
  setText('#alarm-detail', detail || '等待新的可核查窗口');
  document.title = normalized === 'ALARM'
    ? '⚠ 刀具报警 · TeLLMe KV260'
    : 'TeLLMe · KV260 刀具安全监控';
}

function handleSafetyResult(data) {
  const people = Array.isArray(data.people) ? data.people : [];
  const alarm = data.alarm || {};
  const knife = data.knife || {};
  const latency = Number(data.capture_to_result_ms);
  const target = Number(data.target_update_period_ms);
  const actionText = people.length
    ? people.map((person) => `人物 #${person.track_id}: ${person.action || 'UNKNOWN'} (${Number(person.action_score || 0).toFixed(2)})`).join('；')
    : '当前窗口未检测到人物。';
  setText('#person-count', String(data.person_count ?? people.length));
  setText('#person-actions', actionText);
  setText('#knife-verdict', knife.verdict || 'UNCERTAIN');
  setText('#knife-score', Number.isFinite(Number(knife.score)) ? Number(knife.score).toFixed(4) : '—');
  setText('#evidence-sha', data.evidence_sha256 || '—');
  setText('#fast-path-latency', Number.isFinite(latency)
    ? `${(latency / 1000).toFixed(2)} s / ${(target / 1000).toFixed(1)} s`
    : '—');
  setText('#realtime-boundary', data.realtime_deadline_met
    ? `快速安全通道 ${latency} ms：达到 ${target} ms 更新周期`
    : `快速安全通道 ${latency} ms：超过 ${target} ms 更新周期`);
  setAlarm(
    alarm.state || 'REVIEW',
    alarm.active
      ? `${alarm.icon || '⚠'} ${alarm.badge_text || '刀具报警'} · 证据 ${String(data.evidence_sha256 || '').slice(0, 12)}…`
      : `人物动作：${actionText}`,
    alarm.active ? '快速安全事件已触发' : '快速安全通道',
  );
}

function drawCover() {
  const context = canvas.getContext('2d', { willReadFrequently: true });
  const width = video.videoWidth;
  const height = video.videoHeight;
  const side = Math.min(width, height);
  context.drawImage(video, (width - side) / 2, (height - side) / 2, side, side, 0, 0, 448, 448);
  const rgba = context.getImageData(0, 0, 448, 448).data;
  const rgb = new Uint8Array(448 * 448 * 3);
  let cursor = 0;
  for (let index = 0; index < rgba.length; index += 4) {
    rgb[cursor++] = rgba[index];
    rgb[cursor++] = rgba[index + 1];
    rgb[cursor++] = rgba[index + 2];
  }
  return rgb;
}

async function sendFrame() {
  if (!started || sending || video.readyState < 2) return;
  sending = true;
  try {
    const response = await fetch('/api/4b/video/live/frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-tellme-rgb448' },
      body: drawCover(),
    });
    if (!response.ok) throw new Error((await response.json()).error || `HTTP ${response.status}`);
  } catch (error) {
    stage('capture', 'fail', error.message);
  } finally {
    sending = false;
  }
}

function handleObservation(data) {
  const score = Number(data.knife_score);
  setText('#knife-verdict', data.verdict || 'UNCERTAIN');
  setText('#knife-score', Number.isFinite(score) ? score.toFixed(4) : '—');
  setText('#evidence-sha', data.evidence_sha256 || '—');
  answer.textContent = data.text === '1'
    ? '模型受限输出：1（刀具出现候选，等待报警状态机确认）'
    : '模型受限输出：0（未见刀具候选，连续两个低分窗口后才解除报警）';
}

function handleAlarm(data) {
  const observation = data.observation || {};
  const sequences = observation.sequences || [];
  const elapsed = currentWindowStartedAt === null ? null : Date.now() - currentWindowStartedAt;
  const elapsedText = elapsed === null ? '—' : `${(elapsed / 1000).toFixed(1)} s`;
  setText('#alarm-latency', elapsedText);
  setText('#alarm-policy', data.calibration_required
    ? '阈值未校准；阳性立即报警，连续 2 次阴性解除'
    : '目标场景阈值已校准');
  setText('#last-result-status', `${data.state} · 窗口 ${sequences.join(', ') || '—'}`);
  setAlarm(
    data.state,
    `判定 ${data.effective_verdict || 'UNCERTAIN'} · 窗口 ${sequences.join(', ') || '—'} · ${elapsedText}`,
    data.state === 'ALARM' ? '安全事件已触发' : '最近窗口状态',
  );
}

function handleEvent(name, data) {
  if (name === 'runtime') {
    health.className = `health ${data.status === 'ready' ? 'ready' : 'cold'}`;
    health.querySelector('b').textContent = data.status === 'ready' ? 'M246 runtime 就绪' : 'runtime 已关闭';
  }
  if (name === 'frame') stage('capture', 'active', `已接收 ${data.sequence + 1} 帧`);
  if (name === 'window_begin') {
    currentWindowStartedAt = Date.now();
    lastComplete = null;
    stage('window', 'active', `序号 ${data.sequences.join(', ')}`);
    setText('#window-sequences', data.sequences.join(', '));
    stage('vision', 'active', '准备视觉塔');
    setText('#last-result-status', '窗口推理中');
  }
  if (name === 'stage') stage(data.name, 'active', data.label);
  if (name === 'vision_layer_begin') stage('vision', 'active', `第 ${data.index + 1}/24 层`);
  if (name === 'vision_heartbeat') stage('vision', 'active', `第 ${data.index + 1}/24 层 · ${data.layer_elapsed_s.toFixed(0)}s`);
  if (name === 'vision_layer_pass') stage('vision', 'active', `已完成 ${data.index + 1}/24 层`);
  if (name === 'token') stage('decode', 'active', `受限 token ${data.token_id}`);
  if (name === 'knife_observation') handleObservation(data);
  if (name === 'knife_alarm') handleAlarm(data);
  if (name === 'safety_result') handleSafetyResult(data);
  if (name === 'complete') {
    lastComplete = data;
    badge.className = 'badge pass';
    badge.textContent = 'FPGA PASS';
    const proof = data.proof || {};
    setText('#build-kernel', `${proof.build_id || '—'} / ${proof.kernel || '—'}`);
    setText('#realtime-boundary', `当前窗口 ${(data.total_ms / 1000).toFixed(1)} s；目标 < 5 s`);
  }
  if (name === 'window_complete') {
    stage('window', 'done', `完成 ${data.sequences.join(', ')}`);
    if (lastComplete?.proof?.result === 'PASS') stage('decode', 'done', '0/1 判定完成');
    refresh();
  }
  if (name === 'window_error') {
    badge.className = 'badge fail';
    badge.textContent = 'NOT ACCEPTED';
    answer.textContent = `本窗口失败：${data.error}`;
    setText('#last-result-status', '窗口失败');
    setAlarm('REVIEW', '本窗口没有形成可接受证据', '故障可见');
  }
}

function connectEvents() {
  eventStream?.close();
  eventStream = new EventSource('/api/4b/video/live/events?after=0');
  const names = [
    'runtime', 'frame', 'window_begin', 'stage', 'vision_layer_begin',
    'vision_heartbeat', 'vision_layer_pass', 'token', 'knife_observation',
    'knife_alarm', 'safety_result', 'complete', 'window_complete', 'window_error',
  ];
  for (const name of names) {
    eventStream.addEventListener(name, (event) => handleEvent(name, JSON.parse(event.data)));
  }
  eventStream.onerror = () => {
    health.className = 'health cold';
    health.querySelector('b').textContent = 'SSE 重连中';
  };
}

async function refresh() {
  try {
    const response = await fetch('/api/4b/video/live/status', { cache: 'no-store' });
    const status = await response.json();
    health.className = `health ${status.status === 'running' ? 'ready' : 'cold'}`;
    health.querySelector('b').textContent = status.status === 'running' ? 'M246 持续流运行中' : '服务待启动';
    setText('#frame-count', `${status.buffer?.accepted_frames || 0} / ${status.buffer?.overwritten_frames || 0}`);
    setText('#window-count', `${status.windows_started || 0} / ${status.windows_completed || 0}`);
    setText('#window-sequences', status.last_window_sequences?.length ? status.last_window_sequences.join(', ') : '—');
    setText('#load-count', `${status.runtime_load_count || 0}（要求始终为 1）`);
    if (status.knife_alarm_state) setAlarm(status.knife_alarm_state, '等待最新窗口事件');
    if (status.source_mode === 'browser-camera') sourceProof.textContent = '浏览器摄像头（实时现场源）';
    if (status.source_mode === 'uploaded-file-loop') sourceProof.textContent = `${status.source_label || '本地视频'}（本地循环回放）`;
  } catch {
    health.className = 'health cold';
    health.querySelector('b').textContent = '服务离线';
  }
}

camera.addEventListener('click', async () => {
  try {
    releaseVisualSource();
    media = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = media;
    await video.play();
    setSource('browser-camera', 'browser-camera', '摄像头已打开：这是持续到来的真实现场视频源。');
  } catch (error) {
    releaseVisualSource();
    answer.textContent = `无法打开摄像头：${error.message}`;
  }
});

fileInput.addEventListener('change', async () => {
  const file = fileInput.files?.[0];
  if (!file) return;
  if (file.type && !file.type.startsWith('video/')) {
    answer.textContent = '请选择浏览器可以解码的视频文件。';
    fileInput.value = '';
    return;
  }
  try {
    releaseVisualSource();
    fileUrl = URL.createObjectURL(file);
    video.src = fileUrl;
    video.loop = true;
    video.muted = true;
    await video.play();
    setSource('uploaded-file-loop', file.name, `正在本地循环播放 ${file.name}。浏览器只发送采样后的 RGB 帧，不上传完整视频文件。`);
  } catch (error) {
    releaseVisualSource();
    answer.textContent = `无法播放本地视频：${error.message}`;
  }
});

stop.addEventListener('click', () => {
  clearInterval(captureTimer);
  captureTimer = null;
  started = false;
  eventStream?.close();
  eventStream = null;
  releaseVisualSource();
  camera.disabled = false;
  fileInput.disabled = false;
  fileButton.classList.remove('disabled');
  stop.disabled = true;
  run.disabled = false;
  sourceStatus.textContent = '本地发送已停止。板端若正在推理，会完成当前窗口；不会再接收新帧。';
  stage('capture', '', '已停止');
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (sourceMode === 'unselected') {
    answer.textContent = '请先打开摄像头或选择本地视频。';
    return;
  }
  run.disabled = true;
  camera.disabled = true;
  fileInput.disabled = true;
  fileButton.classList.add('disabled');
  badge.className = 'badge pending';
  badge.textContent = '运行中';
  try {
    const response = await fetch('/api/4b/video/live/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: $('#prompt').value,
        max_new_tokens: Number($('#max-tokens').value),
        source_mode: sourceMode,
        source_label: sourceLabel,
      }),
    });
    if (!response.ok) throw new Error((await response.json()).error || `HTTP ${response.status}`);
    started = true;
    connectEvents();
    await sendFrame();
    captureTimer = setInterval(sendFrame, 500);
    stage('capture', 'active', sourceMode === 'browser-camera' ? '摄像头持续发送 2 FPS' : '本地视频循环发送 2 FPS');
  } catch (error) {
    run.disabled = false;
    camera.disabled = false;
    fileInput.disabled = false;
    fileButton.classList.remove('disabled');
    answer.textContent = `启动失败：${error.message}`;
    badge.className = 'badge fail';
    badge.textContent = 'NOT STARTED';
  }
});

refresh();
setInterval(refresh, 5000);
