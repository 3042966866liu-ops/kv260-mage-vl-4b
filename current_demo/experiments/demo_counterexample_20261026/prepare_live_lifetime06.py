"""Bound a demonstration session to six hours instead of twenty-minute idle exit."""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.open('x',encoding='utf-8').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
closed=RUNS/'M544-live-worker-instances/5b07f571df6342f4a39f58e919b5eec1/BOARD_RESULT.json';v=read(closed)
assert v['primary_rc']==0 and v['safe_cleanup_complete'] and not v['unsafe_retained'] and v['releases']==list(reversed(v['allocations'])) and len(v['releases'])==7 and v['clock_initial']==v['clock_final']
old=read(RUNS/'M544-campus-live-worker-preparation-05/RESULT.json')
targets=[];changes={}
for key,name in [('package','M544-campus-live-worker-06'),('capsule','M544-campus-live-control-06')]:
 src=ROOT/old[key];assert sha(src/'PACKAGE_MANIFEST.json')==old['manifest_sha256' if key=='package' else 'capsule_manifest_sha256']
 dst=OPT/'candidates'/name;dst.mkdir(exist_ok=False);targets.append(dst);changes[key]=[]
 for row in read(src/'PACKAGE_MANIFEST.json')['files']:
  f=src/row['path'];before=f.read_bytes();assert sha(f)==row['sha256'];raw=before
  if key=='package' and row['path']=='live_protocol.py':
   s=raw.decode();assert s.count('idle_seconds=1200')==1 and s.count('idle_seconds==1200')==1
   s=s.replace('idle_seconds=1200','idle_seconds=21600').replace('idle_seconds==1200','idle_seconds==21600')
   s=s.replace('self.frames=OrderedDict();self.seen=set()','self.frames=OrderedDict();self.seen=set();self.deadline=time.monotonic()+21600')
   needle='            if len(self.seen)>=self.maximum:break';assert s.count(needle)==1
   s=s.replace(needle,needle+"\n            if time.monotonic()>=self.deadline:self.packet('STOP',dict(reason='absolute_six_hour_limit'));return")
   s=s.replace('v=read_line(self.idle)','v=read_line(max(0,min(self.idle,self.deadline-time.monotonic())))')
   s=s.replace("raw_RGB_bit_exact=True,device_calls=0,model_calls=0)","raw_RGB_bit_exact=True,device_calls=0,model_calls=0,session_lifetime=lifetime_tests())")
   s+='''
def lifetime_tests():
    ch=Channel('1'*64,'2'*32);assert ch.idle==21600 and 21599<ch.deadline-time.monotonic()<=21600
    packets=[];ch.packet=lambda k,v:packets.append((k,v));ch.deadline=time.monotonic()-1
    assert list(ch.jobs())==[] and packets==[('STOP',dict(reason='absolute_six_hour_limit'))]
    try:Channel('1'*64,'2'*32,idle_seconds=1200)
    except AssertionError:pass
    else:raise AssertionError('Old short idle still accepted')
    ch=Channel('1'*64,'2'*32);packets=[];ch.packet=lambda k,v:packets.append((k,v));ch.deadline=time.monotonic()+.1;original=globals()['read_line'];seen=[]
    def expired(timeout):
        assert 0<=timeout<=.1;seen.append(timeout);raise TimeoutError('fixture-only deadline')
    try:
        globals()['read_line']=expired;assert list(ch.jobs())==[] and seen and packets[-1]==('STOP',dict(reason='bounded_session_complete'))
    finally:globals()['read_line']=original
    return dict(six_hour_absolute_bound=True,idle21600=True,old1200_rejected=True,remaining_deadline_caps_read=True,expiry_returns_normally=True,max_live_jobs_unchanged=12,model_calls=0)
'''
   raw=s.encode()
  elif key=='package' and row['path']=='DEMO_BOARD_PLAN.json':
   p=json.loads(raw);assert p['persistent_worker']['idle_seconds']==1200;p['persistent_worker']['idle_seconds']=21600;p['persistent_worker']['absolute_session_seconds']=21600;p['persistent_worker']['host_timeout_seconds']=22800;raw=(json.dumps(p,ensure_ascii=False,indent=2)+'\n').encode()
  elif key=='capsule' and f.suffix in ['.py','.ps1','.json','.sh']:
   s=raw.decode('utf-8-sig').replace('m544_live_worker_package01','m544_live_worker_package06').replace('m544_live_worker_control05','m544_live_worker_control06').replace('m544_live_worker_ingress05','m544_live_worker_ingress06').replace('m544_live_worker_import05','m544_live_worker_import06').replace('tmp/m544_live_worker05/','tmp/m544_live_worker06/');raw=s.encode()
  if f.suffix=='.py':compile(raw,str(f),'exec')
  if raw!=before:changes[key].append(row['path'])
  p=dst/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.open('xb').write(raw)
 rows=[dict(path=f.relative_to(dst).as_posix(),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(dst.rglob('*')) if f.is_file()]
 assert all((dst/r['path']).stat().st_nlink==1 and '__pycache__' not in r['path'] for r in rows)
 save(dst/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
pkg,cap=targets
for name in ['native.py','board_demo_trial.py','board_subset.py','board_visual_subset.py','learned_head.py','A.npy','B.npy','V4_3584_weights.npz','m532_parser_kernel.so']:
 assert sha(pkg/name)==sha(ROOT/old['package']/name),name
p=dict(old,status='PREPARED_M544_SIX_HOUR_BOUNDED_DEMO06',package=pkg.relative_to(ROOT).as_posix(),capsule=cap.relative_to(ROOT).as_posix(),remote='/dev/shm/m544_live_worker_package06',control_remote='/dev/shm/m544_live_worker_control06',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),capsule_manifest_sha256=sha(cap/'PACKAGE_MANIFEST.json'),runner_sha256=sha(pkg/'run.sh'),ingress_sha256=sha(cap/'ingress.py'),probe_sha256=sha(cap/'probe.py'),parent_preparation_sha256=sha(RUNS/'M544-campus-live-worker-preparation-05/RESULT.json'),prior_scope_closed_sha256=sha(closed),changed_payload_files=changes)
out=RUNS/'M544-campus-live-worker-preparation-06/RESULT.json';save(out,p)
for source,target in [('check_live_worker_boot05.py','check_live_worker_boot06.py'),('live_worker_control_boot05.py','live_worker_control_boot06.py')]:
 s=(HERE/source).read_text(encoding='utf-8-sig')
 for a,b in [('M544-campus-live-worker-preparation-05','M544-campus-live-worker-preparation-06'),('M544-campus-live-worker-control-05','M544-campus-live-worker-control-06'),('M544-campus-live-worker-board-05','M544-campus-live-worker-board-06'),('M544-live-worker-CPU-05','M544-live-worker-CPU-06'),('tmp/m544_live_worker05','tmp/m544_live_worker06')]:s=s.replace(a,b)
 compile(s,target,'exec');(HERE/target).open('x',encoding='utf-8').write(s)
bridge=ROOT/'apps/campus_guard/live_uart.ps1';s=bridge.read_text(encoding='utf-8-sig').replace('[int]$TimeoutSeconds=3000','[int]$TimeoutSeconds=22800').replace('m544_live_worker_package01','m544_live_worker_package06');assert '22800' in s
(bridge.parent/'live_uart06.ps1').open('x',encoding='utf-8').write(s)
s=(bridge.parent/'run_live_worker.py').read_text(encoding='utf-8').replace("HERE/'live_uart.ps1'","HERE/'live_uart06.ps1'");compile(s,'run_live_worker06.py','exec');(bridge.parent/'run_live_worker06.py').open('x',encoding='utf-8').write(s)
sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
synchronized('latest_m544_lifetime06_prepared',dict(status=p['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False,promoted=False),'## M544演示20分钟空闲退出的有界会话修正准备06\n\nRESULT SHA '+sha(out)+'；原05工作器原host/native0、7owner逆序/稳定四clock已闭合，视频7实际Yes证据保持。06仅新协议21600秒空闲与绝对寿命、主机22800秒上限配套，仍最多12真实新请求，正常停止/未知保留/数学/头/码/scale/owner逐字保持。新独立目录不覆盖05；需CPU与A53组件再启动固定预热，尚未称演示连接。')
print(p['status'],p['manifest_sha256'],changes)
