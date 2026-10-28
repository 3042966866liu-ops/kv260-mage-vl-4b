'use strict';
const $=id=>document.getElementById(id);
const escapeHTML=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data=null,camera='kitchen',caseId='cal_04_t0',selectedId='record-cal_04_t0',page='desk',filter='all',reviewTarget=null,lastCamera=null;
const dispositionNames={normal_work:'正常作业',attention:'需要关注',false_alarm:'模型误报'};
const statusNames={queued:'已排队',running:'模型复核中',review:'待人工确认',closed:'已处置',unknown:'待人工复核'};
const cameraName=id=>data?.cameras.find(c=>c.id===id)?.name??'演示机位';
const caseFor=id=>data?.cases.find(c=>c.id===id);
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toast.timeout);toast.timeout=setTimeout(()=>$('toast').hidden=true,4200)}
async function api(path,body){const r=await fetch(path,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const value=await r.json();if(!r.ok)throw Error(value.error||'服务暂不可用');return value}
function seconds(t){return typeof t==='number'?t.toFixed(2):'—'}
function currentEvent(){return data?.events.find(e=>e.id===selectedId)??data?.events.find(e=>e.case_id===caseId)}
function chooseCamera(id){camera=id;const cases=data.cases.filter(c=>c.camera_id===id);caseId=cases[0].id;selectedId=data.events.find(e=>e.case_id===caseId)?.id;renderCamera();renderResult();renderCameras()}
function renderCameras(){
 $('camera-list').innerHTML=data.cameras.map(c=>`<button class="camera ${camera===c.id?'active':''}" data-camera="${escapeHTML(c.id)}"><strong><i class="dot"></i>${escapeHTML(c.name)}</strong><small>${escapeHTML(c.location)} · 模拟素材</small></button>`).join('');
 $('camera-list').querySelectorAll('button').forEach(b=>b.onclick=()=>chooseCamera(b.dataset.camera));
}
function renderCamera(){
 const c=data.cameras.find(c=>c.id===camera),selected=caseFor(caseId);if(!c||!selected)return;
 $('camera-title').textContent=c.name;$('video-camera-name').textContent=c.name;$('camera-location').textContent=c.location+' · 模拟素材';
 const options=data.cases.filter(c=>c.camera_id===camera);$('window-select').innerHTML=options.map(x=>`<option value="${escapeHTML(x.id)}" ${caseId===x.id?'selected':''}>${(x.timestamp_ms/1000).toFixed(1)} 秒窗口</option>`).join('');
 $('capture-preview').src=selected.frame_path;$('capture-description').textContent=`视频 ${(selected.timestamp_ms/1000).toFixed(1)} 秒 · 448 × 448 原采样帧`;
 const video=$('camera-video');if(lastCamera!==camera){video.src='/media/'+camera+'.mp4';video.poster=selected.frame_path;video.load();lastCamera=camera;video.onloadedmetadata=()=>{video.currentTime=selected.timestamp_ms/1000};}else if(Number.isFinite(video.duration)){video.currentTime=selected.timestamp_ms/1000;video.pause();}
}
function renderResult(){
 const event=currentEvent();if(!event)return;const running=['queued','running'].includes(event.status);const r=event.result??{};
 const yes=event.decision==='Yes',no=event.decision==='No';
 $('result-source').textContent=event.kind==='recorded'?'历史实板':'当前实时任务';
 $('result-status').textContent=running?'等待真实板端结果':event.status==='closed'?'已完成人工处置':event.status==='unknown'?'结果未明确':'已完成模型复核';
 $('result-decision').textContent=running?(event.status==='queued'?'等待复核':'正在复核'):yes?'刀具可见':no?'未见刀具':'待人工复核';
 $('result-description').textContent=running?'结果返回前不预填有／无，请等待板端完成。':event.status==='closed'?`${dispositionNames[event.disposition]??'已处置'} · ${event.note??''}`:yes?'可能是正常备餐工具，请结合场景人工确认。':no?'仅代表当前采样画面，其他时刻仍需持续留意。':'推理失败、超时或不明确不等于“无刀具”。';
 $('result-icon').textContent=running?'◷':yes?'◇':no?'✓':'?';$('result-icon').className='result-icon'+(no?' normal':!yes&&!running?' unknown':'');
 document.querySelector('.review-panel').classList.toggle('running',running);
 $('latency-label').textContent=running?'当前等待时间':event.kind==='recorded'?'该条历史首判断耗时':'本次首判断耗时';
 $('result-latency').innerHTML=`${running?Math.max(0,Date.now()/1000-event.created).toFixed(1):seconds(r.TTFT_s)} <small>s</small>`;
 $('workflow').innerHTML=`<div class="step done"><i>✓</i><div><b>画面留存</b><span>固定采样帧与来源绑定</span></div></div><div class="step ${!running&&event.decision?'done':''}"><i>${!running&&event.decision?'✓':'2'}</i><div><b>板端模型复核</b><span>${running?'结果尚未返回':event.kind==='recorded'?'已保存实板推理记录':'真实首 token 判断'}</span></div></div><div class="step ${event.status==='closed'?'done':''}"><i>${event.status==='closed'?'✓':'3'}</i><div><b>人工确认</b><span>${event.status==='closed'?'处置说明已留存':'确认用途与现场情况'}</span></div></div>`;
 $('review-button').disabled=running;$('review-button').textContent=event.status==='closed'?'查看或更新处置':'人工确认与处置';
}
function renderRows(){
 const rows=data.events.filter(e=>filter==='all'||(filter==='review'?['review','unknown'].includes(e.status):e.status==='closed'));
 $('event-rows').innerHTML=rows.length?rows.map(e=>{const c=caseFor(e.case_id),r=e.result??{},yes=e.decision==='Yes',no=e.decision==='No';return `<tr><td><div class="event-camera"><img src="${escapeHTML(e.frame_path)}" alt="事件截图"><span><b>${escapeHTML(cameraName(c.camera_id))}</b><small>${(c.timestamp_ms/1000).toFixed(1)} 秒窗口 · 模拟素材</small></span></div></td><td><span class="chip ${e.kind==='recorded'?'neutral':'teal-chip'}">${e.kind==='recorded'?'历史实板':'本次复核'}</span></td><td><span class="chip ${yes?'amber-chip':no?'teal-chip':'neutral'}">${yes?'刀具可见':no?'未见刀具':'等待 / 不明确'}</span></td><td>${seconds(r.TTFT_s)} <small>s</small></td><td><span class="state-label ${escapeHTML(e.status)}"><i></i>${escapeHTML(statusNames[e.status]??e.status)}</span></td><td><button class="text-action" data-detail="${escapeHTML(e.id)}">查看</button><button class="text-action" data-review="${escapeHTML(e.id)}" ${['queued','running'].includes(e.status)?'disabled':''}>处置</button></td></tr>`}).join(''):'<tr><td colspan="6" class="empty-row">当前没有符合条件的事件</td></tr>';
 $('event-rows').querySelectorAll('[data-detail]').forEach(b=>b.onclick=()=>showDetails(b.dataset.detail));
 $('event-rows').querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>showReview(b.dataset.review));
 $('table-count').textContent=`共 ${rows.length} 条记录`;$('event-count').textContent=data.events.length;
}
function renderReport(){
 const e=data.evidence;$('hot-time').innerHTML=`${e.hot_mean_s.toFixed(2)} <small>秒</small>`;
 const values=[['首次请求',e.first_request_s],...e.hot_s.map((x,i)=>['热请求 '+(i+1),x])];
 $('timing-bars').innerHTML=values.map(([label,t])=>`<div class="bar-row"><span>${label}</span><div class="bar-track"><div style="width:${Math.min(t/60*100,100)}%;${label==='首次请求'?'background:#a8b9cf':''}"></div></div><b>${t.toFixed(2)} s</b></div>`).join('');
 $('evidence-sha').textContent='BOARD_RESULT SHA-256: '+e.sha256;
}
function renderStatus(){
 const w=data.worker,ready=w?.ready,busy=data.events.some(e=>e.kind==='live'&&['queued','running'].includes(e.status));
 $('verify-button').disabled=!ready||busy;$('verify-button').textContent=busy?'已有复核进行中':ready?'发起板端复核':'等待板端连接';
 $('side-device').textContent=w?(busy?'板端正在复核':ready?(w.warm?'已就绪 · 已预热':'已连接 · 尚未预热'):'已连接 · 正在准备'):'等待板端工作器连接';
 $('footer-status').textContent=(w?(busy?'板端复核中':w.warm?'板端已预热':'板端已连接'):'板端未连接')+' · MQTT 未配置';
 $('mode-banner').querySelector('strong').textContent=ready?'板端已连接':'实板记录查看模式';
 $('mode-banner').querySelector(':scope > div > span').textContent=ready?'可发起固定窗口真实复核。历史记录仍单独标识；模拟素材不是校园实拍。':'当前展示已完成的固定窗口验收；实时板端工作器尚未连接。模拟视频不是校园实拍。';
 const pending=data.events.filter(e=>['review','unknown'].includes(e.status));$('pending-count').innerHTML=`${pending.length.toString().padStart(2,'0')} <small>条</small>`;
 $('pending-caption').textContent='包含历史验收记录，不代表当前校园警情';
}
function setPage(p){page=p;const titles={desk:['监控工作台','风险复核工作台','留存画面证据，辅助值班人员确认。刀具可见不等于危险事件。'],events:['事件中心','事件与处置记录','按事件查看画面、模型判断与人员处理记录。'],report:['实板验收','可追溯的实板验收','仅展示已有原始证据，不把历史数据冒充本次实时推理。']};
 $('page-label').textContent=titles[p][0];$('page-title').textContent=titles[p][1];$('page-subtitle').textContent=titles[p][2];$('desk-page').hidden=p!=='desk';$('events-panel').hidden=p==='report';$('report-page').hidden=p!=='report';document.querySelectorAll('.nav').forEach(b=>b.classList.toggle('active',b.dataset.page===p));
}
function showDetails(id){
 const e=data.events.find(e=>e.id===id);if(!e)return;selectedId=id;const c=caseFor(e.case_id),r=e.result??{};
 const pairs=[['记录类型',e.kind==='recorded'?'历史板端验收':'本次复核'],['采样画面',`${cameraName(c.camera_id)} · 视频 ${(c.timestamp_ms/1000).toFixed(1)} 秒`],['模型输出',e.decision??'尚无明确结果'],['首判断耗时',seconds(r.TTFT_s)+' s'],['视觉与输入',seconds(r.prepare_s)+' s'],['语言与首 head',seconds(r.prefill_s)+' s'],['状态',statusNames[e.status]],['人工处置',dispositionNames[e.disposition]??'尚未确认'],['说明',e.note??'—'],['结果证据 SHA',r.evidence_sha256??data.evidence.sha256],['全词表 logits SHA',r.logits_sha256??'—']];
 $('detail-content').innerHTML=`<img class="detail-image" src="${escapeHTML(e.frame_path)}" alt="原采样画面"><dl class="detail-list">${pairs.map(([k,v])=>`<dt>${escapeHTML(k)}</dt><dd>${escapeHTML(v)}</dd>`).join('')}</dl>`;$('detail-dialog').showModal();renderResult();
}
function showReview(id){const e=data.events.find(e=>e.id===id);if(!e||['queued','running'].includes(e.status))return;reviewTarget={id:e.id,revision:e.revision};$('review-form').reset();$('review-note').value=e.note??'';if(e.disposition)$('review-form').querySelector(`input[value="${e.disposition}"]`).checked=true;$('review-dialog').showModal()}
async function refresh(){try{const next=await api('/api/state');const initial=!data;data=next;if(initial){renderCameras();renderCamera();renderReport()}renderRows();renderResult();renderStatus()}catch(e){$('side-device').textContent='本地服务暂不可用';$('verify-button').disabled=true;$('footer-status').textContent='连接中断 · 不生成判断'}}
$('window-select').onchange=()=>{caseId=$('window-select').value;selectedId=data.events.find(e=>e.case_id===caseId)?.id;renderCamera();renderResult()};
$('verify-button').onclick=async()=>{try{const r=await api('/api/verify',{case_id:caseId});selectedId=r.id;await refresh();toast('已提交真实板端复核任务')}catch(e){toast(e.message)}};
$('review-button').onclick=()=>showReview(currentEvent()?.id);$('details-button').onclick=()=>showDetails(currentEvent()?.id);
$('review-form').onsubmit=async e=>{e.preventDefault();try{await api(`/api/events/${reviewTarget.id}/review`,{revision:reviewTarget.revision,disposition:new FormData(e.target).get('disposition'),note:$('review-note').value});$('review-dialog').close();await refresh();toast('处置记录已保存')}catch(err){toast(err.message)}};
document.querySelectorAll('.close-dialog').forEach(b=>b.onclick=()=>b.closest('dialog').close());
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>setPage(b.dataset.page));$('evidence-link').onclick=()=>setPage('report');
document.querySelectorAll('.filter').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x===b));renderRows()});
$('export-button').onclick=async()=>{try{const value=await api('/api/export');const blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='campus-events-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){toast(e.message)}};
function clock(){const now=new Date();$('clock').textContent=now.toLocaleDateString('zh-CN')+' '+now.toLocaleTimeString('zh-CN',{hour12:false});const e=currentEvent();if(e&&['queued','running'].includes(e.status))renderResult()}
clock();refresh();setInterval(clock,1000);setInterval(refresh,2000);
