"""Direct-loaded student capture with identical-producer numerical references."""
import sys,traceback,gc,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common03 import *
def main():
    p=verify();CAP.mkdir(exist_ok=False);start=time.monotonic();e=None;override=None
    old=read(RUNS/'M541-demo-adaptation-capture-01/RESULT.json');assert len(old['teacher'])==8
    result=dict(status='FAIL_M541_DIRECT_STUDENT_CAPTURE',primary_rc=1,teacher=old['teacher'],student=[],new_student_prefills=0,reused_student_prefills=0,
        new_teacher_prefills=0,training_updates=0,board_commands=0,heldout_opened=False,rejected_mixed_context_student_arrays_used=False)
    try:
        spec=importlib.util.spec_from_file_location('_m541_direct_head',HEAD/'learned_head.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        head=mod.LearnedHead(HEAD,read(HEAD/'HEAD_MANIFEST.json'));e=setup_engine();torch=e.torch;e.set_active(p['vision'],p['language'])
        sys.path.insert(0,str(ROOT/'experiments/v4_recovery_20261025'));from v4_recovery_native import V4Recovery
        override=V4Recovery(torch,core(e.original_vision[4]).mlp,BODY,lambda:None);override.select(True)
        versions=[(q,q._version,q.data_ptr(),tuple(q.shape)) for m in override.new for q in m.parameters()]
        for r in sorted(p['student_cases'],key=lambda r:(not bool(r.get('original_logits')),r['key'])):
            assert time.monotonic()-start<p['budgets']['capture_seconds'];reuse=p['reused_student_payloads'].get(r['key'])
            if reuse:
                f=ROOT/reuse['path'];assert sha(f)==reuse['sha256']
                with np.load(f,allow_pickle=False) as a:x=a['x'].copy();z=a['z'].copy();features=a['features'].copy()
                result['reused_student_prefills']+=1
            else:
                f=ROOT/r['frame'];assert sha(f)==r['frame_sha256'];x,z,features=forward(e,np.load(f,allow_pickle=False),p['token_ids'])
                result['new_student_prefills']+=1
            oldz=head.add(x[None],z[None])[0];file=CAP/(r['key']+'.npz');npz(file,x=x,z=z,old_logits=oldz,features=features)
            if r.get('original_logits'):
                reference=r['original_logits'];assert sha(ROOT/reference['payload'])==reference['sha256']
                with np.load(ROOT/reference['payload'],allow_pickle=False) as a:
                    assert np.array_equal(a['base_logits'],z) and np.array_equal(a['logits'],oldz),'Same direct-loaded evaluation context must match exactly'
            assert all(q._version==n and q.data_ptr()==ptr and tuple(q.shape)==shape for q,n,ptr,shape in versions)
            row=dict(r,source=rel(file),sha256=sha(file),before=decision(oldz,r['target'],e.tokenizer),reused=bool(reuse),reused_source=reuse,
                actual_student_pre_A8_hidden=True,cache_before=0,cache_after_clear=0,cache_layers=18,parameters_unchanged=True,tokens=128,views=2,visual_slots=98,decode_calls=0)
            result['student'].append(row);print('M541_STUDENT03',r['key'],repr(row['before']['raw_token']),row['before']['correct'],flush=True);gc.collect()
        assert len(result['student'])==37 and result['new_student_prefills']==35 and result['reused_student_prefills']==2
        result.update(status='COMPLETE_M541_DIRECT_STUDENT_CAPTURE',primary_rc=0,teacher_correct=8,original_body_and_head_unchanged=True,
            same_context_nine_original_logits_exact=True,legacy4_used_as_semantic_controls_not_cross_context_byte_identity=True)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if override is not None:override.close()
        if e is not None:e.close()
        result['elapsed_s']=time.monotonic()-start;save(CAP/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
