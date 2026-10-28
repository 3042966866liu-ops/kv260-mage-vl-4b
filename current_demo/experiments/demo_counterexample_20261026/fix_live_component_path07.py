"""Preserve Import06 rejection; isolate its component report instead of deleting05 evidence."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.open('x',encoding='utf-8').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
failed=RUNS/'M544-campus-live-worker-board-06/Import/BOARD_RESULT.json';f=read(failed);assert f['primary_rc']==1 and f['model_forwards']==0 and f['Overlay']==0 and 'assert not report.exists()' in f['errors'][0]
old=read(RUNS/'M544-campus-live-worker-preparation-06/RESULT.json');targets=[]
for key,name in [('package','M544-campus-live-worker-07'),('capsule','M544-campus-live-control-07')]:
 src=ROOT/old[key];assert sha(src/'PACKAGE_MANIFEST.json')==old['manifest_sha256' if key=='package' else 'capsule_manifest_sha256'];dst=OPT/'candidates'/name;dst.mkdir(exist_ok=False);targets.append(dst)
 for row in read(src/'PACKAGE_MANIFEST.json')['files']:
  p=src/row['path'];assert sha(p)==row['sha256'];b=p.read_bytes()
  if key=='package' and row['path']=='board_component.py':
   s=b.decode();assert s.count('/dev/shm/m544_live_component01.json')==1;b=s.replace('/dev/shm/m544_live_component01.json','/dev/shm/m544_live_component07.json').encode()
  elif key=='capsule' and p.suffix in ['.py','.json','.ps1','.sh']:
   b=b.decode('utf-8-sig').replace('m544_live_worker_package06','m544_live_worker_package07').replace('m544_live_worker_control06','m544_live_worker_control07').replace('m544_live_worker_ingress06','m544_live_worker_ingress07').replace('m544_live_worker_import06','m544_live_worker_import07').replace('tmp/m544_live_worker06/','tmp/m544_live_worker07/').encode()
  if p.suffix=='.py':compile(b,str(p),'exec')
  q=dst/row['path'];q.parent.mkdir(parents=True,exist_ok=True);q.open('xb').write(b)
 rows=[dict(path=q.relative_to(dst).as_posix(),bytes=q.stat().st_size,sha256=sha(q)) for q in sorted(dst.rglob('*')) if q.is_file()];save(dst/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
pkg,cap=targets;p=dict(old,status='CORRECTED_COMPONENT_REPORT_PATH07_IMPORT_PENDING',package=pkg.relative_to(ROOT).as_posix(),capsule=cap.relative_to(ROOT).as_posix(),remote='/dev/shm/m544_live_worker_package07',control_remote='/dev/shm/m544_live_worker_control07',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),capsule_manifest_sha256=sha(cap/'PACKAGE_MANIFEST.json'),runner_sha256=sha(pkg/'run.sh'),ingress_sha256=sha(cap/'ingress.py'),probe_sha256=sha(cap/'probe.py'),original_Import06_sha256=sha(failed),only_component_report_path_changed=True)
out=RUNS/'M544-campus-live-worker-preparation-07/RESULT.json';save(out,p)
for source,target in [('check_live_worker_boot06.py','check_live_worker_boot07.py'),('live_worker_control_boot06.py','live_worker_control_boot07.py')]:
 s=(HERE/source).read_text(encoding='utf-8-sig')
 for a,b in [('M544-campus-live-worker-preparation-06','M544-campus-live-worker-preparation-07'),('M544-campus-live-worker-control-06','M544-campus-live-worker-control-07'),('M544-campus-live-worker-board-06','M544-campus-live-worker-board-07'),('M544-live-worker-CPU-06','M544-live-worker-CPU-07'),('tmp/m544_live_worker06','tmp/m544_live_worker07')]:s=s.replace(a,b)
 compile(s,target,'exec');(HERE/target).open('x',encoding='utf-8').write(s)
app=ROOT/'apps/campus_guard'
(app/'live_uart07.ps1').open('x',encoding='utf-8').write((app/'live_uart06.ps1').read_text(encoding='utf-8').replace('m544_live_worker_package06','m544_live_worker_package07'))
(app/'run_live_worker07.py').open('x',encoding='utf-8').write((app/'run_live_worker06.py').read_text(encoding='utf-8').replace("HERE/'live_uart06.ps1'","HERE/'live_uart07.ps1'"))
s=(app/'bind_lifetime06.py').read_text(encoding='utf-8')
for a,b in [('M544-campus-live-worker-preparation-06','M544-campus-live-worker-preparation-07'),('M544-campus-live-worker-board-06','M544-campus-live-worker-board-07'),('M544-live-binding-current-boot-06','M544-live-binding-current-boot-07'),('LIVE_BINDING_before06','LIVE_BINDING_before07'),('latest_m544_binding06','latest_m544_binding07')]:s=s.replace(a,b)
(app/'bind_lifetime07.py').open('x',encoding='utf-8').write(s)
# These restart steps have not been executed for06; use independent07 receipts.
(app/'restart_owned_boot07.ps1').open('x',encoding='utf-8').write((app/'restart_owned_boot06.ps1').read_text(encoding='utf-8').replace('launcher/boot06','launcher/boot07').replace('restart_from_record06.py','restart_from_record07.py'))
(app/'restart_from_record07.py').open('x',encoding='utf-8').write((app/'restart_from_record06.py').read_text(encoding='utf-8').replace('launcher/boot06','launcher/boot07'))
sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
synchronized('latest_m544_component_path07',dict(status=p['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False,promoted=False),'## M544会话寿命06导入复用报告路径拒绝及07修正\n\nRESULT SHA '+sha(out)+'；Import06原FAIL SHA '+sha(failed)+'，0模型/Overlay/DMA；原board_component固定component01报告已存在，重封包时未隔离，是准备遗漏。原06源/报告/失败全保留；07只单一报告路径component07和独立包/控制/证据目录，6小时与数学原字节保持，不删除旧报告。只重做失败Import前置Install/组件，不重跑完成模型。')
print(p['status'],p['manifest_sha256'])
