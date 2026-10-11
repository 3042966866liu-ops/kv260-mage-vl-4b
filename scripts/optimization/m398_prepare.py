"""Prepare missing-only original last-layer capture using proven sealed loader."""
import ast
import json
import shutil
import sys
import symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
OLD=BASE/'candidates/M394-silu-video-01'
PKG=BASE/'candidates/M398-tail-reference-01'
DRAFT=ROOT/'tmp/m398/capture-draft'

def change(s):
    return s.replace('M394','M398').replace('m394','m398').replace('silu-video','tail-reference').replace('silu_video','tail_reference').replace('SILU_VIDEO','TAIL_REFERENCE').replace('enable-silu-video','enable-tail-reference').replace('enable_silu_video','enable_tail_reference').replace('sealed-DMA-SiLU-workspace-fixed159-video-numerical','sealed-DMA-original-fixed159-tail-reference').replace('PASS_M398_TAIL_REFERENCE_NUMERICAL','PASS_M398_ORIGINAL_TAIL_REFERENCE')

def generate():
    if DRAFT.exists() or PKG.exists():raise RuntimeError('Draft/package already exists')
    recovery={}
    for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/n;s=p.read_text(encoding='utf-8-sig');recovery[n]=dict(sha256=sha(p),lines=len(s.splitlines()),bytes=p.stat().st_size)
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prerequisite=b['latest_m397_last_layer_tail_preparation']
    assert sha(ROOT/prerequisite['result'])==prerequisite['sha256']=='17817f223700a901e924af4c01dd30b1497b1052c6df03acd9bbfef5e4b96250'
    assert all(prerequisite['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert sha(OLD/'PACKAGE_MANIFEST.json')=='ce1913cec0510273a988393400aebe093c3b7c90633404512510c54f83dce8d5'
    assert all(sha(OLD/r['path'])==r['sha256'] for r in m['files'])
    # Selected prior results have only layer0 gate/up fixture paths; full output
    # records are hashes. Record this bounded availability scope explicitly.
    available=[]
    for run in ('M368-staged-video-board-02','M387-ps-video-board-01','M390-gate-up-capture-board-01','M394-silu-video-board-01','M395-silu-performance-board-01'):
        p=BASE/'runs'/run/'BOARD_RESULT.json'
        if p.exists():
            r=json.loads(p.read_text(encoding='utf-8'));available.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),fixture_fields={k:v for k,v in r.items() if 'fixture' in k},tail_arrays_recovered_on_host=False))
    gate=change((OLD/'m394_silu_video_gate.py').read_text(encoding='utf-8'))
    gate=gate.replace('from m393_silu_scope import SiluLayerScope,RetainedSiluOwnerError','from m398_reference_capture import LastLayerReferenceCapture,RetainedReferenceOwnerError')
    gate=gate.replace('silu_scope','capture_scope').replace('RetainedSiluOwnerError','RetainedReferenceOwnerError')
    a=gate.index("        text_path=Path('/home/ubuntu/m393_");z=gate.index('        if os.geteuid()',a)
    gate=gate[:a]+f"        capture_prior=HERE/'TAIL_REFERENCE_PREREQUISITE.json'\n        if json.loads(capture_prior.read_text(encoding='utf-8'))['sha256']!='{prerequisite['sha256']}':raise RuntimeError('Tail preparation identity differs')\n        result['tail_capture_prerequisite_sha256']='{prerequisite['sha256']}'\n"+gate[z:]
    gate=gate.replace('one ordinary5.900390625MiB SiLU workspace, no PS prefetch or extra CMA','original math, missing-only layer35 fixtures bounded16MiB disk, no PS prefetch or extra CMA')
    marker="            families.append(dict(layer=layer,family=name,input=tensor(values),output={k:tensor(v) for k,v in sorted(output.items())}))"
    assert gate.count(marker)==1
    gate=gate.replace(marker,marker+"\n            if capture_scope is None:raise RuntimeError('Original capture scope missing')\n            capture_scope.family(layer,name,values,output)")
    gate=gate.replace('capture_scope=SiluLayerScope(model,policy,resident,enabled=True)','capture_scope=LastLayerReferenceCapture(model,policy,resident,EVIDENCE,enabled=True)')
    gate=gate.replace("result['capture_scope']=capture_scope.report()","result['reference_capture']=capture_scope.report()")
    gate=gate.replace("result['silu_workspace_enabled']=True","result['silu_workspace_enabled']=False\n            result['tail_candidate_executed']=False")
    gate=gate.replace("result['status']='PASS_M398_ORIGINAL_TAIL_REFERENCE'","result['status']='PASS_M398_ORIGINAL_TAIL_REFERENCE'\n        result['reference_capture_pass']=True\n        result['candidate_numerical_pass']=False")
    gate=gate.replace('Closed video SiLU scope retained','Closed original reference scope retained')
    gate=gate.replace('Independent SiLU video numeric/lifetime closure; then lightweight original expression A/workspace B balanced full requests on same parallel hardware and one parser','Original tail fixture identity/lifecycle closure only; then isolated tail chain gate, no performance or candidate full video yet')
    assert 'SiluLayerScope' not in gate and 'silu_scope' not in gate
    DRAFT.mkdir(parents=True)
    skip={'m394_silu_video_gate.py','m393_silu_scope.py','m393_silu_workspace.py','m394_export_result.py','run_m394_silu_video.sh','m394_assemble.py','SHA256SUMS'}
    for r in m['files']:
        if r['path'] not in skip:shutil.copyfile(OLD/r['path'],DRAFT/r['path'])
    atomic(DRAFT/'m398_tail_reference_gate.py',gate.encode('utf-8'))
    shutil.copyfile(HERE/'m398_reference_capture.py',DRAFT/'m398_reference_capture.py')
    atomic(DRAFT/'TAIL_REFERENCE_PREREQUISITE.json',encoded(prerequisite))
    for src,dst in [('m394_export_result.py','m398_export_result.py'),('run_m394_silu_video.sh','run_m398_tail_reference.sh'),('m394_assemble.py','m398_assemble.py')]:
        atomic(DRAFT/dst,change((OLD/src).read_text(encoding='utf-8')).encode('utf-8'))
    # All inherited dependencies come from the actually deployed M387 path/SHA.
    assert "OLD=Path('/home/ubuntu/m387_ps_video_candidate_01')" in (DRAFT/'m398_assemble.py').read_text(encoding='utf-8')
    assert "$remote='/home/ubuntu/m387_ps_video_candidate_01'" in (HERE/'m387_control_recovered_02.ps1').read_text(encoding='utf-8-sig')
    for src,dst in [('m394_control.ps1','m398_control.ps1'),('m394_workflow.py','m398_workflow.py')]:
        s=change((HERE/src).read_text(encoding='utf-8-sig'))
        s=s.replace('原固定159视频SiLU数值门禁','原固定159视频末层参考捕获').replace('SiLU视频包传输核对','末层参考捕获包传输核对')
        atomic(HERE/dst,s.encode('utf-8'))
    atomic(ROOT/'tmp/m398/recovery_and_availability.json',encoded(dict(recovery_read=recovery,selected_saved_results=available,
           all_board_paths_globally_proven_absent=False,prior_capture_layer=0,needed_capture_layer=35,
           same_terminal_sudo_precheck_sha256=sha(ROOT/'tmp/m398/sudo_precheck_01.log'))))
    print('M398_DRAFT_CREATED',len(list(DRAFT.iterdir())))

def freeze():
    if PKG.exists():raise RuntimeError('Immutable candidate already exists')
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in DRAFT.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(json.loads((DRAFT/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for module,tree in trees.items():
        for n in ast.walk(tree):
            imports=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((module,x) for x in imports if x and x not in trees and x not in allowed)
    assert not missing,missing
    s=(DRAFT/'m398_tail_reference_gate.py').read_text(encoding='utf-8')
    main=next(t for t in symtable.symtable(s,'gate','exec').get_children() if t.get_name()=='main')
    assert next(t for t in main.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert next(t for t in main.get_children() if t.get_name()=='observed_family').lookup('capture_scope').is_free()
    assert next(t for t in main.get_children() if t.get_name()=='observed_prefill').lookup('capture_scope').is_nonlocal()
    for r in json.loads((DRAFT/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/r['path'])==r['sha256']
    assert sha(DRAFT/'m398_reference_capture.py')==sha(HERE/'m398_reference_capture.py')
    PKG.mkdir(parents=True)
    for p in DRAFT.iterdir():shutil.copyfile(p,PKG/p.name)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M398-original-fixed159-tail-reference-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    r=dict(status='PASS_OFFLINE_ORIGINAL_TAIL_CAPTURE_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
           build_id='0x4D333537',recursive_missing=missing,python310_syntax=True,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),
           fixture_count=12,fixture_disk_budget_bytes=16<<20,extra_DMA_allowed=False,PS_prefetch=False,parser_workers=1,
           candidate_tail_executed=False,scope_original_math_hooks=3,removed_hooks_ast_equals_original=True,
           production_policy_unchanged=True,board_run=False,numerical_pass=False,performance_pass=False,test_support_pending=True,
           availability_receipt_sha256=sha(ROOT/'tmp/m398/recovery_and_availability.json'),
           rejected_offline_test='Initial fake Linear output F-order rejected; test fake normalizes to actual frozen M238 C-order target contract. Capture production layout check unchanged.')
    out=BASE/'runs/M398-tail-reference-preparation-01/RESULT.json';atomic(out,encoded(r),immutable=True);h=sha(out)
    sync('latest_m398_tail_reference_preparation',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=r['manifest_sha256']),
         f'## M398 缺失末层原参考捕获准备（2026-10-04）\n\nSHA `{h}`，manifest `{r["manifest_sha256"]}`；同固定159视频原完整778逻辑/781物理/36层/完整head，三观察钩子去除AST恢复原数学。只保存缺失末层12项NPY，16MiB磁盘预算，原七DMA封锁、1GiB普通RSS预算/64MiB普通余量；PS预读/双parser/SiLU workspace关闭，未执行裁剪候选。所选已有结果只有全tensor哈希与layer0 fixture，非全板端路径不存在证明。missing0/3.10与同SHA硬件47项核对；原生产政策/服务/稳定回滚保持。尚需实际wrapper/捕获/回收支持，未上传或运行；COM3 shell已确认，sudo过期，等人工续期，不重复阻塞。')
    print(json.dumps(r|{'result_sha256':h}))

if __name__=='__main__':
    if sys.argv[1:]==['generate']:generate()
    elif sys.argv[1:]==['freeze']:freeze()
    elif sys.argv[1:]==['repair-draft-status']:
        p=DRAFT/'m398_tail_reference_gate.py';old=p.read_bytes()
        atomic(ROOT/'tmp/m398/rejected_status_draft.py',old,immutable=True)
        s=old.decode('utf-8').replace('PASS_M398_TAIL_REFERENCE_NUMERICAL','PASS_M398_ORIGINAL_TAIL_REFERENCE')
        marker="result['status']='PASS_M398_ORIGINAL_TAIL_REFERENCE'"
        assert s.count(marker)==1 and "result['candidate_numerical_pass']" not in s
        s=s.replace(marker,marker+"\n        result['reference_capture_pass']=True\n        result['candidate_numerical_pass']=False")
        atomic(p,s.encode('utf-8'));print('M398_UNFROZEN_STATUS_REPAIRED_NO_BOARD')
    else:raise SystemExit('generate | freeze')
