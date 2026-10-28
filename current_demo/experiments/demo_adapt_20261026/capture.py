"""Capture actual frozen student tensors and deeper clean teacher predictions."""
import sys,traceback,gc,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_adapt import *
def main():
    p=verify();CAP.mkdir(exist_ok=False);start=time.monotonic();e=None;override=None
    result=dict(status='FAIL_M541_REAL_STUDENT_TEACHER_CAPTURE',primary_rc=1,teacher=[],student=[],training_updates=0,board_commands=0,heldout_opened=False)
    try:
        e=setup_engine();torch=e.torch
        e.set_active(list(range(24)),list(range(36)))
        for r in p['teacher_cases']:
            assert time.monotonic()-start<p['budgets']['capture_seconds']
            f=ROOT/r['frame'];assert sha(f)==r['frame_sha256'];frame=np.load(f,allow_pickle=False)
            x,z,features=forward(e,frame,p['token_ids']);file=CAP/('teacher_'+r['id']+'.npz');npz(file,x=x,z=z,features=features)
            score=decision(z,r['target'],e.tokenizer)
            result['teacher'].append(dict(id=r['id'],target=r['target'],source=rel(file),sha256=sha(file),score=score,
                KL_enabled=score['correct'],kind='deeper_quantized_V24L36_original_V4_4096_no_learned_head_not_original_checkpoint'))
            print('M541_TEACHER',r['id'],repr(score['raw_token']),score['correct'],flush=True)
        sys.path.insert(0,str(ROOT/'experiments/v4_recovery_20261025'));from v4_recovery_native import V4Recovery
        e.set_active(p['vision'],p['language']);override=V4Recovery(torch,core(e.original_vision[4]).mlp,BODY,lambda:None);override.select(True)
        versions=[(q,q._version,q.data_ptr(),tuple(q.shape)) for m in override.new for q in m.parameters()]
        spec=importlib.util.spec_from_file_location('_m541_oldhead',HEAD/'learned_head.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        head=mod.LearnedHead(HEAD,read(HEAD/'HEAD_MANIFEST.json'))
        for r in p['student_cases']:
            assert time.monotonic()-start<p['budgets']['capture_seconds']
            f=ROOT/r['frame'];assert sha(f)==r['frame_sha256'];frame=np.load(f,allow_pickle=False)
            x,z,features=forward(e,frame,p['token_ids']);old=head.add(x[None],z[None])[0]
            file=CAP/(r['key']+'.npz');npz(file,x=x,z=z,old_logits=old,features=features)
            assert all(q._version==n and q.data_ptr()==ptr and tuple(q.shape)==shape for q,n,ptr,shape in versions)
            if r.get('original_logits'):
                o=r['original_logits'];source=ROOT/o['payload'];assert sha(source)==o['sha256']
                with np.load(source,allow_pickle=False) as a:
                    assert np.array_equal(a['base_logits'],z) and np.array_equal(a['logits'],old),'Original capture numerical identity changed'
            row=dict(r,source=rel(file),sha256=sha(file),before=decision(old,r['target'],e.tokenizer),
                actual_student_pre_A8_hidden=True,cache_before=0,cache_after_clear=0,cache_layers=18,parameters_unchanged=True,
                tokens=128,views=2,visual_slots=98,decode_calls=0)
            result['student'].append(row);print('M541_STUDENT',r['key'],repr(row['before']['raw_token']),row['before']['correct'],flush=True);gc.collect()
        assert len(result['teacher'])==p['budgets']['teacher_prefills'] and len(result['student'])==p['budgets']['student_capture_prefills']
        result.update(status='COMPLETE_M541_REAL_STUDENT_CAPTURE_AND_CLEAN_TEACHER',primary_rc=0,
            teacher_correct=sum(r['score']['correct'] for r in result['teacher']),teacher_wrong_KL_skipped=[r['id'] for r in result['teacher'] if not r['KL_enabled']],
            original_body_and_head_unchanged=True,new_student_forward_reason='Need actual pre-head hidden vectors for new training;prior reports lacked them. Known logits must reproduce bitwise;not rerun to change old results.')
    except BaseException:result['traceback']=traceback.format_exc()
    finally:
        if override is not None:override.close()
        if e is not None:e.close()
        result['elapsed_s']=time.monotonic()-start;save(CAP/'RESULT.json',result);print(result['status'],result.get('traceback',''),flush=True)
    return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
