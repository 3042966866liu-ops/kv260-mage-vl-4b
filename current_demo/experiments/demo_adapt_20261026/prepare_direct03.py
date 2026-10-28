"""Correct old cross-producer reference claim without weakening same-producer gates."""
import sys,ast,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common02 import *
def main():
    p=verify();failed=RUNS/'M541-demo-adaptation-capture-02/RESULT.json';f=read(failed)
    assert f['primary_rc']==1 and f['new_student_prefills']==1
    # Reuse the one direct legacy tensor and previously verified direct current-video tensor.
    reusable={
      'cal_00_t0_legacy-fit':RUNS/'M541-demo-adaptation-capture-02/cal_00_t0_legacy-fit.npz',
      'campus12_f00000_known-check':RUNS/'M541-capture-numeric-probe-01/fresh_helper.npz'}
    diffs={}
    for r in p['student_cases']:
        if r['role']=='legacy-fit':
            r['prior_switched_width_semantic_reference']=r.pop('original_logits')
            r['reference_policy']='Semantic regression only;M536 source computed control4096 four first,then candidate3584. Current process directly loads3584. Numerical difference retained,not assumed equivalent.'
    c=next(r for r in p['student_cases'] if r['key']=='cal_00_t0_legacy-fit');old=c['prior_switched_width_semantic_reference']
    with np.load(reusable[c['key']],allow_pickle=False) as a,np.load(ROOT/old['payload'],allow_pickle=False) as b:
        for k,j in [('features','features'),('z','base_logits'),('old_logits','logits')]:diffs[k]=dict(exact=bool(np.array_equal(a[k],b[j])),maxabs=float(np.max(np.abs(a[k].astype(np.float64)-b[j].astype(np.float64)))))
        assert int(a['old_logits'].argmax())==int(b['logits'].argmax())==2753
    derived=[]
    for name in ['fit','reload','host']:
        source=HERE/(name+'02.py');tree=ast.parse(source.read_text(encoding='utf8'));edited=copy.deepcopy(tree)
        for node in ast.walk(edited):
            if isinstance(node,ast.ImportFrom) and node.module=='common02':node.module='common03'
            if name=='host' and isinstance(node,ast.Constant) and isinstance(node.value,str):
                if node.value=='M541-demo-adaptation02-':node.value='M541-demo-adaptation03-'
                if node.value=='02.py':node.value='03.py'
        ast.fix_missing_locations(edited);target=HERE/(name+'03.py');text=ast.unparse(edited)+'\n';compile(text,str(target),'exec');target.open('x',encoding='utf8').write(text)
        derived.append(dict(source=rel(source),sha256=sha(source),derived=rel(target),derived_sha256=sha(target)))
    record=RUNS/'M541-direct-baseline-reference-repair-03/RESULT.json'
    note=dict(status='FROZEN_M541_DIRECT_BASELINE_VS_LEGACY_SEMANTIC_REFERENCE',primary_rc=0,
        prior_capture02_sha256=sha(failed),prior_actual_host_rc=1,legacy_numeric_difference=diffs,
        corrected_claim='Probe proved one current phone frame exact,not all legacy M536 inputs. Isolated process alone didnotmake legacy reference exact. Source control/candidate order differs;unique numerical root cause not established.',
        exact_gates_retained=['Nine same-producer M539/M540 complete base/head logit comparisons','Fresh export reload must exactly reproduce accepted current student hidden/base logits'],
        legacy_four_still_required_correct=True,training_started=False,math_or_board_tolerance_changed=False,derived=derived,board_commands=0)
    save(record,note)
    p['reused_student_payloads']={k:dict(path=rel(v),sha256=sha(v)) for k,v in reusable.items()}
    p['accepted_capture']=rel(RUNS/'M541-demo-adaptation-capture-03/RESULT.json')
    p['capture_process_policy']='Direct candidate-only process;currentvideo9 exact byte refs;old4 switched-context semantic regression;own fresh reload21 exact hidden/base required.'
    newfiles=[HERE/'common03.py',HERE/'capture03.py',HERE/'fit03.py',HERE/'reload03.py',HERE/'host03.py',HERE/'prepare_direct03.py',record,failed]+list(reusable.values())
    p['frozen'].update({rel(f):sha(f) for f in newfiles});dest=RUNS/'M541-demo-adaptation-protocol-03/RESULT.json';save(dest,p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(record);synchronized('latest_m541_direct_baseline_repair03',dict(status=note['status'],result=rel(record),sha256=h,board=False,promoted=False),
        '## M541旧切换式参考与当前直接加载式参考分列\n\nRESULT SHA '+h+'；02在首cal00旧M536参考仍拒绝，1新学生数组No正确保留。最小probe只证当前phone逐位相同，不能过推旧4；原宽控制→裁后路径与当前直接3584次序不同，差异maxfeatures0.03125/base0.9307/head0.9381，未证唯一根因。03不改数学/硬件容差，当前M539/M540九帧仍严格逐位，旧4改为语义回归且全需正确，最终新head完整重载仍需对本次自身hidden/base逐位。复用2已保存直接路径向量、仅35缺失训练捕获，原8教师复用、受影响25隔离，0训练/板/heldout。原失败/源/结论边界均保留。')
    print(dict(status=note['status'],sha256=h,protocol_sha256=sha(dest)))
if __name__=='__main__':main()
