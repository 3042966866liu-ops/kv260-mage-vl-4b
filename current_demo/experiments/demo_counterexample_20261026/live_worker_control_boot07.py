"""M544 transfer and A53 admission; actual Web worker is a separate frozen bridge."""
import importlib.util,sys
from pathlib import Path,PurePosixPath
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_fix import *
sys.path[:0]=[str(ROOT/'experiments/visual_early_pl_20261024'),str(ROOT/'experiments/pruning_plan_20261020'),str(ROOT/'experiments/speed_target_30s_20261020'),str(ROOT/'scripts/optimization')]
import ttft_control02 as prior
from m455456_workflow02 import synchronized
PROTO=RUNS/'M544-campus-live-worker-preparation-07/RESULT.json';BIND=RUNS/'M544-campus-live-worker-control-07/RESULT.json';OUT=RUNS/'M544-campus-live-worker-board-07';LOG=ROOT/'tmp/m544_live_worker07';ACTION=''
def checked():
    p=read(PROTO);b=read(BIND);assert sha(__file__)==b['source_sha256'] and sha(PROTO)==b['preparation_sha256']
    cpu=RUNS/'M544-live-worker-CPU-07/RESULT.json';assert sha(cpu)==b['CPU_sha256'] and read(cpu)['primary_rc']==0
    parent=RUNS/'M543-repaired-campus-board-audit-02/RESULT.json';assert sha(parent)==p['parent_audit_sha256'] and read(parent)['primary_rc']==0
    for key,field in [('package','manifest_sha256'),('capsule','capsule_manifest_sha256')]:
        d=ROOT/p[key];assert sha(d/'PACKAGE_MANIFEST.json')==p[field];m=read(d/'PACKAGE_MANIFEST.json')
        assert {f.relative_to(d).as_posix() for f in d.rglob('*') if f.is_file()}=={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}
        for row in m['files']:
            f=d/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'] and f.stat().st_nlink==1 and not f.is_symlink()
    return p,ROOT/p['package']
def sync_action(key,v,note):
    synchronized('latest_m544_live_worker_'+ACTION.lower(),v,'## M544真实网页工作器 '+ACTION+' 原结果\n\nRESULT SHA '+v['sha256']+'；原状态'+v['status']+'。仅传输或ARM组件；导入器保留M543组件状态标签，实际绑定M544新manifest和新增live_frame_protocol检查。0本次模型/Overlay/DMA，不冒充网页实板已接通。')
def setup():
    p,pkg=checked();cap=ROOT/p['capsule'];spec=importlib.util.spec_from_file_location('_m544_live_ingress',cap/'ingress.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport);transport.TARGET=PurePosixPath(p['remote'])
    prior.transport=transport;prior.LOG=LOG;prior.serial.LOG=LOG;prior.PREP=PROTO;prior.CAP=cap;prior.REMOTE=p['control_remote'];prior.OUT=OUT;prior.checked=checked;prior.synchronized=sync_action
    return p,pkg
def main():
    global ACTION
    ACTION=sys.argv[1];assert ACTION in ['Prepare','Install','Import']
    if ACTION=='Prepare':
        assert not BIND.exists();p=read(PROTO);cpu=RUNS/'M544-live-worker-CPU-07/RESULT.json';assert read(cpu)['primary_rc']==0
        save(BIND,dict(status='FROZEN_M544_INSTALL_IMPORT_ONLY_CONTROL',source_sha256=sha(__file__),preparation_sha256=sha(PROTO),CPU_sha256=sha(cpu),full_model_runs=0));print('FROZEN_M544_CONTROL',sha(BIND));return 0
    setup();rc=prior.install() if ACTION=='Install' else prior.import_gate()
    if ACTION=='Import' and rc==0:
        v=read(OUT/'Import/BOARD_RESULT.json');assert v['CPU_components']['live_frame_protocol']['status']=='PASS_DATA_ONLY_FRAME_AND_INFERENCE_PROTOCOL_CPU'
    return rc
if __name__=='__main__':raise SystemExit(main())
