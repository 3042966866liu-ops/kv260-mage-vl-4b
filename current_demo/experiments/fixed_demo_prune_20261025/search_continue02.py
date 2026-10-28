"""Bounded fixed-demo structural search. No vocabulary masking or canned answer."""
from demo_continue_common import *
from runtime_demo import DemoExperiment
import itertools,shutil,traceback
class BudgetStop(Exception):pass
def main():
    p=verify();assert not OUT.exists();OUT.mkdir();began=time.monotonic();engine=None
    value=dict(status='FAIL_FIXED_DEMO_SEARCH_EXECUTION',original_rc=1,trials=[],rounds=[],board_commands=0,heldout_opened=0,parameter_updates=0,protocol_sha256=sha(PREP/'RESULT.json'))
    sequences=visual_count=byte_count=trial_count=reused=0
    try:
        assert shutil.disk_usage(OUT).free>10<<30
        engine=DemoExperiment(p['runtime_protocol']);req={r['id']:r for r in p['requests']};order=p['demo_ids']
        assert len(order)==4 and {req[n]['knife_present'] for n in order}=={True,False}
        prefix_cache={};feature_cache={};seed_masks={};bank_sources={}
        for source in p['sources']:
            key=mask(source['vision'],source['language']);seed_masks[key]=(source['vision'],source['language'])
            prefix_cache.setdefault(key,{}).update(source['logits']);feature_cache.setdefault(mask(source['vision']),{}).update(source['features'])
            if source['bank']:bank_sources.setdefault(key,source['bank'])
        states={read(ROOT/path)['mask']:read(ROOT/path) for path in p['completed_trial_files']};current=None
        def saved_array(path,a):
            nonlocal byte_count
            assert byte_count+a.nbytes<p['budgets']['saved_array_bytes']
            array(path,a);byte_count+=path.stat().st_size
        def guard(final=False):
            if time.monotonic()-began>=p['budgets']['wall_seconds']:raise BudgetStop('wall budget')
            if sequences>=p['budgets']['new_decision_sequences']-(0 if final else 8):raise BudgetStop('decision sequence budget')
            assert shutil.disk_usage(OUT).free>1<<30
        def cost(branch,i):return p['costs'][branch+'_'+str(i).zfill(2)]['modelled_seconds']
        def saving(v,l):return sum(cost('vision',i) for i in range(24) if i not in v)+sum(cost('language',i) for i in range(36) if i not in l)
        def feature(v,r,final=False):
            nonlocal visual_count
            key=mask(v);known=feature_cache.setdefault(key,{})
            if r['id'] in known:return np.load(ROOT/known[r['id']],allow_pickle=False),known[r['id']]
            guard(final)
            if visual_count>=p['budgets']['new_vision_forwards']-(0 if final else 8):raise BudgetStop('visual forward budget')
            f=engine.features(r);visual_count+=1;folder=OUT/'features'/key/r['id'];saved_array(folder/'features.npy',f)
            save(folder/'M455_TRACE.json',engine.oracle.trace);known[r['id']]=rel(folder/'features.npy');return f,known[r['id']]
        def evaluate(v,l,name,final=False):
            nonlocal sequences,reused
            key=mask(v,l);cached=prefix_cache.setdefault(key,{});r=req[name]
            if name in cached:
                path=ROOT/cached[name];a=np.load(path,allow_pickle=False);z=a if a.ndim==1 else a[0]
                assert z.shape==(151936,) and z.dtype==np.float32 and np.isfinite(z).all()
                token=int(z.argmax());raw=engine.tokenizer.decode([token],skip_special_tokens=True,clean_up_tokenization_spaces=False);reused+=1
                return dict(request_id=name,token_id=token,raw_first_token=raw,decision=decision(raw),correct=decision(raw)==('Yes' if r['knife_present'] else 'No'),prefix_reused=True,logits_path=rel(path),logits_sha256=sha(path),generated_new_tokens=0,application_stop='BINARY_DECISION' if decision(raw)!='Invalid' else 'NO_UNAMBIGUOUS_BINARY_TOKEN',natural_EOS_claimed=False)
            guard(final);f,fpath=feature(v,r,final);row,z=engine.answer(r,f,1);sequences+=1
            folder=OUT/'prefixes'/key/name;saved_array(folder/'first_logits.npy',z[0]);token=row['token_ids'][0]
            raw=engine.tokenizer.decode([token],skip_special_tokens=True,clean_up_tokenization_spaces=False)
            record=dict(request_id=name,token_id=token,raw_first_token=raw,decision=decision(raw),correct=decision(raw)==('Yes' if r['knife_present'] else 'No'),prefix_reused=False,logits_path=rel(folder/'first_logits.npy'),logits_sha256=sha(folder/'first_logits.npy'),feature_path=fpath,feature_sha256=sha(ROOT/fpath),generated_new_tokens=1,application_stop='BINARY_DECISION' if decision(raw)!='Invalid' else 'NO_UNAMBIGUOUS_BINARY_TOKEN',natural_EOS_claimed=False,cache_layers=row['cache_layers'],cache_initial=row['cache_initial'],cache_cleared=row['cache_cleared'],layer_calls=row['layer_calls'],software_seconds_not_board=row['software_seconds'])
            save(folder/'RESULT.json',record);cached[name]=record['logits_path'];return record
        def trial(v,l,label):
            nonlocal trial_count
            key=mask(v,l)
            if key in states:return states[key]
            guard()
            if trial_count>=p['budgets']['trials'] or sequences+4>p['budgets']['new_decision_sequences']-8:raise BudgetStop('trial budget')
            trial_count+=1;engine.set_active(v,l);engine.capture=True;engine.bank={}
            a=dict(name=label,vision=v,language=l,mask=key,rows={},demo_pass=False,modelled_savings_s=saving(v,l),trial_index=trial_count)
            for name in order:
                row=evaluate(v,l,name);a['rows'][name]=row
                print('DEMO_DECISION',trial_count,label,name,row['decision'],row['correct'],'REUSED' if row['prefix_reused'] else 'NEW',flush=True)
                if not row['correct']:break
            a['demo_pass']=len(a['rows'])==4 and all(r['correct'] for r in a['rows'].values())
            a['bank']=copy.deepcopy(p['base_bank']);a['bank'].update(copy.deepcopy(bank_sources.get(key,{})));a['bank'].update(copy.deepcopy(engine.bank))
            folder=OUT/'trials'/key;save(folder/'RESULT.json',a);states[key]=a
            value['trials'].append(dict(name=label,mask=key,vision=v,language=l,demo_pass=a['demo_pass'],evaluated=len(a['rows']),modelled_savings_s=a['modelled_savings_s'],result=rel(folder/'RESULT.json')))
            print('DEMO_TRIAL',trial_count,label,'PASS4' if a['demo_pass'] else 'FAIL','V',len(v),'L',len(l),'MODEL_SAVED',round(a['modelled_savings_s'],4),flush=True)
            return a
        def rankings(state,branch):
            rows=[]
            for i in state[branch]:
                k=branch+'_'+str(i).zfill(2);s=state['bank'][k];damage=(s['residual2']/max(s['output2'],1e-30))**.5
                rows.append(dict(index=i,score=damage/max(cost(branch,i),1e-9),cost=cost(branch,i),branch=branch))
            return sorted(rows,key=lambda r:(r['score'],r['index']))
        stop='twelve_rounds'
        try:
            # The already saved parent prefix is a valid, untouched fallback.
            current=trial(list(range(24)),list(range(36)),'saved_parent')
            assert current['demo_pass']
            for v,l in sorted(seed_masks.values(),key=lambda x:-saving(*x)):
                if mask(v,l) in states:continue
                a=trial(v,l,'saved_seed_'+mask(v,l))
                if a['demo_pass'] and a['modelled_savings_s']>current['modelled_savings_s']:current=a
            for step in range(1,13):
                if p['parent_hot_TTFT_s']-current['modelled_savings_s']<=26:stop='time_model_at_or_below26_requires_board_verification';break
                ranked={b:rankings(current,b) for b in ('vision','language')};short=[];remaining=[]
                for branch,rows in ranked.items():
                    if len(current[branch])<=1:continue
                    ids=[]
                    for r in rows[:4]+sorted(rows,key=lambda r:(-r['cost'],r['index']))[:3]:
                        if r['index'] not in ids:ids.append(r['index']);short.append((branch,r['index']))
                    remaining.extend((branch,r['index']) for r in rows if r['index'] not in ids)
                passed=[]
                for group in (short,remaining):
                    if group is remaining and passed:break
                    for branch,i in group:
                        v=list(current['vision']);l=list(current['language']);(v if branch=='vision' else l).remove(i)
                        if not v or not l:continue
                        a=trial(v,l,'r'+str(step)+'_drop_'+branch+'_'+str(i))
                        if a['demo_pass']:passed.append((branch,i,a))
                selected=None
                if passed:
                    passed.sort(key=lambda x:(-cost(x[0],x[1]),x[0],x[1]));selected=passed[0][2]
                    combos=[]
                    for n in (4,3,2):
                        if len(passed)>=n:combos.append(passed[:n])
                    if len(passed)>=3:combos.append([passed[0],passed[2]])
                    for combination in combos:
                        v=list(current['vision']);l=list(current['language'])
                        for b,i,_ in combination:(v if b=='vision' else l).remove(i)
                        if not v or not l:continue
                        a=trial(v,l,'r'+str(step)+'_combine_'+mask(v,l))
                        if a['demo_pass'] and a['modelled_savings_s']>selected['modelled_savings_s']:selected=a;break
                else:
                    pool=sorted(short,key=lambda x:-cost(*x))[:6]
                    pairs=sorted(itertools.combinations(pool,2),key=lambda xs:-sum(cost(*x) for x in xs))[:12]
                    for pair in pairs:
                        v=list(current['vision']);l=list(current['language'])
                        for b,i in pair:(v if b=='vision' else l).remove(i)
                        if not v or not l:continue
                        a=trial(v,l,'r'+str(step)+'_pair_'+mask(v,l))
                        if a['demo_pass'] and (selected is None or a['modelled_savings_s']>selected['modelled_savings_s']):selected=a
                    if selected is None:
                        removed=sorted([('vision',i) for i in range(24) if i not in current['vision']]+[('language',i) for i in range(36) if i not in current['language']],key=lambda x:cost(*x))[:4]
                        proposals=[]
                        for restore in removed:
                            for pair in pairs:
                                if sum(cost(*x) for x in pair)<=cost(*restore):continue
                                v=list(current['vision']);l=list(current['language']);(v if restore[0]=='vision' else l).append(restore[1]);v.sort();l.sort()
                                for b,i in pair:(v if b=='vision' else l).remove(i)
                                if v and l:proposals.append((saving(v,l),v,l))
                        for _,v,l in sorted(proposals,reverse=True)[:8]:
                            a=trial(v,l,'r'+str(step)+'_exchange_'+mask(v,l))
                            if a['demo_pass'] and (selected is None or a['modelled_savings_s']>selected['modelled_savings_s']):selected=a
                if selected is None:stop='no_acceptable_single_pair_or_exchange_in_bounded_neighborhood';break
                current=selected;record={k:current[k] for k in ('name','mask','vision','language','modelled_savings_s')};record['round']=step
                value['rounds'].append(record);save(OUT/('ROUND_'+str(step)+'.json'),record)
                print('DEMO_ROUND_SELECTED',record,flush=True)
        except BudgetStop as e:stop=str(e)
        assert current and current['demo_pass']
        # A budget stop may occur just after a better complete trial; keep the actual best tested state.
        current=max((a for a in states.values() if a['demo_pass']),key=lambda a:a['modelled_savings_s'])
        winner=dict(name=current['name'],vision=current['vision'],language=current['language'],demo_rows=current['rows'],demo_correct=4,demo_total=4,modelled_savings_s=current['modelled_savings_s'],modelled_TTFT_s=p['parent_hot_TTFT_s']-current['modelled_savings_s'],time_is_model_only=True,actual_board_TTFT=None,stop=stop,selected_before_other8_calibration=True)
        save(OUT/'WINNER_FROZEN.json',winner);print('DEMO_WINNER_FROZEN',winner,flush=True)
        engine.set_active(current['vision'],current['language']);engine.capture=False;context={}
        for name in req:
            if name in order:continue
            context[name]=evaluate(current['vision'],current['language'],name,final=True)
            print('DEMO_OUTSIDE_SCOPE',name,context[name]['decision'],context[name]['correct'],flush=True)
        value.update(status='COMPLETE_FIXED_DEMO_WINNER_4_OF_4_SOFTWARE_ONLY',original_rc=0,winner=winner,other8_calibration=context,
            full12_correct=4+sum(r['correct'] for r in context.values()),new_decision_sequences=sequences,reused_prefixes=reused,new_vision_forwards=visual_count,arrays_saved_bytes=byte_count,trials_completed=trial_count,stop=stop,
            answer_scope='Only4 frozen demo windows accepted; remaining8 are context and do not alter selection. First unforced token field, application stop, not natural full-answer EOS evidence.',new_board_TTFT=None,heldout_still_closed=True)
    except BaseException:value['traceback']=traceback.format_exc()
    finally:
        if engine:engine.close()
        value['elapsed_s']=time.monotonic()-began;save(OUT/'RESULT.json',value)
        print(value['status'],value.get('traceback',''),flush=True)
    return value['original_rc']
if __name__=='__main__':raise SystemExit(main())
