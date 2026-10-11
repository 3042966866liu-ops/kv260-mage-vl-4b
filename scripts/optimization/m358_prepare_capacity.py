"""Freeze an independent, no-forward capacity gate for the verified M357 bit."""
import ast
import json
import shutil
import m351_workflow as w

BASE=w.BASE;ROOT=w.ROOT
OLD=BASE/'candidates/M352-load-ps-slot-01'
NEW=BASE/'candidates/M358-m357-load-only-03'
RUN=BASE/'runs/M358-capacity-preparation-03'
CAND=BASE/'candidates/M357-private-activation-01'
PRIOR='ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'

def replace_once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

def generate():
    s=(OLD/'m352_load_ps_slot_probe.py').read_text(encoding='utf-8')
    s=s.replace('M352','M358').replace('m352','m358')
    s=s.replace('0x4D395832','0x4D333537').replace('6274767c15ac4ea5c81e6289ef4f90d6cd7cd32c5735b5617e6c3a450cf8ef41',PRIOR)
    s=replace_once(s,'from measurement import sha256, write_json','from measurement import sha256, write_json\nfrom owned_buffer_release import OwnedBufferRelease')
    legacy="""            def guarded_free():
                observed=base.transaction_snapshot(runtime.kernel,runtime.dma)
                if not never_submitted_release(observed,runtime.host_calls,runtime.logical_calls,result['blocked_inference_attempts'],len(allocations)):
                    raise RuntimeError('Never-submitted lifecycle no longer proven; retain all remaining buffers')
                if row in result['released_buffers']:
                    raise RuntimeError('Duplicate original-buffer free refused')
                original_free()
                result['released_buffers'].append(row)
            buffer.freebuffer=guarded_free"""
    fixed="""            def release_proven():
                observed=base.transaction_snapshot(runtime.kernel,runtime.dma)
                return never_submitted_release(observed,runtime.host_calls,runtime.logical_calls,result['blocked_inference_attempts'],len(allocations))
            buffer.freebuffer=OwnedBufferRelease(original_free,release_proven,lambda:result['released_buffers'].append(row))"""
    s=replace_once(s,legacy,fixed)
    s=replace_once(s,"HERE = Path(__file__).resolve().parent","HERE = Path(__file__).resolve().parent\nCANDIDATE = Path('/home/ubuntu/m357_candidate_01')\nCAND_SHA = '2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'")
    s=s.replace("EVIDENCE = Path('/home/ubuntu/m358_load_memory_evidence_01')","EVIDENCE = Path('/home/ubuntu/m358_candidate_capacity_01')")
    s=s.replace("HERE/'M351_BOARD_PREREQUISITE.json'","HERE/'M357_COMPARE_PREREQUISITE.json'")
    s=replace_once(s,"prerequisite['status'] != 'PASS_PS_COMPONENT_ONLY_NO_FPGA' or prerequisite['tests_run'] != 28","prerequisite['status'] != 'PASS_M357_COMPARE' or not prerequisite['chain_performance_pass'] or not prerequisite['stable_restored']")
    s=s.replace('Exact completed M351 component prerequisite differs','Exact M357 balanced single-chain prerequisite differs')
    s=replace_once(s,"hardware['status'] != 'PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED'","hardware['status'] != 'PASS_ALL_NEW_CIRCUIT_PREREQUISITES'")
    s=replace_once(s,"checked = subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(STABLE),\n            '--expected-package-manifest-sha256',STABLE_SHA,'--result',str(envpath)],timeout=90)","verify_self(CANDIDATE,CAND_SHA)\n        checked = subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(CANDIDATE),\n            '--expected-package-manifest-sha256',CAND_SHA,'--result',str(envpath)],timeout=90)")
    s=replace_once(s,"super().__init__(*a,**kw); initialized = True","if not a or Path(a[0]).resolve() != (STABLE/'overlay/m120_m89x2_t32.bit').resolve(): raise RuntimeError('Original constructor bit argument differs')\n                super().__init__(CANDIDATE/'overlay/m120_m89x2_t32.bit',*a[1:],**kw); initialized = True")
    start=s.index("        result['pre_slot_eligibility'] = eligibility(loaded,before_slot=True)")
    end=s.index("        if runtime.host_calls != 0 or runtime.logical_calls != 0 or blocked: raise RuntimeError('Unexpected transaction/inference')",start)
    s=s[:start]+"""        def capacity(snapshot):
            mem=snapshot['system_bytes']
            row=dict(cma_free_bytes=mem['CmaFree'],mem_available_bytes=mem['MemAvailable'],required_cma_bytes=64<<20,required_mem_available_bytes=64<<20)
            row['meets_threshold']=row['cma_free_bytes']>=row['required_cma_bytes'] and row['mem_available_bytes']>=row['required_mem_available_bytes']
            return row
        result['loaded_capacity']=capacity(loaded)
        if len(allocations)!=7 or runtime.maximum_weight_window_bytes!=6963200: raise RuntimeError('Original allocation/window geometry differs')
        if not result['loaded_capacity']['meets_threshold']: raise CapacityRejected('M357 complete runtime reserve rejected: '+repr(result['loaded_capacity']))
        time.sleep(2)
        result['settled_capacity']=capacity(mark('complete-runtime-retained-plus-2s'))
        if not result['settled_capacity']['meets_threshold']: raise CapacityRejected('M357 settled reserve rejected: '+repr(result['settled_capacity']))
        result['extra_pynq_allocations']=len(allocations)-7
        result['load_only_capacity_pass']=True
"""+s[end:]
    s=s.replace('PASS_LOAD_ONLY_PS_SLOT_CAPACITY','PASS_M357_COMPLETE_RUNTIME_CAPACITY').replace('FAIL_LOAD_ONLY_PS_SLOT_CAPACITY','FAIL_M357_COMPLETE_RUNTIME_CAPACITY')
    s=s.replace('Original complete video runtime plus real touched ordinary PS slot; no GC/trim/forward/worker/PL transaction','Original complete video runtime with M357 bit; no extra CMA/PS slot, GC/trim/forward/worker/PL transaction')
    s=s.replace('Original complete runtime plus touched PS slot. All inference is blocked.','M357 complete runtime capacity only. All inference is blocked.')
    anchor="            for obj,name,original in reversed(restorations): setattr(obj,name,original)"
    s=replace_once(s,anchor,anchor+"""
            if runtime is not None and hasattr(runtime,'overlay'):
                try:
                    restored_env=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(STABLE),'--expected-package-manifest-sha256',STABLE_SHA,'--result',str(EVIDENCE/'stable_restore_environment.json')],timeout=90)
                    if restored_env.returncode: raise RuntimeError('Stable restore environment rejected')
                    from pynq import Overlay
                    restored_overlay=Overlay(str(STABLE/'overlay/m120_m89x2_t32.bit'),download=True)
                    result['stable_overlay_reloaded']=True
                    result['stable_bit_sha256']=sha256(STABLE/'overlay/m120_m89x2_t32.bit')
                    result['stable_restore_transaction_submitted']=False
                    from m120_board_common import KERNEL_NAME,DMA_NAME
                    result['stable_restore_snapshot']=base.transaction_snapshot(getattr(restored_overlay,KERNEL_NAME),getattr(restored_overlay,DMA_NAME))
                except BaseException as exc:
                    result['errors'].append('Stable reload rejected: '+str(exc));result['status']='FAIL';result['gate_return_code']=1;result['memory_capacity_proven']=False
""")
    s=replace_once(s,"        write_json(path,result)","        print('M358_FAILURE_OR_COMPLETION_STATE '+json.dumps(dict(gate_rc=result['gate_return_code'],candidate_snapshot=result.get('final_snapshot'),stable_snapshot=result.get('stable_restore_snapshot'),fpga_transactions=0,input_bytes=0,output_bytes=0)),flush=True)\n        write_json(path,result)")
    s=s.replace('from m358_export_result import emit_saved','from m358_export_result import emit_saved')
    ast.parse(s,feature_version=(3,10))
    return s

def prepare():
    assert not NEW.exists() and not RUN.exists()
    prior=BASE/'runs/M357-compare-board-01/BOARD_RESULT.json'
    assert w.sha(prior)==PRIOR
    assert all(PRIOR in (ROOT/p).read_text(encoding='utf-8-sig') for p in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    for package in (OLD,CAND):
        m=json.loads((package/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
        for row in m['files']:assert w.sha(package/row['path'])==row['sha256']
    s=generate()
    NEW.mkdir(parents=True);RUN.mkdir(parents=True)
    names=['measurement.py','board_safety.py','m341_build_id_gate.py','m120_board_common.py','m120_board_env_preflight.py','frozen_video_identity.py','memory_lifecycle.py','ps_slot_capacity.py','SOURCE_CLOSURE.json','M348_SOURCE_IDENTITIES.json']
    for name in names:shutil.copyfile(OLD/name,NEW/name)
    shutil.copyfile(CAND/'owned_buffer_release.py',NEW/'owned_buffer_release.py')
    shutil.copyfile(CAND/'HARDWARE_CLOSURE.json',NEW/'HARDWARE_CLOSURE.json')
    shutil.copyfile(prior,NEW/'M357_COMPARE_PREREQUISITE.json')
    w.atomic(NEW/'m358_load_only_probe.py',s.encode('utf-8'))
    shutil.copyfile(ROOT/'scripts/optimization/m358_export_result.py',NEW/'m358_export_result.py')
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
[[ $# == 2 ]] || exit 64
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m358_export_result.py"; exit 0; fi
[[ $2 == Run && ${M358_ENABLE_LOAD_ONLY:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m358_candidate_capacity_01 ]] || exit 67
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
"$task_python" -B "$task_dir/m358_load_only_probe.py" "$1" --enable-load-only
task_gate_rc=$?
"$task_python" -B "$task_dir/m358_export_result.py"
task_export_rc=$?
set -e
echo "M358_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    w.atomic(NEW/'run_m358_load_only.sh',runner.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(NEW.iterdir())]
    manifest=dict(schema='m358-m357-load-only-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))
    w.atomic(NEW/'PACKAGE_MANIFEST.json',w.encoded(manifest))
    r=dict(status='PREPARED_NO_FORWARD_M357_CAPACITY_GATE',build_id='0x4D333537',prior_sha256=PRIOR,manifest_sha256=w.sha(NEW/'PACKAGE_MANIFEST.json'),package_path=NEW.relative_to(ROOT).as_posix(),files=len(rows),bytes=manifest['total_bytes'],required_cma_bytes=64<<20,required_mem_available_bytes=64<<20,extra_ps_slot=False,extra_cma_bank=False,all_original_release_hashes_preserved=True,all_inference_blocked=True,board_executed=False)
    w.atomic(RUN/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(RUN/'RESULT.json')
    w.sync('latest_m358_capacity_preparation',dict(status=r['status'],sha256=digest,result=(RUN/'RESULT.json').relative_to(ROOT).as_posix()),f'## M358 新电路完整runtime容量门禁准备\n\nBuild0x4D333537；在已通过单链交错收益后，冻结完整原M276/M273/M238/M241加载路径及原完整资产哈希。仅替换构造Overlay路径，不执行forward/FPGA事务，不增加PSslot或CMA bank；实际runtime保留时CMA及MemAvailable各需64MiB余量。0初始DMASR仅从未提交生命周期。证据SHA `{digest}`；尚无容量PASS。')
    print(json.dumps(r))

if __name__=='__main__':prepare()
