// Actual browser -> fresh UUID -> actual board result. No routes, mocks or synthetic answers.
const {chromium}=require('C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const root=path.resolve(__dirname,'../..'),base='http://127.0.0.1:8766',out=path.join(root,'deployment/mage_vl4b/optimization_v1/runs/M544-live-browser-board-03');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
(async()=>{
 fs.mkdirSync(out,{recursive:false});const binding=JSON.parse(fs.readFileSync(path.join(__dirname,'LIVE_BINDING.json')));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(240000);
 const results=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.__actualPlayTimes=[];document.addEventListener('play',e=>{if(e.target.id==='video-player')window.__actualPlayTimes.push(Date.now())},true)});
 try{
  await page.goto(base,{waitUntil:'networkidle'});await page.waitForFunction(async()=>{const s=await(await fetch('/api/state',{cache:'no-store'})).json();return !!s.worker?.warm},null,{timeout:240000});
  const initial=await(await page.request.get(base+'/api/state')).json();assert.equal(initial.worker.package_manifest_sha256,binding.package_manifest_sha256);const session=initial.worker.session;
  for(const item of [{id:'campus03',file:'data/campus_demo_20261025/source/campus_03.mp4',expected:'Yes'},{id:'campus12',file:'data/campus_demo_20261026/campus_12.mp4',expected:'No'}]){
   const requested=page.waitForResponse(r=>r.url()===base+'/api/verify'&&r.request().method()==='POST',{timeout:240000});
   await page.locator('#video-file').setInputFiles(path.join(root,item.file));const response=await requested;assert.equal(response.status(),202);const request=await response.json(),submitted=response.request().postDataJSON();
   assert(!('expected_decision' in submitted));const playTimes=await page.evaluate(()=>window.__actualPlayTimes.slice());assert(playTimes.length>0,'Actual playback must precede request');
   console.log('ACTUAL_BOARD_REQUEST',item.id,request.id);
   await page.waitForFunction(async id=>{const s=await(await fetch('/api/state',{cache:'no-store'})).json();const e=s.events.find(x=>x.id===id);return e&&!['queued','running'].includes(e.status)},request.id,{timeout:240000});
   const state=await(await page.request.get(base+'/api/state')).json();const event=state.events.find(e=>e.id===request.id);assert.equal(event.decision,item.expected,'Actual unforced board decision');
   const evidence=path.join(root,'deployment/mage_vl4b/optimization_v1/runs/M544-live-board-results',session,request.id,'RESULT.json');assert(fs.existsSync(evidence));const proof=JSON.parse(fs.readFileSync(evidence));assert.equal(hash(evidence),event.result.evidence_sha256);assert.equal(proof.ui_job_id,request.id);assert.equal(proof.session,session);assert.equal(proof.package_manifest_sha256,binding.package_manifest_sha256);assert.equal(proof.decision,item.expected);assert.equal(proof.actual_full_vocab,151936);assert(proof.completed_request&&proof.argmax_verified&&proof.physical_calls>=324);
   if(item.expected==='Yes'){
    await page.locator('#knife-warning').waitFor({state:'visible'});assert(await page.locator('#video-alert-edge').isVisible());assert(await page.locator('#video-player').evaluate(v=>v.paused));assert(await page.locator('#alarm-history').isVisible());
   }else{
    await page.waitForFunction(()=>document.querySelector('#recognition-status').hidden&&document.querySelector('#knife-warning').hidden&&document.querySelector('#alarm-history').hidden);assert(await page.locator('#video-alert-edge').isHidden());assert(!/TTFT|耗时|无刀具|\bNo\b/.test(await page.locator('body').innerText()));
   }
   const screenshot=path.join(out,item.id+'_ACTUAL_BOARD.png');await page.screenshot({path:screenshot,fullPage:true});
   results.push({source:item.file,source_sha256:hash(path.join(root,item.file)),session,request_id:request.id,upload_id:submitted.upload_id,case_id:submitted.case_id,play_events:playTimes,proof_path:path.relative(root,evidence).replaceAll('\\','/'),proof_sha256:hash(evidence),actual_decision:proof.decision,TTFT_s:proof.TTFT_s,frame_sha256:proof.frame_sha256,pixel_sha256:proof.pixel_sha256,full_logits_sha256:proof.full_logits_sha256,physical_calls:proof.physical_calls,alarm_visible:await page.locator('#knife-warning').isVisible(),screenshot_sha256:hash(screenshot)});
   fs.writeFileSync(path.join(out,'PARTIAL.json'),JSON.stringify({actual_board_only:true,results},null,2));console.log('ACTUAL_BOARD_RETURNED',item.id,proof.decision,proof.TTFT_s);
  }
  assert.deepEqual(errors,[]);assert.notEqual(results[0].request_id,results[1].request_id);
  const value={status:'PASS_BROWSER_PLAYBACK_ACTUAL_BOARD_YES_ALARM_NO_SILENT',primary_rc:0,actual_board_only:true,mocks:false,session,package_manifest_sha256:binding.package_manifest_sha256,new_live_requests:2,results,errors,full_scope_cleanup_pending:true,one_representative_frame_per_video:true,not_independent_accuracy:true};fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify(value,null,2));
  // Ordinary data-only stop at the known idle boundary; bridge remains until original cleanup returns.
  const stopped=await page.request.post(base+'/api/board/stop',{data:{}});assert(stopped.ok());console.log(value.status,session);
 }catch(e){fs.writeFileSync(path.join(out,'FAILURE.json'),JSON.stringify({status:'FAIL_ACTUAL_BROWSER_CHECK_NO_REPLAY',error:String(e),results,errors,board_scope_may_remain_live:true},null,2));throw e}
 finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
