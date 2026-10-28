// Browser UI fixtures only. Images carry a watermark; never FPGA accuracy evidence.
const {chromium}=require('C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const root=path.resolve(__dirname,'../..'),base='http://127.0.0.1:8767',out=path.join(__dirname,'qa/alarm_no_seek09');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 let uploaded=0;page.on('request',r=>{if(r.url()===base+'/api/uploads'&&r.method()==='POST')uploaded++});let inputReady=false;let mock=await (await page.request.get(base+'/api/state')).json(),calls=0,completed=0,mode='pending',active=null;
 mock.events=[];mock.worker={ready:true,warm:true,supports_uploads:true,build:'SOFTWARE_ONLY_FIXTURE'};
 await page.route('**/api/state',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(mock)}));
 await page.route('**/api/uploads/*',async route=>{
  if(route.request().method()!=='GET')return route.continue();const r=await route.fetch();const d=await r.json();d.board_prepared=inputReady;await route.fulfill({response:r,json:d});
 });
 await page.route('**/api/verify',async route=>{
  const b=route.request().postDataJSON();assert(await page.locator('#video-player').evaluate(v=>!v.paused),'real video play must precede inference');calls++;
  const d=await (await page.request.get(base+'/api/uploads/'+b.upload_id)).json();assert(d.cases.some(c=>c.id===b.case_id));const c=d.cases.find(c=>c.id===b.case_id);
  active={id:crypto.randomBytes(16).toString('hex'),kind:'live',upload_id:b.upload_id,case_id:b.case_id,frame_path:c.frame_path,status:mode==='unknown'?'unknown':mode==='No'?'review':'running',decision:mode==='No'?'No':null,TEST_ONLY_SYNTHETIC:true};mock.events.unshift(active);
  await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({id:active.id,status:'queued'})});completed++;
 });
 async function watermark(){await page.evaluate(()=>{const e=document.createElement('div');e.id='qa-watermark';e.textContent='软件界面测试样例 · 非新增板端识别结果';e.style='position:fixed;bottom:8px;left:24%;padding:10px 18px;background:#17324b;color:white;z-index:99999;font-size:12px';document.body.append(e)})}
 async function upload(file){await page.locator('#video-file').setInputFiles(path.join(root,file));await page.waitForFunction(()=>document.querySelectorAll('.sample-frame').length===1);}
 async function waitCalls(n){for(let i=0;i<120&&completed<n;i++)await page.waitForTimeout(50);assert(completed>=n,'expected completed submission '+n)}
 try{
  await page.goto(base,{waitUntil:'networkidle'});assert(await page.locator('#knife-warning').isHidden());assert(await page.locator('#alarm-history').isHidden());
  await upload('data/campus_demo_20261025/source/campus_03.mp4');await page.locator('#input-preparation-notice').waitFor({state:'visible'});assert(await page.locator('#start-button').isDisabled());assert.equal(await page.locator('#start-button').innerText(),'画面准备中');assert.equal(calls,0);await page.locator('#video-player').evaluate(v=>v.play().catch(()=>{}));await page.waitForTimeout(300);assert(await page.locator('#video-player').evaluate(v=>v.paused));assert.equal(calls,0);await page.screenshot({path:path.join(out,'input_wait_TEST_ONLY.png'),fullPage:true});inputReady=true;await waitCalls(1);await page.waitForFunction(()=>document.querySelector('#status-text').textContent==='正在识别视频画面');assert.equal(calls,1);assert(await page.locator('#knife-warning').isHidden(),'pending never alarms');
  await page.locator('#video-player').evaluate(async v=>{v.pause();await v.play()});await page.waitForTimeout(400);assert.equal(calls,1,'pause/resume does not duplicate');
  mock.events.unshift({id:'f'.repeat(32),upload_id:'other',kind:'live',case_id:active.case_id,decision:'Yes',status:'review'});await page.waitForTimeout(400);assert(await page.locator('#knife-warning').isHidden(),'unrelated historical Yes never alarms');
  await page.locator('#video-player').evaluate(v=>{v.pause();v.currentTime=5.5});
  for(let i=0;i<40;i++){if(await page.locator('#video-player').evaluate(v=>!v.seeking&&Math.abs(v.currentTime-5.5)<.05))break;await page.waitForTimeout(50)}
  const alarmPosition=await page.locator('#video-player').evaluate(v=>v.currentTime);assert(Math.abs(alarmPosition-5.5)<.05);
  const sampleTime=(await (await page.request.get(base+'/api/uploads/'+active.upload_id)).json()).cases[0].timestamp_ms/1000;
  assert(Math.abs(sampleTime-alarmPosition)>1,'fixture must distinguish playback from sampled frame');
  active.decision='Yes';active.status='review';await page.locator('#knife-warning').waitFor({state:'visible'});assert(await page.locator('#video-alert-edge').isVisible());assert(await page.locator('#video-player').evaluate(v=>v.paused));assert(await page.locator('#alarm-history').isVisible());await page.waitForTimeout(300);assert(Math.abs((await page.locator('#video-player').evaluate(v=>v.currentTime))-alarmPosition)<.05,'alarm must not seek to sampled evidence');
  await watermark();await page.screenshot({path:path.join(out,'positive_TEST_ONLY.png'),fullPage:true});await page.locator('#acknowledge-warning').click();assert(await page.locator('#knife-warning').isHidden());
  mode='No';await upload('data/campus_demo_20261026/campus_12.mp4');await page.waitForFunction(()=>document.querySelector('#recognition-status').hidden&&document.querySelector('#start-button').textContent==='重新演示');assert.equal(calls,2);assert(await page.locator('#knife-warning').isHidden());assert(await page.locator('#alarm-history').isHidden());assert(await page.locator('#video-alert-edge').isHidden());
  assert(!/TTFT|耗时|无刀具|\bNo\b/.test(await page.locator('body').innerText()));await page.screenshot({path:path.join(out,'negative_TEST_ONLY.png'),fullPage:true});
  assert.equal(uploaded,2);await page.locator('#video-file').evaluate(e=>e.value='');await page.locator('#video-file').setInputFiles(path.join(root,'data/campus_demo_20261026/campus_12.mp4'));await waitCalls(3);await page.waitForFunction(()=>document.querySelector('#recognition-status').hidden);assert.equal(uploaded,2,'same exact video reuses prepared pixels, not a new upload');
  await page.locator('#start-button').click();await waitCalls(4);await page.waitForFunction(()=>document.querySelector('#start-button').textContent==='重新演示'&&!document.querySelector('#start-button').disabled);assert.equal(calls,4,'explicit replay makes a fresh job');
  mode='unknown';await page.locator('#start-button').click();await waitCalls(5);await page.waitForFunction(()=>document.querySelector('#status-text').textContent.includes('识别未完成'));assert.equal(calls,5);assert(await page.locator('#knife-warning').isHidden());
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'mobile_TEST_ONLY.png'),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
  const result={status:'PASS_LIVE_PRESENTATION_BROWSER_SOFTWARE_FIXTURES_ONLY',checks:['input wait visible above video and button named','early native play pauses with zero model submission','real play triggers job','pending quiet','resume no duplicate','unrelated Yes ignored','Yes huge alert and current-position pause without seeking to sample','No result and alarm hidden','no latency text','identical input reselect reuses bytes but creates fresh model job','explicit replay fresh job','failure not No','mobile no overflow'],fake_predictions:true,FPGA_runs:0};fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await page.unrouteAll({behavior:'ignoreErrors'});await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
