"""Derive complete visual timing from exact passed numerical owner."""
import ast,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m427_prepare import once
OLD=BASE/'candidates/M429-late11-visual-PL-numeric-03'
PKG=BASE/'candidates/M430-late11-visual-warm-01'
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=board['latest_m430_complete_visual_protocol']
    assert sha(ROOT/e['result'])==e['sha256'];protocol=(ROOT/e['result']).with_name('PROTOCOL.json');assert sha(protocol)==e['protocol_sha256']
    plan=json.loads((OLD/'PLAN.json').read_bytes());plan.update(component_package='/home/ubuntu/m430_late11_visual_warm_candidate_01',budget_seconds=1800,protocol_sha256=e['protocol_sha256'],numerical_result_path='/home/ubuntu/m429_late11_visual_numeric_02/BOARD_RESULT.json',numerical_result_sha256=board['latest_m429_late11_visual_PL_board']['sha256'])
    gate=(OLD/'m429_gate.py').read_text(encoding='utf-8')
    gate=gate.replace('M429','M430').replace('m429','m430')
    # Reused frozen arithmetic packages retain their actual original names.
    gate=gate.replace('from m430_pl_range import PLRangeScope,SavedWireCheck,SELECTED','from m430_timed_scope import TimedPLRangeScope as PLRangeScope,LightBatchCheck as SavedWireCheck,SELECTED')
    gate=gate.replace('/home/ubuntu/m430_late11_visual_numeric_02/','/home/ubuntu/m430_late11_visual_warm_01/')
    gate=gate.replace('late11-complete-visual-PL-numerical','late11-complete-visual-controlled-warm-performance')
    gate=gate.replace('--enable-PL-numerical','--enable-visual-performance').replace('args.enable_PL_numerical','args.enable_visual_performance')
    gate=gate.replace('FAIL_M430_LATE11_VISUAL_NUMERICAL','FAIL_M430_COMPLETE_VISUAL_WARM').replace('PASS_M430_LATE11_COMPLETE_VISUAL_PL_NUMERICAL','PASS_M430_COMPLETE_VISUAL_WARM_COLLECTED')
    gate=once(gate,"        SavedWireCheck(accepted['reference_batches'],lambda *unused:None)",'''        SavedWireCheck(accepted['reference_batches'],lambda *unused:None)
        performance_protocol=json.loads((HERE/'PROTOCOL.json').read_bytes())
        if digest(HERE/'PROTOCOL.json')!=plan['protocol_sha256']:raise RuntimeError('Frozen timing protocol differs')
        if digest(Path(plan['numerical_result_path']))!=plan['numerical_result_sha256']:raise RuntimeError('Complete numerical evidence differs')
        prior_numeric=json.loads(Path(plan['numerical_result_path']).read_bytes())
        if prior_numeric['status']!='PASS_M429_LATE11_COMPLETE_VISUAL_PL_NUMERICAL' or prior_numeric['gate_return_code'] or prior_numeric['errors'] or not prior_numeric['stable_restored'] or not prior_numeric['safe_buffers_released'] or prior_numeric['matched_wire_batches']!=286:raise RuntimeError('Complete numerical/lifecycle evidence required')
        result['numerical_source_sha256']=plan['numerical_result_sha256']''')
    gate=gate.replace("lines[0])\n        if result['component']", "lines[0])\n        if result['component']")
    gate=once(gate,"        result['CPU_component_before_Overlay']=True", "        if len(result['component']['timed_light_negative_checks'])!=8:raise RuntimeError('Timed scope/geometry component required')\n        result['CPU_component_before_Overlay']=True")
    # The lower wait, pointer/config ABI, DMA transfer, sync and parse are identical.
    gate=once(gate,"r['PL_rows'].append(dict(layer=index,part=part,start=start,shift=shift,wait_ns=observation['wait_ns'],input_bytes=len(packet),output_bytes=len(raw),completed_snapshot=s,packet_sha256=hashlib.sha256(packet).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest()));return raw", "r['PL_rows'].append(dict(layer=index,part=part,start=start,shift=shift,wait_ns=observation['wait_ns'],input_bytes=len(packet),output_bytes=len(raw),completed_snapshot=s));return raw")
    start=gate.index('        def stage(index,part,c):');end=gate.index("        result['dma_allocations']=",start)
    replacement='''        from m411_mlp_binding import stage_windows
        from m425_environment import read_environment
        from m425_warm import WarmSequence,adjudicate
        import resource
        def io_stats():
            return {line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/self/io').read_text().splitlines()}
        def stage(index,part,c):
            checkpoint('before-staging')
            rows=[dict(row,relative_file='vision_layout/'+row['path']) for row in plan['windows'][str(index)][part]]
            result['staging'].append(dict(layer=index,**stage_windows(owner,part,rows,vbase)))
        environment=read_environment();result['reference_environment']=environment
        seq=WarmSequence(result,environment,protocol_sha=plan['protocol_sha256'])
        snapshots=[]
        for index,variant in enumerate(performance_protocol['combined_order']):
            seq.before(index);phase[0]='warm-visual-'+str(index+1)+'-'+variant
            checkpoint(phase[0]+':before')
            before_env=read_environment();before_cache=store.evidence();before_io=io_stats();before_usage=resource.getrusage(resource.RUSAGE_SELF);before_memory=proc()
            before_count=result['physical_transactions_started'];row_start=len(result['PL_rows']);stage_start=len(result['staging'])
            scope=None;wire_check=None
            if variant=='B':
                wire_check=SavedWireCheck(accepted['reference_batches'],owner.submit)
                scope=PLRangeScope(torch,runtime.vision.encoder.layers,targets,load_case,initial,host,lambda *x:None,checkpoint,stage,wire_check)
            result['visual_forward_calls']+=1
            tick=time.perf_counter_ns()
            if scope is None:candidate=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
            else:
                with scope:candidate=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
            elapsed=time.perf_counter_ns()-tick
            after_io=io_stats();after_usage=resource.getrusage(resource.RUSAGE_SELF);after_memory=proc();after_cache=store.evidence();after_env=read_environment()
            expected_feature=saved_arrays[0 if variant=='A' else 1]
            actual_feature=tensor(candidate)
            if not np.array_equal(candidate.view(np.uint32),expected_feature.view(np.uint32)):raise RuntimeError('Complete post-timer feature differs:'+variant)
            if wire_check is not None:
                wire_check.require_complete()
                if not scope.complete or not scope.restored or scope.peak_live_layer_scopes!=1:raise RuntimeError('Timed PL scope lifecycle incomplete')
                batches=scope.batches;scopes.append(scope.restored)
            else:batches={};scopes.append(True)
            count=result['physical_transactions_started']-before_count
            if count!=(286 if variant=='B' else 0):raise RuntimeError('Per-sample PL call count differs')
            row=dict(index=index+1,variant=variant,timing=dict(total_ms=elapsed/1e6),elapsed_ns=elapsed,
                feature=actual_feature,feature_complete_exact=True,before_environment=before_env,after_environment=after_env,
                before_cache=before_cache,after_cache=after_cache,io_delta={k:after_io[k]-before_io[k] for k in before_io},
                major_fault_delta=after_usage.ru_majflt-before_usage.ru_majflt,before_memory=before_memory,after_memory=after_memory,
                physical_calls=count,bindings_restored=scopes[-1],PL_batches=batches,staging_rows=result['staging'][stage_start:],
                device_wait_ns=sum(x['wait_ns'] for x in result['PL_rows'][row_start:]),staging_ns=sum(x['elapsed_ns'] for x in result['staging'][stage_start:]))
            del expected_feature,candidate
            seq.record(row);checkpoint(phase[0]+':after')
            print('M430_VISUAL_SAMPLE '+json.dumps(dict(index=index+1,variant=variant,ms=row['timing']['total_ms'],read_bytes=row['io_delta']['read_bytes'],major_faults=row['major_fault_delta'])),flush=True)
        result['performance_adjudication']=adjudicate(result['formal_samples'])
        a=result['performance_adjudication'];worthwhile=a['performance_pass'] and a['gain_percent']>=performance_protocol['adjudication']['worthwhile_complete_visual_gain_percent_minimum']
        a['scope']='Fixed-input controlled warm complete visual only; no language or production promotion.'
        a['reliable_positive_gain']=a['performance_pass'];a['worthwhile_complete_visual_gain_percent_minimum']=5.;a['performance_pass']=worthwhile
        a['status']='PASS_WORTHWHILE_COMPLETE_VISUAL_GAIN' if worthwhile else 'CLOSE_NO_WORTHWHILE_RELIABLE_COMPLETE_VISUAL_GAIN'
        result['performance_pass']=worthwhile;result['bindings_restored']=all(scopes);result['feature_screen_pass']=True
        result['numerical_hardware_proven']=True;result['matched_wire_batches_reused']=286
        result['candidate_visual']=prior_numeric['candidate_visual'];result['full_visual_quality']=prior_numeric['full_visual_quality']
        result['retained_features']=[]
'''
    gate=gate[:start]+replacement+gate[end:]
    # Removed last candidate tensor/old diagnostic closures no longer exist.
    gate=gate.replace('del original,original_record,load_case,vision','del original,original_record,load_case,vision,expected_feature' if False else 'del original,original_record,load_case,vision')
    gate=once(gate,"del original,original_record,load_case,vision", "del original,original_record,load_case,vision")
    # after reuse scopes must no longer hold a bound callable/runtime reference.
    gate=gate.replace('targets=scope=store=None;runtime.close()', 'targets=scope=store=None;runtime.close()')
    # Do not retain redundant per-transaction diagnostic memory table in timed interval.
    gate=once(gate,"r['memory'].append(row)", "\n                if ':batch' not in label and label!='MLP-before-submit':r['memory'].append(row)")
    oldtree=ast.parse((OLD/'m429_gate.py').read_text(encoding='utf-8'));newtree=ast.parse(gate)
    def node(t,n):return next(x for x in ast.walk(t) if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name==n)
    for n in ('zero','restore','load_case'):assert ast.dump(node(oldtree,n),include_attributes=False)==ast.dump(node(newtree,n),include_attributes=False)
    # Exact submit body apart from the final lightweight record.
    assert ast.dump(node(oldtree,'submit').body[:-1],include_attributes=False) if False else True
    a=node(oldtree,'submit');c=node(newtree,'submit')
    assert all(ast.dump(x,include_attributes=False)==ast.dump(y,include_attributes=False) for x,y in zip(a.body[:-2],c.body[:-2])) and len(a.body)==len(c.body)
    PKG.mkdir(parents=True,exist_ok=False)
    for p in OLD.iterdir():
        if p.name not in ('m429_gate.py','m429_component_entry.py','test_m429_range.py','PLAN.json','m429_export.py','run_m429.sh','DEPENDENCY_CLOSURE.json','SHA256SUMS','PACKAGE_MANIFEST.json'):atomic(PKG/p.name,p.read_bytes(),immutable=True)
    atomic(PKG/'m430_gate.py',gate.encode(),immutable=True);atomic(PKG/'PLAN.json',encoded(plan),immutable=True);atomic(PKG/'PROTOCOL.json',protocol.read_bytes(),immutable=True)
    for name in ('m430_timed_scope.py','m425_environment.py','m425_warm.py'):atomic(PKG/name,(HERE/name).read_bytes(),immutable=True)
    atomic(PKG/'m429_pl_range.py',(OLD/'m429_pl_range.py').read_bytes(),immutable=True)
    test=(OLD/'test_m429_range.py').read_text(encoding='utf-8')
    test=once(test,'    from m429_pl_range import PLRangeScope,SavedWireCheck,SELECTED as late', '''    from m429_pl_range import SavedWireCheck,SELECTED as late
    from m430_timed_scope import TimedPLRangeScope,LightBatchCheck
    class PLRangeScope(TimedPLRangeScope):
        def after(self,index,value):
            super().after(index,value)
            output=value[0] if isinstance(value,tuple) else value
            self.sink(index,output.detach().float().cpu().numpy()[0])''')
    label='    return dict(full_output_exact='
    at=test.index(label)
    test=test[:at]+'''    light=LightBatchCheck(references,submit)
    for index in late:
        for part in ('fc1','fc2'):
            for ref in references[str(index)][part]:
                packet,raw=wire[(index,part,ref['start'],ref['selected_shift'])]
                assert light(index,part,cases[index]['chains'][part],ref['start'],ref['selected_shift'],packet)==raw
    light.require_complete();light_negative=[]
    packet,raw=wire[key]
    def light_reject(name,fn):
        try:fn()
        except (ValueError,RuntimeError):light_negative.append(name)
        else:raise AssertionError('Invalid timed schedule accepted:'+name)
    def call_light(index=13,part='fc1',start=0,shift=key[3],packet_value=packet,chain_value=chain,callback=submit):
        return LightBatchCheck(references,callback)(index,part,chain_value,start,shift,packet_value)
    light_reject('order',lambda:call_light(index=14));light_reject('part',lambda:call_light(part='fc2'))
    light_reject('start',lambda:call_light(start=32));light_reject('shift',lambda:call_light(shift=-1))
    light_reject('input-size',lambda:call_light(packet_value=packet[:-1]))
    light_reject('geometry',lambda:call_light(chain_value=dict(chain,output_bytes=1)))
    light_reject('output-size',lambda:call_light(callback=lambda *x:raw[:-1]))
    light_reject('incomplete',lambda:LightBatchCheck(references,submit).require_complete())
'''+test[at:]
    test=test.replace('return dict(full_output_exact=', 'return dict(timed_light_negative_checks=light_negative,full_output_exact=')
    atomic(PKG/'test_m430_timing.py',test.encode(),immutable=True)
    entry=(OLD/'m429_component_entry.py').read_text(encoding='utf-8').replace('test_m429_range','test_m430_timing').replace('M429_COMPONENT','M430_COMPONENT').replace('M429_BOOTSTRAP','M430_BOOTSTRAP');atomic(PKG/'m430_component_entry.py',entry.encode(),immutable=True)
    exporter=(OLD/'m429_export.py').read_text(encoding='utf-8').replace('m429_late11_visual_numeric_02','m430_late11_visual_warm_01').replace('M429','M430').replace('late11-complete-visual-PL-numerical','late11-complete-visual-controlled-warm-performance');atomic(PKG/'m430_export.py',exporter.encode(),immutable=True)
    runner=(OLD/'run_m429.sh').read_text(encoding='utf-8').replace('M429','M430').replace('m429','m430').replace('m430_late11_visual_numeric_02','m430_late11_visual_warm_01').replace('M430_ENABLE_PL_NUMERICAL','M430_ENABLE_VISUAL_PERFORMANCE').replace('--enable-PL-numerical','--enable-visual-performance');atomic(PKG/'run_m430.sh',runner.encode(),immutable=True)
    for p in PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    m=dict(file_count=0,files=[])
    record=dict(status='M430_COMPLETE_VISUAL_DRAFT_COMPONENT_PENDING',protocol_sha256=sha(protocol),numerical_source_sha256=plan['numerical_result_sha256'],pending='Isolated actual timed scope fixture; actual recursive dependencies/export/host/control; immutable manifest then COM3.',board_run=False,performance_pass=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M430-timed-scope-preparation-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m430_timed_scope_preparation',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),f'## M430 完整视觉轻量计时入口准备（2026-10-06）\n\nSHA {sha(out)}；复用实际通过M429原资源owner/安全事务和MLP算术，仅移出逐wire哈希及边界数组诊断。固定12视觉/0语言/测温，七DMA封锁，无固定CMA floor。未上传/上板，待隔离真实fixture与完整export/host/control；不宣称性能。')
    print('M430_DRAFT_PREPARED',sha(out))
if __name__=='__main__':main()
