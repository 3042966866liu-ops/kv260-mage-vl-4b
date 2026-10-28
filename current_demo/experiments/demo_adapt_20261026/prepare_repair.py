"""Quarantine mixed-depth capture; reuse teachers, isolate student and keep exact gate."""
import sys,ast,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_adapt import *
def main():
    p=verify();failed=read(CAP/'RESULT.json');assert failed['primary_rc']==1
    probe=read(RUNS/'M541-capture-numeric-probe-01/RESULT.json');ph=read(RUNS/'M541-capture-numeric-probe-host-01/RESULT.json')
    assert ph['host_rc']==probe['primary_rc']==0 and ph['native_sha256']==sha(RUNS/'M541-capture-numeric-probe-01/RESULT.json')
    for key in ['helper_vs_original_features','helper_vs_original_logits','inline_vs_original_features','inline_vs_original_logits']:assert probe[key]['exact']
    assert len(failed['teacher'])==8 and all(r['KL_enabled'] for r in failed['teacher'])
    files=[]
    # Bind downstream modules only to the accepted02 capture/protocol, keep their math identical.
    for name in ['fit','reload','host']:
        source=HERE/(name+'.py');tree=ast.parse(source.read_text(encoding='utf8'));edited=copy.deepcopy(tree)
        for node in ast.walk(edited):
            if isinstance(node,ast.ImportFrom) and node.module=='common_adapt':node.module='common02'
            if name=='host' and isinstance(node,ast.Constant) and isinstance(node.value,str):
                if node.value=='M541-demo-adaptation-':node.value='M541-demo-adaptation02-'
                if node.value=='make_frames.py':node.value='make_frames.py'
                if node.value=='.py':node.value='02.py'
        if name=='host':
            # stage capture/fit/reload -> their versioned02 scripts. This controller is not for frames.
            for node in ast.walk(edited):
                if isinstance(node,ast.Constant) and node.value=='frames':pass
        ast.fix_missing_locations(edited);target=HERE/(name+'02.py');text=ast.unparse(edited)+'\n';compile(text,str(target),'exec');target.open('x',encoding='utf8').write(text)
        files.append(dict(source=rel(source),source_sha256=sha(source),target=rel(target),target_sha256=sha(target)))
    # The generated host selects capture02/fit02/reload02 by appending02.py;no frames use is permitted.
    quarantine={rel(f):sha(f) for f in sorted(CAP.glob('*.npz')) if not f.name.startswith('teacher_')}
    record=RUNS/'M541-capture-context-isolation-repair-01/RESULT.json'
    v=dict(status='FROZEN_M541_STUDENT_PROCESS_ISOLATION_EXACT_NUMERIC_GATE_RETAINED',primary_rc=0,
        original_capture_result_sha256=sha(CAP/'RESULT.json'),original_host_rc=1,original_student_records_completed=len(failed['student']),
        quarantined_student_payloads=quarantine,quarantined_used_for_training=False,original_teacher_reused=8,
        fresh_helper_and_original_inline_exact_to_prior=True,probe_sha256=sha(RUNS/'M541-capture-numeric-probe-01/RESULT.json'),
        new_capture_student_prefills=36,reuse_verified_probe_student=1,new_teacher_forwards=0,
        reason='Difference observed only in teacher-first shared process;fresh helper and originalinline both exact. Isolate processes,not claim unique cache root cause. Reject prior student tensors rather than relax numeric tolerance.',
        derived=files,completed_accepted_answers_rerun_for_reporting=0,board_commands=0)
    save(record,v)
    p['frozen'].update({rel(f):sha(f) for f in [HERE/'common02.py',HERE/'capture02.py',HERE/'fit02.py',HERE/'reload02.py',HERE/'host02.py',HERE/'prepare_repair.py',record,CAP/'RESULT.json',RUNS/'M541-capture-numeric-probe-01/RESULT.json',RUNS/'M541-capture-numeric-probe-01/fresh_helper.npz']})
    p['frozen'].update({r['source']:r['sha256'] for r in failed['teacher']})
    p['accepted_capture']='deployment/mage_vl4b/optimization_v1/runs/M541-demo-adaptation-capture-02/RESULT.json'
    p['original_capture_rejected']=True;p['capture_process_policy']='Teacher cache reused separately;fresh student-only process;all13 prior full logits exactly checked.'
    dest=RUNS/'M541-demo-adaptation-protocol-02/RESULT.json';save(dest,p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(record);synchronized('latest_m541_capture_isolation_repair01',dict(status=v['status'],result=rel(record),sha256=h,board=False,promoted=False),
        '## M541采集上下文数值拒绝保全与进程隔离\n\nRESULT SHA '+h+'；原8教师全对，24新学生完成及第25数组在旧参考逐位检查拒绝，25学生数组全部隔离不训练，原host/native1保留。最小新进程helper和原inline均逐位复现旧features/logits，未证明具体cache根因。新02仅学生进程、复用8教师+1已核probe、36缺失训练采集；数学/阈值不改、13旧参考仍逐位门。不是补日志重跑已接受回答；需要重新获取此前拒绝上下文训练张量。256×2预算/头/原数据不变，0训练已发生/板/heldout。')
    print(dict(status=v['status'],sha256=h,protocol_sha256=sha(dest),quarantined=len(quarantine)))
if __name__=='__main__':main()
