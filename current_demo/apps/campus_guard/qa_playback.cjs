// Real browser interactions; prediction fixtures are SOFTWARE ONLY, never board evidence.
const {chromium}=require('C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..'),out=path.join(__dirname,'qa/playback');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  let fixture,activeUpload,mode='pending',calls=0,stateInFlight=0,maxStateInFlight=0;
 try{
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'networkidle'});
  fixture=await (await page.request.get('http://127.0.0.1:8765/api/state')).json();fixture.worker=null;fixture.events=[];
  await page.route('**/api/state',async route=>{stateInFlight++;maxStateInFlight=Math.max(maxStateInFlight,stateInFlight);try{await new Promise(r=>setTimeout(r,240));await route.fulfill({contentType:'application/json',body:JSON.stringify(fixture)})}finally{stateInFlight--}});
  await page.route('**/api/verify',async route=>{
   const b=route.request().postDataJSON();assert(activeUpload.cases.some(c=>c.id===b.case_id));assert.equal(b.upload_id,activeUpload.id);
   assert(await page.locator('#video-player').evaluate(v=>!v.paused),'A real video play must trigger the first submission');
   calls++;const id=calls.toString(16).padStart(32,'0'),c=activeUpload.cases.find(c=>c.id===b.case_id);
   fixture.events.unshift({id,kind:'live',upload_id:b.upload_id,case_id:b.case_id,decision:mode==='No'?'No':null,status:mode==='unknown'?'unknown':'queued',frame_path:c.frame_path,TEST_ONLY_SYNTHETIC:true});
   await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({id,status:'queued'})});
  });
  async function upload(id){
   const bytes=Buffer.concat([fs.readFileSync(path.join(root,`data/campus_demo_20261025/source/${id}.mp4`)),Buffer.from('\nSOFTWARE_PLAYBACK_TEST_ONLY')]);
   const done=page.waitForResponse(r=>r.url().endsWith('/frames')&&r.request().method()==='POST'&&r.status()===200);
   await page.locator('#video-file').setInputFiles({name:id+'_TEST_ONLY.mp4',mimeType:'video/mp4',buffer:bytes});activeUpload=await (await done).json();
   await page.waitForFunction(()=>document.querySelectorAll('.sample-frame').length===3&&!document.querySelector('#start-button').disabled);
  }
  assert(await page.locator('#knife-warning').isHidden());assert(await page.locator('#start-button').isDisabled());
  await upload('campus_03');await page.locator('#video-player').evaluate(v=>v.pause());assert.equal(calls,0);
  fixture.worker={ready:true,warm:true,supports_uploads:true,build:'SOFTWARE_FIXTURE_NOT_BOARD'};
  await page.waitForFunction(()=>document.querySelector('#connection span').textContent==='板卡已就绪');assert.equal(calls,0,'No inference while paused before the first job');
  const firstRequest=page.waitForResponse(r=>r.url().endsWith('/api/verify')&&r.status()===202);
  await page.locator('#video-player').evaluate(v=>v.play());await firstRequest;
  assert.equal(calls,1);assert(await page.locator('#knife-warning').isHidden(),'Pending must not trigger a warning');
  await page.locator('#video-player').evaluate(async v=>{v.pause();await v.play()});assert.equal(calls,1,'Pause/resume must not duplicate the task');
  fixture.events[0].decision='Yes';fixture.events[0].status='review';await page.locator('#knife-warning').waitFor({state:'visible'});
  assert(await page.locator('#video-alert-edge').isVisible());assert.equal(calls,1,'Yes must latch and stop the remaining samples');
  await page.evaluate(()=>{const e=document.createElement('div');e.id='test-watermark';e.textContent='软件界面测试样例 · 非新增板端识别结果';e.style='position:fixed;bottom:8px;left:25%;background:#163047;color:white;padding:12px;z-index:9999';document.body.append(e)});
  await page.screenshot({path:path.join(out,'positive_TEST_ONLY.png'),fullPage:true});await page.locator('#acknowledge-warning').click();assert(await page.locator('#knife-warning').isHidden());
  fixture.events=[];mode='No';await upload('campus_02');
  await page.waitForFunction(()=>document.querySelector('#recognition-status').hidden===true);
  assert.equal(calls,4);assert(await page.locator('#knife-warning').isHidden());assert(await page.locator('#video-alert-edge').isHidden());
  assert.equal(await page.locator('#status-text').textContent(),'');
  assert(!/采样画面未见刀具|No\b|TTFT|耗时/.test(await page.locator('body').innerText()));
  await page.screenshot({path:path.join(out,'negative_TEST_ONLY.png'),fullPage:true});
  await page.locator('#video-player').evaluate(async v=>{v.pause();v.currentTime=0;await v.play()});
  await page.waitForResponse(r=>r.url().endsWith('/api/state'));assert.equal(calls,4,'Replay must not silently rerun an already completed model job');
  fixture.events=[];mode='unknown';await upload('old_lab_candidate');
  await page.waitForFunction(()=>document.querySelector('#status-text').textContent.includes('识别未完成'));
  assert(await page.locator('#recognition-status').isVisible());assert(await page.locator('#knife-warning').isHidden());assert.equal(calls,5);
  assert(await page.locator('#task-select option[value="hand_holding_knife"]').isDisabled());assert.equal(maxStateInFlight,1,'Slow server must not accumulate overlapping state requests');
  await page.evaluate(()=>document.getElementById('test-watermark').remove());await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify({status:'PASS_PLAYBACK_AUTOSTART_SILENT_NEGATIVE_SOFTWARE_ONLY',play_event_starts_request:true,paused_before_start_no_request:true,resume_no_duplicate:true,yes_latched:true,no_result_text_or_alarm:true,unknown_not_negative:true,unsupported_question_disabled:true,no_TTFT:true,actual_uploads_and_sampling:3,synthetic_verify_requests:calls,slow_state_response_ms:240,max_state_requests_in_flight:maxStateInFlight,active_poll_after_response_ms:200,idle_poll_after_response_ms:1000,fixture_predictions_not_hardware:true,board_runs:0,model_runs:0,page_errors:errors},null,2));console.log('PASS_PLAYBACK_AUTOSTART_SILENT_NEGATIVE_SOFTWARE_ONLY');
 }finally{await page.unrouteAll({behavior:'ignoreErrors'});await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
