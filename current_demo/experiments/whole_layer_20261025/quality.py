"""One frozen aggressive candidate versus parent; full natural128-token answers."""
from common import *
from runtime import Experiment
def main():
    p=verify();sr=read(SEARCH/'RESULT.json');assert sr['original_rc']==0
    plan=read(SEARCH/'CANDIDATE_PLAN.json');assert sha(SEARCH/'CANDIDATE_PLAN.json')==sr['candidate_plan_sha256']
    assert not QUALITY.exists();QUALITY.mkdir();start=time.monotonic();engine=None
    result=dict(status='FAIL_WHOLE_LAYER_QUALITY_EXECUTION',original_rc=1,cases=[],plan_sha256=sha(SEARCH/'CANDIDATE_PLAN.json'),board_commands=0,heldout_opened=0,parameter_updates=0,full_release_quality_pass=False)
    try:
        engine=Experiment(p)
        for arm,v,l,features in [('parent',list(range(24)),list(range(36)),plan['parent_features']),('candidate',plan['retained_vision'],plan['retained_language'],plan['candidate_training_features'])]:
            engine.set_active(v,l);engine.capture=False
            for req in p['requests']:
                assert time.monotonic()-start<7200
                if req['id'] in features:f=np.load(ROOT/features[req['id']],allow_pickle=False)
                else:f=engine.features(req)
                folder=QUALITY/arm/req['id'];array(folder/'features.npy',f)
                row,z=engine.answer(req,f,32);array(folder/'logits.npy',z)
                row.update(arm=arm,vision=v,language=l,feature_sha256=sha(folder/'features.npy'),full_logits_sha256=sha(folder/'logits.npy'))
                save(folder/'RESULT.json',row);result['cases'].append(row)
                print('WHOLE_NATURAL_ANSWER',arm,req['id'],repr(row['text']),len(row['token_ids']),'EOS' if row['ended_with_eos'] else 'CAP',flush=True)
        assert len(result['cases'])==24
        result.update(status='COMPLETE_WHOLE_LAYER_NATURAL_ANSWERS_REVIEW_PENDING',original_rc=0,actual_input_tokens=128,cap=32,software_not_exact_whole_M455=True)
    except BaseException:
        import traceback;result['traceback']=traceback.format_exc()
    finally:
        if engine:engine.close()
        result['elapsed_s']=time.monotonic()-start;save(QUALITY/'RESULT.json',result)
        print(result['status'],result.get('traceback',''),flush=True)
    return result['original_rc']
if __name__=='__main__':raise SystemExit(main())
