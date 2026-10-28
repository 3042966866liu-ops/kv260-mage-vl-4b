"""Finite, training-only iterative deletion. All attempted arms are preserved."""
from common import *
from runtime import Experiment
def main():
    p=verify();assert not SEARCH.exists();SEARCH.mkdir();start=time.monotonic();engine=None
    result=dict(status='FAIL_WHOLE_LAYER_SEARCH',original_rc=1,protocol_sha256=sha(PREP/'RESULT.json'),rounds=[],board_commands=0,heldout_opened=0,training_steps=0)
    try:
        engine=Experiment(p);train=[r for r in p['requests'] if r['id'] in p['training_ids']]
        assert len(train)==8 and len({r['source_group'] for r in train})==4
        visual_calls=0;sequences=0
        def run(name,v,l,reuse=None):
            nonlocal visual_calls,sequences
            engine.set_active(v,l);engine.bank={};engine.capture=True;rows=[];features={}
            for req in train:
                assert time.monotonic()-start<p['search_budget']['wall_seconds'] and sequences<p['search_budget']['first_token_sequences']
                if reuse is None:
                    assert visual_calls<p['search_budget']['full_vision_forwards'];f=engine.features(req);visual_calls+=1
                else:f=np.load(ROOT/reuse[req['id']],allow_pickle=False)
                folder=SEARCH/name/req['id'];array(folder/'features.npy',f);features[req['id']]=rel(folder/'features.npy')
                row,z=engine.answer(req,f,1);sequences+=1;array(folder/'first_logits.npy',z[0]);row['logits_sha256']=sha(folder/'first_logits.npy');save(folder/'RESULT.json',row);rows.append(row)
                print('WHOLE_TRAIN',name,req['id'],row['first_decision'],round(row['correct_direction_pp'],4),'V',len(v),'L',len(l),flush=True)
            bank=copy.deepcopy(engine.bank);rank={branch:ranked(bank,active,branch,p) for branch,active in [('vision',v),('language',l)]} if reuse is None else dict(vision=[],language=ranked(bank,l,'language',p))
            a=dict(name=name,vision=v,language=l,rows=rows,features=features,bank=bank,ranking=rank)
            save(SEARCH/name/'SUMMARY.json',a);return a
        parent=run('parent',list(range(24)),list(range(36)))
        result['parent_training']=parent;baseline={r['request_id']:r for r in parent['rows']}
        # Initial single-layer short list supplies actual task effects, explicitly limited to4 layers.
        screened=[]
        for branch in ('vision','language'):
            for ranking in parent['ranking'][branch][:2]:
                i=ranking['index'];v=list(range(24));l=list(range(36));(v if branch=='vision' else l).remove(i)
                a=run('single_'+branch+'_'+str(i),v,l,parent['features'] if branch=='language' else None)
                screened.append(dict(branch=branch,index=i,summary=rel(SEARCH/a['name']/'SUMMARY.json'),new_training_errors=[r['request_id'] for r in a['rows'] if baseline[r['request_id']]['correct_first_token'] and not r['correct_first_token']]))
        result['single_block_screen']=screened;current=parent
        for round_index,step in enumerate(p['schedule'],1):
            rankings=current['ranking'];trials=[]
            for arm in range(2):
                removed={}
                for branch,count in [('vision',step['remove_vision']),('language',step['remove_language'])]:
                    ranked_rows=rankings[branch];chosen=ranked_rows[:count] if arm==0 else ranked_rows[:count-1]+ranked_rows[count:count+1]
                    assert len(chosen)==count;removed[branch]=[r['index'] for r in chosen]
                v=[i for i in current['vision'] if i not in removed['vision']];l=[i for i in current['language'] if i not in removed['language']]
                a=run('round_'+str(round_index)+'_arm_'+str(arm),v,l)
                errors=[r['request_id'] for r in a['rows'] if baseline[r['request_id']]['correct_first_token'] and not r['correct_first_token']]
                other=sum(r['first_decision']=='Other' for r in a['rows']);mean=sum(r['correct_direction_pp'] for r in a['rows'])/8
                a['selection_score']=[len(errors),other,-mean,arm];a['removed_this_round']=removed;a['new_training_errors']=errors
                trials.append(a)
            selected=min(trials,key=lambda a:a['selection_score']);current=selected
            record=dict(round=round_index,selected=current['name'],trials=[dict(name=a['name'],score=a['selection_score'],removed=a['removed_this_round'],new_training_errors=a['new_training_errors']) for a in trials])
            result['rounds'].append(record);save(SEARCH/('ROUND_'+str(round_index)+'.json'),record)
            print('WHOLE_ROUND_SELECTED',record,flush=True)
        assert len(current['vision'])==12 and len(current['language'])==16
        plan=dict(status='FROZEN_AGGRESSIVE_OFFLINE_CANDIDATE_QUALITY_PENDING',retained_vision=current['vision'],retained_language=current['language'],removed_vision=sorted(set(range(24))-set(current['vision'])),removed_language=sorted(set(range(36))-set(current['language'])),language_cache_map=[dict(compact=j,original=i) for j,i in enumerate(current['language'])],parent_features=parent['features'],candidate_training_features=current['features'],selected_training_summary=rel(SEARCH/current['name']/'SUMMARY.json'),training_only=True,board_deployable=False,no_new_R1=True,quality_pass=False)
        save(SEARCH/'CANDIDATE_PLAN.json',plan)
        result.update(status='COMPLETE_TRAINING_SEARCH_CANDIDATE_FROZEN_QUALITY_PENDING',original_rc=0,sequences=sequences,visual_forwards=visual_calls,candidate_plan_sha256=sha(SEARCH/'CANDIDATE_PLAN.json'),reserved_cal_used_for_selection=False,parameter_updates=0)
    except BaseException:
        import traceback;result['traceback']=traceback.format_exc()
    finally:
        if engine:engine.close()
        result['elapsed_s']=time.monotonic()-start;save(SEARCH/'RESULT.json',result)
        print(result['status'],result.get('traceback',''),flush=True)
    return result['original_rc']
if __name__=='__main__':raise SystemExit(main())
