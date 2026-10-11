"""One complete visual PL numerical gate, using saved accepted late11 reference."""
import ast,json,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m427_prepare import once
OLD=BASE/'candidates/M427-half-ranges-software-01'
PKG=BASE/'candidates/M429-late11-visual-PL-numeric-01'

def main():
    recovery={n:dict(sha256=sha(ROOT/n),lines=len((ROOT/n).read_text(encoding='utf-8-sig').splitlines())) for n in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prerequisites={}
    for key in ('latest_m427_half_software_board','latest_m427_half_closure','latest_m428_saved_language_board','latest_m428_saved_language_closure','latest_m429_streamed_scope_component'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256'] and all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'));prerequisites[key]=row
    closed=json.loads((ROOT/prerequisites['latest_m428_saved_language_closure']['result']).read_bytes())
    assert closed['fixed_input_decision_consistency_pass'] and closed['safe_buffers_released'] and closed['stable_overlay_reloaded'] and closed['hardware_visual_numeric_gate_unlocked']
    for row in json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(OLD/row['path'])==row['sha256']
    plan=json.loads((OLD/'PLAN.json').read_bytes());saved=json.loads((BASE/'candidates/M428-late11-saved-language-02/PLAN.json').read_bytes())
    for key in ('feature_directories','M426_raw_bytes','M426_raw_sha256','M427_raw_bytes','M427_raw_sha256','features','accepted_range'):plan[key]=saved[key]
    plan.update(selected_layers=list(range(13,24)),candidate_PL_enabled=True,visual_calls=1,original_visual_forward_calls=0,language_calls=0,budget_seconds=600,
        task_complete=True,maximum_automatic_candidates=1,hardware_visual_timing_unlocked=False,full_request_timing_unlocked=False,
        numeric_only=True,logical_PL_batches=286,maximum_live_weight_window_bytes=4456448,
        candidate_wire_policy='Exact all286 complete input/output SHA and all24 boundary/final feature hashes against saved M427; reject unmatched retries before a submit.',
        M428_raw_sha256=prerequisites['latest_m428_saved_language_board']['sha256'],M428_raw_bytes=(ROOT/prerequisites['latest_m428_saved_language_board']['result']).stat().st_size,
        M428_result_path='/home/ubuntu/m428_saved_feature_language_01/BOARD_RESULT.json',lower_directory='/home/ubuntu/m418_visual_linear_candidate_01',
        failure_next_step='Collect original saved bytes; debug only complete visual PL numerics/lifecycle. No timing or language expansion.')
    plan['chains']={str(i):plan['chains'][str(i)] for i in range(13,24)};plan['windows']={str(i):plan['windows'][str(i)] for i in range(13,24)}
    plan.pop('candidate_ranges');plan['prerequisites'].append(dict(path=plan['M428_result_path'],sha256=plan['M428_raw_sha256']))
    gate=(OLD/'m427_gate.py').read_text(encoding='utf-8').replace('M427','M429').replace('/home/ubuntu/m427_half_ranges_software_01/','/home/ubuntu/m429_late11_visual_numeric_01/')
    gate=once(gate,"gate_level='CPU-only-two-half-visual-MLP-screen'","gate_level='late11-complete-visual-PL-numerical'")
    gate=gate.replace('enable-software-range','enable-PL-numerical').replace('args.enable_software_range','args.enable_PL_numerical')
    gate=once(gate,"selected_layers=list(range(2,24))","selected_layers=list(range(13,24))")
    gate=once(gate,"runtime=targets=scope=store=None;owner_ref=None;scopes=[];lock=None","runtime=targets=scope=store=None;owner_ref=None;scopes=[];lock=None\n    owner=allocator=None;sealed_ids=None;restore=None;unsafe=False\n    result.update(transactions=[],PS_checkpoints=[],allocations=[],releases=[],overlay_loads=[],PL_rows=[],staging=[],physical_transactions_started=0,\n        unsafe_dma_buffers_retained=False,safe_buffers_released=True,stable_restored=False,DMA_allocator_restored=False,DMA_sealed_after_main=False)")
    gate=once(gate,"or plan['candidate_PL_enabled'] or plan['temperature_measurement_enabled']","or not plan['candidate_PL_enabled'] or plan['temperature_measurement_enabled']")
    gate=once(gate,"from m426_range02 import resolve,RangeScope,SELECTED,prefix_evidence","from m426_range02 import resolve,prefix_evidence\n        from m429_pl_range import PLRangeScope,SavedWireCheck,SELECTED\n        from m428_saved_features import load_features,read_owned\n        import m418_probe as lower\n        from m341_build_id_gate import ROOT as BOARD_ROOT,STABLE,STABLE_SHA,service_stopped\n        from board_safety import safe_to_release\n        from m414_policy import PlannedDMA,verify_owner_buffers\n        lower.EVIDENCE=OUTPUT.parent\n        if BOARD_ROOT!=RELEASE:raise RuntimeError('Frozen resource owner release root differs')")
    gate=once(gate,"        # Acquire execution lock", "        saved_arrays,saved_identities=load_features(plan)\n        task=json.loads(read_owned(Path(plan['M428_result_path']),plan['M428_raw_bytes'],plan['M428_raw_sha256']))\n        if task['status']!='PASS_M428_SAVED_FEATURE_DECISION_CONSISTENCY' or type(task['gate_return_code']) is not int or task['gate_return_code'] or task['errors'] or not task['safe_buffers_released'] or not task['stable_overlay_reloaded'] or task['vision_forward_calls'] or task['temperature_measurement_enabled']:raise RuntimeError('Saved task/lifecycle prerequisite differs')\n        candidate_source=json.loads(read_owned(Path(plan['feature_directories']['candidate'])/'BOARD_RESULT.json',plan['M427_raw_bytes'],plan['M427_raw_sha256']))\n        accepted=next(x for x in candidate_source['ranges'] if x['name']=='late_13_23')\n        result['saved_feature_identities']=saved_identities;result['software_reference_source_sha256']=plan['M427_raw_sha256'];result['task_source_sha256']=plan['M428_raw_sha256']\n        # Acquire execution lock")
    gate=gate.replace("base=RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate'","vbase=RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate'").replace("base/'", "vbase/'")
    gate=once(gate,"        layout_path=", "        result['initial_service']=service_stopped()\n        sys.path.insert(0,str(STABLE/'runtime'));import board_runtime as base\n        layout_path=")
    start=gate.index('        def load_case(index):');end=gate.index('        host,initial=',start)
    gate=gate[:start]+'''        def load_case(index):
            chains={}
            for j,part in enumerate(('fc1','fc2')):
                chain=chain_for(entries[f'model.visual.encoder.layers.{index}.mlp.{part}'],index*2+j)
                if chain!=plan['chains'][str(index)][part]:raise RuntimeError('Actual full layer chain differs')
                chains[part]=chain
            return dict(chains=chains)
'''+gate[end:]
    gate=once(gate,"            ref=baseline_boundary(original_record,index)","            if tensor(arr)!=accepted['boundary_comparison'][index]['candidate']:raise RuntimeError('Complete saved software boundary differs:'+str(index))\n            ref=baseline_boundary(original_record,index)")
    gate=once(gate,"scope=RangeScope(torch,runtime.vision.encoder.layers,targets,selected,mode,load_case,initial,host,sink,checkpoint)","scope=PLRangeScope(torch,runtime.vision.encoder.layers,targets,load_case,initial,host,sink,checkpoint,stage,wire_check)")
    old_owner=(BASE/'candidates/M420-layers12-13-full-visual-02/m420_gate.py').read_text(encoding='utf-8')
    owner_code=old_owner[old_owner.index('        class WorkOwner'):old_owner.index('        visual_b,cap_b,pl=')]
    owner_code=owner_code.replace("owner=WorkOwner(base,r);lower_case=specs[13];lower_package=Path(plan['lower_packages']['13'])","owner=WorkOwner(base,r);lower_package=Path(plan['lower_directory']);lower_case=json.loads((lower_package/'BOARD_CASES.json').read_bytes())")
    stage_start=owner_code.index('        def stage(index,part,c):')
    owner_code=owner_code[:stage_start]+'''        def stage(index,part,c):
            checkpoint('before-staging')
            rows=plan['windows'][str(index)][part];tick=time.perf_counter_ns()
            for buf,row in zip(owner.buffers[:4],rows):
                raw=read_exact(vbase/'vision_layout'/row['path'],row['bytes'],row['sha256'],offset=row['offset'],file_size=row['file_bytes'])
                buf[:len(raw)]=np.frombuffer(raw,np.uint8);buf.sync_to_device()
                del raw
            result['weight_windows'].setdefault(str(index),{})[part]=rows
            result['staging'].append(dict(layer=index,part=part,bytes=sum(x['bytes'] for x in rows),elapsed_ns=time.perf_counter_ns()-tick))
        wire_check=SavedWireCheck(accepted['reference_batches'],owner.submit)
'''
    # Unchanged owner transaction/timeout/safe-release code; only layer/window selection is new.
    owner_code=owner_code.replace("'MLP-before-submit'","'MLP-before-submit'")
    start=gate.index("        result['retained_features']=[]");end=gate.index("        result['backend_after']",start)
    gate=gate[:start]+'''        r=result
'''+owner_code+'''        result['overlay_loaded']=True;result['DMA_sealed_after_main']=True
        active_range=dict(name='late_13_23_PL',boundary_comparison=[])
        candidate=vision('PL',candidate_sink,SELECTED)
        wire_check.require_complete()
        result['candidate_visual']=tensor(candidate)
        if not np.array_equal(candidate.view(np.uint32),saved_arrays[1].view(np.uint32)):raise RuntimeError('Complete final saved software feature differs')
        result['full_visual_quality']=visual_quality(original,candidate)
        result['feature_screen_pass']=result['full_visual_quality']['feature_screen_pass']
        if not result['feature_screen_pass']:raise RuntimeError('Unchanged full feature quality rejected')
        result['boundary_comparison']=active_range['boundary_comparison'];result['PL_batches']=scope.batches
        result['matched_wire_batches']=len(wire_check.seen);result['peak_live_layer_scopes']=scope.peak_live_layer_scopes
        result['numerical_hardware_proven']=True;result['bindings_restored']=all(scopes)
        result['retained_features']=[array_file(OUTPUT.parent/'late_13_23_PL_visual.npy',candidate)]
        result['dma_allocations']=len(result['allocations']);result['fpga_transactions']=result['physical_transactions_started']+len(result['transactions'])
'''+gate[end:]
    start=gate.index('        del original,original_record');end=gate.index('    except BaseException as error:',start)
    gate=gate[:start]+'''        owner.release();sealed_ids=None
        del original,original_record,load_case,vision
        targets=scope=store=None;runtime.close();runtime=None;gc.collect();result['visual_owner_closed']=owner_ref() is None
        if not result['visual_owner_closed'] or not result['bindings_restored']:raise RuntimeError('Visual scope/owner close unproven')
        restore();result['boot_unchanged']=digest(boot)==boot_sha;result['cmdline_unchanged']=Path('/proc/cmdline').read_text()==cmdline;result['final_service']=service_stopped()
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected system changed')
        result['status']='PASS_M429_LATE11_COMPLETE_VISUAL_PL_NUMERICAL';result['gate_return_code']=0
'''+gate[end:]
    start=gate.index('    finally:');end=gate.index("    return result['gate_return_code']",start)
    gate=gate[:start]+'''    finally:
        unsafe=owner is not None and (owner.active or (bool(owner.buffers) and not owner.safe()))
        if not unsafe:
            try:
                if scope is not None and (scope.handles or scope.active):scope.__exit__(None,None,None)
                result['bindings_restored']=all(scopes) and (scope is None or scope.restored)
                if owner is not None:owner.release()
                sealed_ids=None;scope=targets=store=None
                if runtime is not None:runtime.close();runtime=None;gc.collect();result['visual_owner_closed']=owner_ref() is None
                if owner is not None and owner.overlay is not None and not result['stable_restored']:restore()
            except BaseException as error:unsafe=True;result['errors'].append(dict(type='CleanupUnproven',message=str(error)))
        if allocator is not None and not unsafe:
            try:allocator.close()
            except BaseException as error:unsafe=True;result['errors'].append(dict(type='AllocatorRestoreUnproven',message=str(error)))
        result['unsafe_dma_buffers_retained']=unsafe;result['safe_buffers_released']=not unsafe
        if owner is not None and owner.kernel is not None:result['final_snapshot']=owner.base.transaction_snapshot(owner.kernel,owner.dma)
        result['dma_allocations']=len(result['allocations']);result['fpga_transactions']=result['physical_transactions_started']+len(result['transactions'])
        if unsafe:result['status']='FAIL_UNSAFE_RETAINED';result['gate_return_code']=1
        if result['gate_return_code']:result['numerical_hardware_proven']=False
        result['memory_after_cleanup']=proc();result['elapsed_s_diagnostic_not_performance']=time.monotonic()-started
        save(OUTPUT,json.dumps(result,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('utf-8'));stop.set()
        print('M429_RESULT_SAVED '+result['status'],flush=True)
        if unsafe:
            from m429_export import emit_saved
            emit_saved();print('M429_RETAIN_OWNER_PROCESS_AND_ALL_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        if lock is not None:os.close(lock)
'''+gate[end:]
    gate=gate.replace("status='FAIL_M429_HALF_RANGE_SCREEN'","status='FAIL_M429_LATE11_VISUAL_NUMERICAL'")
    # Numerical gate performs no original/software visual replay and no language call.
    assert "candidate=vision('PL'" in gate and "vision('software'" not in gate and "vision('original'" not in gate
    ast.parse(gate,feature_version=(3,10))
    PKG.mkdir(exist_ok=False,parents=True)
    texts={'m429_gate.py':gate,'m429_pl_range.py':(HERE/'m429_pl_range.py').read_text(encoding='utf-8'),
        'm411_mlp_binding.py':(HERE/'m411_mlp_binding.py').read_text(encoding='utf-8'),
        'm426_range02.py':(OLD/'m426_range02.py').read_text(encoding='utf-8'),
        'm427_saved_baseline.py':(OLD/'m427_saved_baseline.py').read_text(encoding='utf-8'),
        'm428_saved_features.py':(BASE/'candidates/M428-late11-saved-language-02/m428_saved_features.py').read_text(encoding='utf-8')}
    for name,text in texts.items():ast.parse(text,feature_version=(3,10));atomic(PKG/name,text.encode('utf-8'),immutable=True)
    for name in ('EXPECTED_VISUAL.json','SOURCE_IDENTITIES.json'):atomic(PKG/name,(OLD/name).read_bytes(),immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    record=dict(status='M429_NUMERICAL_SCOPE_PREPARED_SUPPORT_PENDING',prerequisites=prerequisites,recovery_reads=recovery,
        selected_layers=list(range(13,24)),visual_forward_calls=1,original_visual_replays=0,software_visual_replays=0,language_calls=0,
        unchanged_resource_owner_code_sha256=sha(BASE/'candidates/M420-layers12-13-full-visual-02/m420_gate.py'),
        maximum_live_weight_window_bytes=4456448,planned_main_DMA_bytes=3436560,PL_batches=286,
        fixed_CMA_floor=None,ordinary_MemAvailable_reserve_bytes=64<<20,temperature_measurement_enabled=False,
        hardware_gate_not_yet_executable=True,board_run=False,hardware_visual_numerics_pass=False,performance_pass=False,
        offline_first_attempt=dict(status='WSL_SANDBOX_ACCESS_DENIED_BEFORE_COMPONENT',stdout_sha256=sha(ROOT/'tmp/m42901/component/stdout.bin'),stderr_sha256=sha(ROOT/'tmp/m42901/component/stderr.bin')))
    out=BASE/'runs/M429-numerical-scope-preparation-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m429_numerical_scope_preparation',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),
        f'## M429 后11层完整视觉PL数值范围准备（2026-10-06）\n\nSHA {sha(out)}；M428固定输入任务一致性已闭合，仅13–23的MLP两个Linear；复用保存软件全部286输入/输出SHA、24边界及完整feature，不重跑原版/软件视觉、不执行语言、不测温。原M420 owner安全事务/释放组织与M414七DMA封锁复用；尚待实际导出/解码/控制/依赖门禁与packet封装，未上传/上板，性能未解锁。')
    print('M429_SCOPE_PREPARATION_SYNC',sha(out))

if __name__=='__main__':main()
