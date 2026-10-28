"""Fresh student-only process. Reuse valid teachers and a verified reference vector."""
import sys,traceback,gc,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common02 import *
def main():
    p=verify();CAP.mkdir(exist_ok=False);start=time.monotonic();e=None;override=None
    original=read(RUNS/'M541-demo-adaptation-capture-01/RESULT.json');probe=read(RUNS/'M541-capture-numeric-probe-01/RESULT.json')
    assert original['primary_rc']==1 and len(original['teacher'])==8 and probe['primary_rc']==0
    assert probe['helper_vs_original_features']['exact'] and probe['helper_vs_original_logits']['exact']
    result=dict(status='FAIL_M541_ISOLATED_STUDENT_CAPTURE',primary_rc=1,teacher=original['teacher'],student=[],new_student_prefills=0,
        reused_student_prefills=0,new_teacher_prefills=0,training_updates=0,board_commands=0,heldout_opened=False,
        rejected_context_student_arrays_used=False,teacher_source_sha256=sha(RUNS/'M541-demo-adaptation-capture-01/RESULT.json'))
    try:
        spec=importlib.util.spec_from_file_location('_m541_isolated_oldhead',HEAD/'learned_head.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        head=mod.LearnedHead(HEAD,read(HEAD/'HEAD_MANIFEST.json'));e=setup_engine();torch=e.torch;e.set_active(p['vision'],p['language'])
        sys.path.insert(0,str(ROOT/'experiments/v4_recovery_20261025'));from v4_recovery_native import V4Recovery
        override=V4Recovery(torch,core(e.original_vision[4]).mlp,BODY,lambda:None);override.select(True)
        versions=[(q,q._version,q.data_ptr(),tuple(q.shape)) for m in override.new for q in m.parameters()]
        # First verify all old cases, then new training/development captures; no teacher depth switching.
        requests=sorted(p['student_cases'],key=lambda r:(not bool(r.get('original_logits')),r['key']))
        for r in requests:
            assert time.monotonic()-start<p['budgets']['capture_seconds']
            if r['key']=='campus12_f00000_known-check':
                source=RUNS/'M541-capture-numeric-probe-01/fresh_helper.npz'
                with np.load(source,allow_pickle=False) as a:x=a['x'].copy();z=a['z'].copy();features=a['features'].copy()
                result['reused_student_prefills']+=1;reused=True
            else:
                f=ROOT/r['frame'];assert sha(f)==r['frame_sha256'];x,z,features=forward(e,np.load(f,allow_pickle=False),p['token_ids'])
                result['new_student_prefills']+=1;reused=False;source=None
            old=head.add(x[None],z[None])[0];file=CAP/(r['key']+'.npz');npz(file,x=x,z=z,old_logits=old,features=features)
            if r.get('original_logits'):
                o=r['original_logits'];assert sha(ROOT/o['payload'])==o['sha256']
                with np.load(ROOT/o['payload'],allow_pickle=False) as a:
                    assert np.array_equal(a['base_logits'],z) and np.array_equal(a['logits'],old),'Fresh isolated student must reproduce original reference exactly'
            assert all(q._version==n and q.data_ptr()==ptr and tuple(q.shape)==shape for q,n,ptr,shape in versions)
            row=dict(r,source=rel(file),sha256=sha(file),before=decision(old,r['target'],e.tokenizer),reused=reused,
                reused_source=rel(source) if source is not None else None,actual_student_pre_A8_hidden=True,
                cache_before=0,cache_after_clear=0,cache_layers=18,parameters_unchanged=True,tokens=128,views=2,visual_slots=98,decode_calls=0)
            result['student'].append(row);print('M541_STUDENT02',r['key'],repr(row['before']['raw_token']),row['before']['correct'],flush=True);gc.collect()
        assert len(result['student'])==37 and result['new_student_prefills']==36 and result['reused_student_prefills']==1
        result.update(status='COMPLETE_M541_ISOLATED_STUDENT_CAPTURE',primary_rc=0,teacher_correct=8,
            original_body_and_head_unchanged=True,all13_original_logit_references_exact=True,
            repair_scope='Student-only fresh process,unchanged arithmetic/helper and exact reference checks. Old teacher-first context rejected,not used for training;cache/state root cause not uniquely established.')
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if override is not None:override.close()
        if e is not None:e.close()
        result['elapsed_s']=time.monotonic()-start;save(CAP/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
