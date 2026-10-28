'use strict';
const $=id=>document.getElementById(id),escapeHTML=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state=null,upload=null,phase='idle',index=0,jobId=null,submitting=false,positive=null,acknowledged=null,uploading=false,scanning=false,playbackRequested=false,scanStarted=false;
async function api(path,body){const r=await fetch(path,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'服务暂不可用');return data}
function toast(s){$('toast').textContent=s;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,4800)}
function hasChannel(){return !!state?.worker?.ready&&!!upload?.frames_ready&&(upload.verified_demo||state.worker.supports_uploads)}
function setStatus(text,kind=''){$('status-text').textContent=text;$('recognition-status').className='recognition-status '+kind}
function render(){
 const w=state?.worker,connected=!!w;$('connection').classList.toggle('connected',connected);$('connection').querySelector('span').textContent=connected?(w.ready?'板卡已就绪':'板卡处理中'):'板卡未连接';$('side-device').textContent=connected?(w.ready?'已连接 · 可接收识别任务':'已连接 · 任务处理中'):'等待板卡连接';
 const warning=positive&&positive.id!==acknowledged;$('knife-warning').hidden=!warning;$('video-alert-edge').hidden=!positive;
 if(positive){const sample=upload?.cases.find(c=>c.id===positive.case_id);$('warning-description').textContent=`板端在采样画面中识别到刀具，请留意视频中的工具与现场情况。`}
 $('start-button').disabled=uploading||!upload?.frames_ready;$('start-button').textContent='播放视频';
 $('recognition-status').hidden=phase==='clear';
 if(phase==='idle')setStatus('请选择一段视频');
 else if(phase==='uploading')setStatus('正在上传视频，请稍候','processing');
 else if(phase==='sampling')setStatus('正在准备视频采样画面','processing');
 else if(phase==='ready')setStatus(connected?(hasChannel()?'播放视频时自动识别':'视频已上传，等待板端上传帧通道就绪'):'视频已上传，等待板卡连接');
 else if(phase==='recognizing')setStatus(`正在由板端识别画面 ${Math.min(index+1,upload?.cases.length??1)} / ${upload?.cases.length??1}`,'processing');
 else if(phase==='waiting')setStatus('等待板端就绪','processing');
 else if(phase==='clear')setStatus('');
 else if(phase==='positive')setStatus('检测到刀具');
 else if(phase==='unknown')setStatus('识别未完成，请检查板卡连接后重试','problem');
 else if(phase==='error')setStatus('视频处理失败，请重新选择可播放的视频','problem');
 $('sampling-frames').querySelectorAll('.sample-frame').forEach((el,i)=>{el.classList.toggle('active',scanning&&i===index);el.classList.toggle('positive',!!positive&&upload?.cases[i]?.id===positive.case_id)});
 const alarms=(state?.events??[]).filter(e=>e.kind==='live'&&e.decision==='Yes');$('alarm-count').textContent=alarms.length+' 条';
 $('alarm-rows').innerHTML=alarms.length?alarms.map(e=>`<div class="alarm-row"><img src="${escapeHTML(e.frame_path)}" alt="报警画面"><div><b>检测到刀具</b><small>${e.upload_id===upload?.id?'当前视频':'既有识别记录'} · 板端判断</small></div><span class="chip">刀具警示</span></div>`).join(''):'<div class="empty-row">暂无刀具报警</div>';
}
function renderSamples(){
 $('sampling-row').hidden=!upload?.cases.length;
 $('sampling-frames').innerHTML=(upload?.cases??[]).map(c=>`<div class="sample-frame"><img src="${escapeHTML(c.frame_path)}" alt="采样画面"><span>${(c.timestamp_ms/1000).toFixed(1)} 秒画面</span></div>`).join('');
 $('sampling-note').textContent='识别结果对应这些采样画面';
}
function waitMetadata(video){return new Promise((resolve,reject)=>{if(video.readyState>=1&&Number.isFinite(video.duration))return resolve();const timer=setTimeout(()=>done(Error('视频读取超时')),15000);function done(error){clearTimeout(timer);video.removeEventListener('loadedmetadata',loaded);video.removeEventListener('error',failed);error?reject(error):resolve()}function loaded(){done()}function failed(){done(Error('浏览器无法播放该视频，请使用MP4/H.264或WebM'))}video.addEventListener('loadedmetadata',loaded,{once:true});video.addEventListener('error',failed,{once:true})})}
function seek(video,t){return new Promise((resolve,reject)=>{if(Math.abs(video.currentTime-t)<.003&&video.readyState>=2)return resolve();const timer=setTimeout(()=>{video.removeEventListener('seeked',done);reject(Error('采样画面读取超时'))},10000);function done(){clearTimeout(timer);resolve()}video.addEventListener('seeked',done,{once:true});video.currentTime=t})}
async function extractFrames(video){
 await waitMetadata(video);if(!(video.duration>0)||video.videoWidth<1||video.videoHeight<1)throw Error('视频没有有效画面');
 const times=video.duration<2?[video.duration*.5]:[.25,.55,.85].map(r=>Math.min(video.duration-.05,video.duration*r));const canvas=document.createElement('canvas');canvas.width=448;canvas.height=448;const ctx=canvas.getContext('2d'),frames=[];
 for(const t of times){await seek(video,t);const edge=Math.min(video.videoWidth,video.videoHeight);ctx.drawImage(video,(video.videoWidth-edge)/2,(video.videoHeight-edge)/2,edge,edge,0,0,448,448);frames.push({timestamp_ms:Math.round(t*1000),png_base64:canvas.toDataURL('image/png').split(',')[1]})}
 return frames;
}
function uploadFile(file){return new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST','/api/uploads');xhr.setRequestHeader('Content-Type','application/octet-stream');xhr.setRequestHeader('X-File-Name',encodeURIComponent(file.name));xhr.upload.onprogress=e=>{if(e.lengthComputable)$('upload-progress-fill').style.width=(e.loaded/e.total*100)+'%'};xhr.onerror=()=>reject(Error('视频上传连接中断'));xhr.onload=()=>{try{const v=JSON.parse(xhr.responseText);xhr.status===201?resolve(v):reject(Error(v.error||'上传失败'))}catch(e){reject(e)}};xhr.send(file)})}
async function onVideo(file){
 if(!file||uploading)return;if(scanning)return toast('请等待当前识别任务结束，再更换视频');if(file.size>100*1024*1024)return toast('请选择不超过100 MiB的视频');
 upload=null;positive=null;acknowledged=null;jobId=null;scanning=false;playbackRequested=false;scanStarted=false;index=0;uploading=true;phase='uploading';$('knife-warning').hidden=true;$('video-alert-edge').hidden=true;$('video-file').disabled=true;$('upload-meter').hidden=false;$('upload-progress-fill').style.width='0';render();
 try{
  upload=await uploadFile(file);$('upload-drop').hidden=true;$('player-area').hidden=false;$('video-name').textContent=upload.name;
  const video=$('video-player');video.src=upload.video_url;video.load();await waitMetadata(video);
  if(!upload.cases.length){phase='sampling';render();const frames=await extractFrames(video);upload=await api(`/api/uploads/${upload.id}/frames`,{frames})}
  await seek(video,0);phase='ready';renderSamples();
 }catch(e){phase='error';toast(e.message)}
 finally{uploading=false;$('video-file').disabled=false;$('upload-meter').hidden=true;render();if(phase==='ready')$('video-player').play().catch(()=>{})}
}
function startFromPlayback(){
 if(!playbackRequested||uploading||!upload?.frames_ready||scanStarted||$('video-player').paused)return;
 if(!hasChannel()){phase='waiting';render();return}
 if($('task-select').value!=='knife_visible')return;
 scanStarted=true;index=0;scanning=true;phase='recognizing';render();submitNext();
}
async function submitNext(){
 if(submitting||jobId||!scanning)return;if(!hasChannel()){phase='waiting';return render()}
 if(index>=upload.cases.length){scanning=false;phase='clear';return render()}
 submitting=true;
 try{const value=await api('/api/verify',{case_id:upload.cases[index].id,upload_id:upload.id,task_id:$('task-select').value});jobId=value.id;phase='recognizing'}
 catch(e){phase='unknown';scanning=false;toast(e.message)}finally{submitting=false;render()}
}
async function refresh(){
 try{
  state=await api('/api/state');
  if(jobId){const e=state.events.find(x=>x.id===jobId);
   if(e&&e.kind==='live'&&e.upload_id===upload?.id){
    if(e.decision==='Yes'){
     positive=e;jobId=null;scanning=false;phase='positive';const c=upload.cases.find(c=>c.id===e.case_id);const v=$('video-player');v.pause();if(c)v.currentTime=c.timestamp_ms/1000;
    }else if(e.decision==='No'){jobId=null;index++;if(index>=upload.cases.length){phase='clear';scanning=false}else phase='waiting'}
    else if(e.status==='unknown'||e.status==='closed'){jobId=null;phase='unknown';scanning=false}
   }
  }
  render();startFromPlayback();if(scanning&&!jobId)await submitNext();
 }catch(e){$('connection').classList.remove('connected');$('connection').querySelector('span').textContent='服务连接中断';$('start-button').disabled=true}
}
$('video-player').addEventListener('play',()=>{playbackRequested=true;startFromPlayback()});
$('start-button').onclick=()=>{$('video-player').play().catch(()=>toast('请使用视频播放器的播放按钮'))};
$('acknowledge-warning').onclick=()=>{acknowledged=positive?.id;render()};
$('choose-video').onclick=e=>{e.stopPropagation();$('video-file').click()};$('replace-video').onclick=()=>$('video-file').click();$('upload-drop').onclick=()=>$('video-file').click();$('upload-drop').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('video-file').click()}};
$('video-file').onchange=()=>onVideo($('video-file').files[0]);
['dragenter','dragover'].forEach(name=>$('upload-drop').addEventListener(name,e=>{e.preventDefault();$('upload-drop').classList.add('dragover')}));
['dragleave','drop'].forEach(name=>$('upload-drop').addEventListener(name,e=>{e.preventDefault();$('upload-drop').classList.remove('dragover');if(name==='drop')onVideo(e.dataTransfer.files[0])}));
// One request at a time: short active-job polling reduces result-to-warning
// delay without piling up requests when the local server is slow.
async function poll(){await refresh();setTimeout(poll,scanning||jobId?200:1000)}
poll();
