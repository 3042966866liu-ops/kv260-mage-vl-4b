import fs from 'node:fs';
import vm from 'node:vm';

const appPath = new URL('../deployment/mage_vl4b/m247_knife_alarm_web_source/static/app.js', import.meta.url);
const source = fs.readFileSync(appPath, 'utf8');
const listeners = new Map();
const intervals = [];
const fetchCalls = [];

function element(name) {
  return {
    name,
    textContent: '',
    className: '',
    disabled: false,
    value: '',
    files: [],
    readyState: 2,
    videoWidth: 448,
    videoHeight: 448,
    classList: { add() {}, remove() {} },
    addEventListener(type, callback) { listeners.set(`${name}:${type}`, callback); },
    querySelector() { return element(`${name}:child`); },
    pause() {},
    load() {},
    removeAttribute() {},
    async play() {},
  };
}

const nodes = new Map();
for (const selector of [
  '#source-video', '#capture-canvas', '#camera', '#video-file', '.file-button',
  '#stop', '#prompt-form', '#run', '#answer', '#health', '#proof-badge',
  '#source-status', '#source-proof', '#prompt', '#max-tokens',
]) nodes.set(selector, element(selector));
nodes.get('#prompt').value = '[TELLME_KNIFE_BINARY_V1]';
nodes.get('#max-tokens').value = '1';
nodes.get('#capture-canvas').getContext = () => ({
  drawImage() {},
  getImageData() { return { data: new Uint8ClampedArray(448 * 448 * 4) }; },
});

const stageItems = ['capture', 'window', 'vision', 'prefill', 'decode'].map((name) => ({
  dataset: { stage: name },
  className: '',
  querySelector() { return nodes.get(`#stage-${name}`) || nodes.set(`#stage-${name}`, element(`#stage-${name}`)).get(`#stage-${name}`); },
}));

const activeStatus = {
  status: 'running',
  mode: 'M254-dual-path-latest-only',
  fast_path: { runtime_load_count: 1 },
  semantic_review: { policy: 'alarm-only-capacity-one' },
  source_mode: 'browser-camera',
  source_label: 'M254-no-frame-readiness',
};

async function fetchMock(url, options = {}) {
  fetchCalls.push({ url, method: options.method || 'GET' });
  if (url.endsWith('/start')) {
    return {
      ok: false,
      status: 409,
      async json() { return { error: 'an M254 dual-path session is already active' }; },
    };
  }
  if (url.endsWith('/status')) {
    return { ok: true, status: 200, async json() { return activeStatus; } };
  }
  if (url.endsWith('/frame')) {
    return { ok: true, status: 202, async json() { return { accepted: true, sequence: 0 }; } };
  }
  throw new Error(`unexpected fetch ${url}`);
}

class EventSourceMock {
  constructor(url) { this.url = url; }
  addEventListener() {}
  close() {}
}

const context = {
  console,
  Uint8Array,
  Uint8ClampedArray,
  Date,
  JSON,
  Math,
  Number,
  String,
  document: {
    title: '',
    querySelector(selector) {
      if (!nodes.has(selector)) nodes.set(selector, element(selector));
      return nodes.get(selector);
    },
    querySelectorAll(selector) { return selector === '#stages li' ? stageItems : []; },
  },
  navigator: { mediaDevices: { async getUserMedia() { return { getTracks() { return []; } }; } } },
  URL: { createObjectURL() { return 'blob:test'; }, revokeObjectURL() {} },
  EventSource: EventSourceMock,
  fetch: fetchMock,
  setInterval(callback, delay) { intervals.push({ callback, delay }); return intervals.length; },
  clearInterval() {},
};
vm.runInNewContext(source, context, { filename: appPath.pathname });
await new Promise((resolve) => setTimeout(resolve, 0));

const fileInput = nodes.get('#video-file');
fileInput.files = [{ name: 'knife-test.mp4', type: 'video/mp4' }];
await listeners.get('#video-file:change')();
if (!nodes.get('#source-proof').textContent.includes('knife-test.mp4')) {
  throw new Error('selected local source was not retained');
}

await listeners.get('#prompt-form:submit')({ preventDefault() {} });
const framePosts = fetchCalls.filter((call) => call.url.endsWith('/frame') && call.method === 'POST');
if (framePosts.length !== 1) throw new Error(`expected one immediate frame POST, observed ${framePosts.length}`);
if (!nodes.get('#answer').textContent.includes('已接管门禁预热留下的 M254 会话')) {
  throw new Error(`attach message missing: ${nodes.get('#answer').textContent}`);
}
if (!nodes.get('#stage-capture').textContent.includes('已接管板端现有会话')) {
  throw new Error(`capture stage did not expose attachment: ${nodes.get('#stage-capture').textContent}`);
}
if (!intervals.some((item) => item.delay === 500)) throw new Error('2 FPS capture timer was not armed');

console.log(JSON.stringify({
  gate: 'M255-active-M254-session-browser-attach',
  status: 'PASS',
  start_conflict_status: 409,
  existing_session_attached: true,
  immediate_frame_posts: framePosts.length,
  capture_period_ms: 500,
  stale_backend_source_label_overwrites_selected_source: false,
}, null, 2));
console.log('M255_ACTIVE_SESSION_ATTACH_OFFLINE_PASS');
