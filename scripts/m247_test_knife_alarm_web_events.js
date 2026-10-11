'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const appPath = path.join(root, 'deployment', 'mage_vl4b', 'm247_knife_alarm_web_source', 'static', 'app.js');

function node(id = '') {
  return {
    id,
    textContent: '',
    className: '',
    disabled: false,
    value: '',
    files: [],
    dataset: {},
    style: {},
    classList: { add() {}, remove() {} },
    addEventListener() {},
    querySelector(selector) {
      if (selector === 'b' || selector === 'span') {
        this.children ||= {};
        this.children[selector] ||= node(`${id}-${selector}`);
        return this.children[selector];
      }
      return null;
    },
    pause() {},
    play: async () => {},
    load() {},
    removeAttribute() {},
    getContext() {
      return {
        drawImage() {},
        getImageData() { return { data: new Uint8ClampedArray(448 * 448 * 4) }; },
      };
    },
  };
}

const selectors = [
  '#source-video', '#capture-canvas', '#camera', '#video-file', '#stop', '#prompt-form',
  '#run', '#answer', '#health', '#proof-badge', '#source-status', '#source-proof',
  '#alarm-card', '#alarm-icon', '#alarm-kicker', '#alarm-title', '#alarm-detail', '#knife-verdict',
  '#knife-score', '#alarm-latency', '#evidence-sha', '#alarm-policy', '#last-result-status',
  '#window-sequences', '#build-kernel', '#realtime-boundary', '#frame-count', '#window-count',
  '#load-count', '#prompt', '#max-tokens', '#person-count', '#person-actions', '#fast-path-latency',
];
const nodes = Object.fromEntries(selectors.map((selector) => [selector, node(selector)]));
nodes['#prompt'].value = '[TELLME_KNIFE_BINARY_V1]';
nodes['#max-tokens'].value = '1';
nodes['#source-video'].readyState = 2;
nodes['#source-video'].videoWidth = 448;
nodes['#source-video'].videoHeight = 448;
nodes['.file-button'] = node('.file-button');

const stages = ['capture', 'window', 'vision', 'prefill', 'decode'].map((name) => {
  const item = node(`stage-${name}`);
  item.dataset.stage = name;
  return item;
});

const context = {
  console,
  Uint8Array,
  Uint8ClampedArray,
  Date,
  JSON,
  Number,
  document: {
    title: '',
    querySelector(selector) { return nodes[selector] || null; },
    querySelectorAll(selector) { return selector === '#stages li' ? stages : []; },
  },
  navigator: { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [] }) } },
  URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
  EventSource: class {
    addEventListener() {}
    close() {}
  },
  fetch: async () => ({
    ok: true,
    json: async () => ({
      status: 'running',
      buffer: { accepted_frames: 0, overwritten_frames: 0 },
      windows_started: 0,
      windows_completed: 0,
      runtime_load_count: 1,
      knife_alarm_state: 'REVIEW',
    }),
  }),
  setInterval: () => 1,
  clearInterval() {},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(appPath, 'utf8'), context, { filename: appPath });

function dispatch(name, payload) {
  context.__eventName = name;
  context.__payload = payload;
  vm.runInContext('handleEvent(__eventName, __payload)', context);
}

dispatch('window_begin', { sequences: [20, 21, 22, 23] });
dispatch('knife_observation', {
  verdict: 'PRESENT',
  knife_score: 0.9123,
  evidence_sha256: 'a'.repeat(64),
  text: '1',
});
dispatch('knife_alarm', {
  state: 'ALARM',
  effective_verdict: 'PRESENT',
  calibration_required: true,
  observation: { sequences: [20, 21, 22, 23] },
});
assert.strictEqual(nodes['#alarm-card'].className, 'alarm-card alarm');
assert.strictEqual(nodes['#alarm-icon'].textContent, '⚠');
assert.strictEqual(nodes['#alarm-title'].textContent, '检测到刀具');
assert.strictEqual(nodes['#knife-verdict'].textContent, 'PRESENT');
assert.strictEqual(nodes['#knife-score'].textContent, '0.9123');
assert.strictEqual(nodes['#evidence-sha'].textContent, 'a'.repeat(64));
assert.match(nodes['#alarm-policy'].textContent, /阈值未校准/);
assert.match(context.document.title, /刀具报警/);

dispatch('complete', {
  total_ms: 12345.6,
  proof: { result: 'PASS', build_id: '0x4D395832', kernel: 'mage_m120_m89x2_0' },
});
assert.strictEqual(nodes['#proof-badge'].textContent, 'FPGA PASS');
assert.strictEqual(nodes['#build-kernel'].textContent, '0x4D395832 / mage_m120_m89x2_0');
assert.strictEqual(nodes['#realtime-boundary'].textContent, '当前窗口 12.3 s；目标 < 5 s');

dispatch('knife_alarm', {
  state: 'SAFE',
  effective_verdict: 'ABSENT',
  calibration_required: true,
  observation: { sequences: [24, 25, 26, 27] },
});
assert.strictEqual(nodes['#alarm-card'].className, 'alarm-card safe');
assert.strictEqual(nodes['#alarm-title'].textContent, '暂未检测到刀具');

dispatch('knife_alarm', {
  state: 'REVIEW',
  effective_verdict: 'UNCERTAIN',
  calibration_required: true,
  observation: { sequences: [28, 29, 30, 31] },
});
assert.strictEqual(nodes['#alarm-card'].className, 'alarm-card review');
assert.strictEqual(nodes['#alarm-title'].textContent, '需要复核');

dispatch('safety_result', {
  window_index: 9,
  window_sequences: [36, 37, 38, 39],
  evidence_sha256: 'b'.repeat(64),
  capture_to_result_ms: 820,
  target_update_period_ms: 5000,
  realtime_deadline_met: true,
  person_count: 2,
  people: [
    { track_id: 3, action: 'WORKING', action_score: 0.92 },
    { track_id: 8, action: 'WALKING', action_score: 0.81 },
  ],
  knife: { verdict: 'PRESENT', score: 0.94 },
  alarm: { active: true, state: 'ALARM', icon: '⚠', badge_text: '刀具报警' },
});
assert.strictEqual(nodes['#person-count'].textContent, '2');
assert.match(nodes['#person-actions'].textContent, /人物 #3: WORKING/);
assert.match(nodes['#person-actions'].textContent, /人物 #8: WALKING/);
assert.strictEqual(nodes['#fast-path-latency'].textContent, '0.82 s / 5.0 s');
assert.match(nodes['#realtime-boundary'].textContent, /达到 5000 ms/);
assert.strictEqual(nodes['#alarm-card'].className, 'alarm-card alarm');
assert.strictEqual(nodes['#alarm-icon'].textContent, '⚠');
assert.strictEqual(nodes['#evidence-sha'].textContent, 'b'.repeat(64));

dispatch('window_error', { error: 'synthetic failure' });
assert.strictEqual(nodes['#proof-badge'].textContent, 'NOT ACCEPTED');
assert.match(nodes['#answer'].textContent, /synthetic failure/);
assert.strictEqual(nodes['#alarm-card'].className, 'alarm-card review');

const result = {
  gate: 'M247-knife-alarm-web-event-state',
  status: 'PASS',
  cases: ['ALARM', 'SAFE', 'REVIEW', 'FPGA_PROOF', 'WINDOW_ERROR'],
  scope: 'Offline mocked DOM/SSE state transitions only; not browser visual QA or board evidence.',
};
const resultPath = path.join(root, 'deployment', 'mage_vl4b', 'M247_KNIFE_ALARM_WEB_EVENT_RESULT.json');
fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(result, null, 2));

const m248Result = {
  gate: 'M248-fast-safety-web-event-state',
  status: 'PASS',
  cases: ['PERSON_ACTIONS', 'KNIFE_ALARM_ICON', 'EVIDENCE_HASH', 'LATENCY_DEADLINE'],
  scope: 'Offline mocked DOM/SSE state transition only; not detector accuracy, board, browser visual or real-video evidence.',
};
const m248ResultPath = path.join(root, 'deployment', 'mage_vl4b', 'M248_FAST_SAFETY_WEB_EVENT_RESULT.json');
fs.writeFileSync(m248ResultPath, `${JSON.stringify(m248Result, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(m248Result, null, 2));
