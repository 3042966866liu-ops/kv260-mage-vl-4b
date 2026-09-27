#!/usr/bin/env node
// Offline diagnostic: exercise the unchanged M335 page's drawCover/sendFrame path.
// This starts a loopback-only stub, never a board service or model runtime.
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const path = require('path');
let chromium;
try {
  ({ chromium } = require('playwright-core'));
} catch {
  // The bundled workspace runtime keeps node_modules next to node/bin.
  ({ chromium } = require(path.resolve(path.dirname(process.execPath), '../node_modules/playwright-core')));
}

const root = path.resolve(__dirname, '../..');
const candidateStatic = path.join(root, 'deployment/mage_vl4b/optimization_v1/candidates/M335-manual-web-review-02/static');
const releaseStatic = path.join(root, 'experiments/m335_manual_web_review/static');
const staticRoot = fs.existsSync(candidateStatic) ? candidateStatic : releaseStatic;
const chrome = process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const sha = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');

async function main() {
  const [, , videoArg, outputArg, secondsArg = '4.8'] = process.argv;
  if (!videoArg || !outputArg) throw new Error('usage: node m336_capture_actual_browser_rgb448.js VIDEO.mp4 OUTPUT_DIR [SECONDS]');
  const videoPath = path.resolve(videoArg);
  const output = path.resolve(outputArg);
  const seconds = Number(secondsArg);
  if (!fs.statSync(videoPath).isFile() || !Number.isFinite(seconds) || seconds < 0) throw new Error('invalid video or seconds');
  fs.mkdirSync(output, { recursive: true });
  const posts = [];
  const server = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/api/4b/video/live/frame') {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      const bytes = Buffer.concat(chunks);
      posts.push({ bytes, contentType: req.headers['content-type'] });
      res.writeHead(202, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ accepted: true, sequence: posts.length - 1 }));
      return;
    }
    const name = req.url === '/' ? 'index.html' : req.url?.slice(1);
    if (!['index.html', 'app.js', 'style.css'].includes(name)) {
      res.writeHead(404); res.end(); return;
    }
    const contentType = name.endsWith('.js') ? 'text/javascript' : name.endsWith('.css') ? 'text/css' : 'text/html';
    res.writeHead(200, { 'Content-Type': `${contentType}; charset=utf-8` });
    res.end(fs.readFileSync(path.join(staticRoot, name)));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ executablePath: chrome, headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' });
    await page.locator('#video-file').setInputFiles(videoPath);
    await page.waitForFunction(() => document.querySelector('#source-video').readyState >= 2);
    const capture = await page.evaluate(async (requestedSeconds) => {
      const element = document.querySelector('#source-video');
      element.pause();
      const target = Math.min(requestedSeconds, Math.max(0, element.duration - 0.05));
      if (Math.abs(element.currentTime - target) > 0.001) {
        await new Promise((resolve, reject) => {
          element.addEventListener('seeked', resolve, { once: true });
          element.addEventListener('error', reject, { once: true });
          element.currentTime = target;
        });
      }
      const rgb = drawCover(); // The actual, unchanged M335 app.js function.
      const digest = await crypto.subtle.digest('SHA-256', rgb);
      const hex = [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, '0')).join('');
      const png = document.querySelector('#capture-canvas').toDataURL('image/png');
      started = true; // Trigger only the original sendFrame() transport, not the model.
      await sendFrame();
      return {
        browserSha256: hex,
        browserBytes: rgb.length,
        png,
        requestedSeconds,
        actualSeconds: element.currentTime,
        videoWidth: element.videoWidth,
        videoHeight: element.videoHeight,
        duration: element.duration,
      };
    }, seconds);
    if (posts.length !== 1) throw new Error(`expected one received frame, got ${posts.length}`);
    const post = posts[0];
    const expectedBytes = 448 * 448 * 3;
    const transportSha256 = sha(post.bytes);
    const status = capture.browserBytes === expectedBytes && post.bytes.length === expectedBytes &&
      capture.browserSha256 === transportSha256 && post.contentType === 'application/x-tellme-rgb448'
      ? 'PASS_BROWSER_TO_BACKEND_BYTES' : 'FAIL_BROWSER_TO_BACKEND_BYTES';
    fs.writeFileSync(path.join(output, 'actual_browser_rgb448.bin'), post.bytes);
    fs.writeFileSync(path.join(output, 'actual_browser_view.png'), Buffer.from(capture.png.split(',', 2)[1], 'base64'));
    const result = {
      gate: 'M336-actual-M335-browser-RGB448-to-receiver', status,
      sourceVideo: videoPath, sourceVideoSha256: sha(fs.readFileSync(videoPath)),
      sourceAppJsSha256: sha(fs.readFileSync(path.join(staticRoot, 'app.js'))),
      browserName: 'Google Chrome', browserVersion: browser.version(),
      requestedSeconds: capture.requestedSeconds, actualSeconds: capture.actualSeconds,
      sourceSize: [capture.videoWidth, capture.videoHeight], videoDurationSeconds: capture.duration,
      frameShape: [448, 448, 3], frameBytes: post.bytes.length,
      contentType: post.contentType, browserSha256: capture.browserSha256,
      receiverSha256: transportSha256, pngSha256: sha(fs.readFileSync(path.join(output, 'actual_browser_view.png'))),
      boundary: 'Loopback receiver only; no KV260, detector, model, or automatic-alarm accuracy claim.',
    };
    fs.writeFileSync(path.join(output, 'RESULT.json'), JSON.stringify(result, null, 2) + '\n');
    process.stdout.write(JSON.stringify(result, null, 2) + '\n');
    if (status !== 'PASS_BROWSER_TO_BACKEND_BYTES') process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
