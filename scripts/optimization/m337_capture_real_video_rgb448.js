#!/usr/bin/env node
// Offline only: run unchanged M335 drawCover/sendFrame into a loopback receiver.
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const path = require('path');
let chromium;
try {
  ({ chromium } = require('playwright-core'));
} catch {
  ({ chromium } = require(path.resolve(path.dirname(process.execPath), '../node_modules/playwright-core')));
}

const root = path.resolve(__dirname, '../..');
const candidateStatic = path.join(root, 'deployment/mage_vl4b/optimization_v1/candidates/M335-manual-web-review-02/static');
const releaseStatic = path.join(root, 'experiments/m335_manual_web_review/static');
const staticRoot = fs.existsSync(candidateStatic) ? candidateStatic : releaseStatic;
const chrome = process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const fixedTimes = [1.0, 5.0, 10.0, 15.0, 19.0];
const sha = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');

async function fileSha(file) {
  const hash = crypto.createHash('sha256');
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
}

async function main() {
  const [, , inputArg, outputArg, mode = 'fixed5'] = process.argv;
  if (!inputArg || !outputArg || !['fixed5', 'all2fps'].includes(mode)) {
    throw new Error('usage: node m337_capture_real_video_rgb448.js VIDEO.mp4 NEW_OUTPUT_DIR [fixed5|all2fps]');
  }
  const videoPath = path.resolve(inputArg);
  const output = path.resolve(outputArg);
  if (!fs.statSync(videoPath).isFile() || path.extname(videoPath).toLowerCase() !== '.mp4') throw new Error('input must be an MP4 file');
  if (fs.existsSync(output)) throw new Error(`output already exists; refusing overwrite: ${output}`);
  fs.mkdirSync(output, { recursive: true });
  const posts = [];
  const server = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/api/4b/video/live/frame') {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      posts.push({ bytes: Buffer.concat(chunks), contentType: req.headers['content-type'] });
      res.writeHead(202, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ accepted: true, sequence: posts.length - 1 }));
      return;
    }
    const name = req.url === '/' ? 'index.html' : req.url?.slice(1);
    if (!['index.html', 'app.js', 'style.css'].includes(name)) { res.writeHead(404); res.end(); return; }
    const type = name.endsWith('.js') ? 'text/javascript' : name.endsWith('.css') ? 'text/css' : 'text/html';
    res.writeHead(200, { 'Content-Type': `${type}; charset=utf-8` });
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
    const metadata = await page.locator('#source-video').evaluate(el => ({ duration: el.duration, size: [el.videoWidth, el.videoHeight] }));
    const times = mode === 'fixed5' ? fixedTimes : Array.from(
      { length: Math.floor((metadata.duration - 0.05) * 2) + 1 }, (_, index) => index / 2);
    if (times.length < 1 || times.length > 120) throw new Error(`unexpected frame plan length: ${times.length}`);
    const rows = [];
    for (const [index, seconds] of times.entries()) {
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
        const rgb = drawCover();
        const digest = await crypto.subtle.digest('SHA-256', rgb);
        const browserSha256 = [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, '0')).join('');
        const png = document.querySelector('#capture-canvas').toDataURL('image/png');
        started = true;
        await sendFrame();
        return { requestedSeconds, actualSeconds: element.currentTime, duration: element.duration,
          sourceSize: [element.videoWidth, element.videoHeight], browserSha256, browserBytes: rgb.length, png };
      }, seconds);
      if (posts.length !== index + 1) throw new Error(`expected ${index + 1} loopback posts, got ${posts.length}`);
      const received = posts[index];
      if (received.bytes.length !== 448 * 448 * 3 || capture.browserBytes !== received.bytes.length ||
          capture.browserSha256 !== sha(received.bytes) || received.contentType !== 'application/x-tellme-rgb448') {
        throw new Error(`browser/receiver mismatch at time ${seconds}`);
      }
      const stem = `frame_${String(index).padStart(3, '0')}`;
      fs.writeFileSync(path.join(output, `${stem}.rgb448.bin`), received.bytes);
      fs.writeFileSync(path.join(output, `${stem}.png`), Buffer.from(capture.png.split(',', 2)[1], 'base64'));
      rows.push({ index, requestedSeconds: seconds, actualSeconds: capture.actualSeconds,
        rgbSha256: capture.browserSha256, pngSha256: await fileSha(path.join(output, `${stem}.png`)),
        rgbFile: `${stem}.rgb448.bin`, pngFile: `${stem}.png` });
    }
    const result = { gate: 'M337-real-video-browser-RGB448-offline', status: 'PASS_BROWSER_TO_LOOPBACK',
      sourceVideo: videoPath, sourceVideoSha256: await fileSha(videoPath),
      appJsSha256: await fileSha(path.join(staticRoot, 'app.js')),
      browserVersion: browser.version(), sourceSize: metadata.size, frameShape: [448, 448, 3],
      samplePlan: mode, requestedTimesSeconds: times, rows,
      boundary: 'Deterministic browser seeks at fixed times; not a wall-clock streaming run. Loopback only; no KV260, detector accuracy or alarm validation.' };
    fs.writeFileSync(path.join(output, 'RESULT.json'), JSON.stringify(result, null, 2) + '\n');
    process.stdout.write(JSON.stringify({ video: path.basename(videoPath), status: result.status, frames: rows.length,
      appJsSha256: result.appJsSha256 }) + '\n');
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
