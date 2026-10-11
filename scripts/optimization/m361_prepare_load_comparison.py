"""Freeze one common constructor-only observer for stable/candidate ABBA."""
import ast
import json
import shutil
import m351_workflow as w
from m358_prepare_capacity import generate,replace_once

PKG=w.BASE/'candidates/M361-common-load-observer-01'
OUT=w.BASE/'runs/M361-load-comparison-preparation-01'
OLD=w.BASE/'candidates/M358-m357-load-only-03'

def source():
    s=generate().replace('M358','M361').replace('m358','m361')
    s=replace_once(s,'from owned_buffer_release import OwnedBufferRelease','from owned_buffer_release import OwnedBufferRelease\nfrom m361_observers import observe_call,tokenizer_proxy,retained_inventory,mapping_inventory,ROLES')
    s=replace_once(s,"EVIDENCE = Path('/home/ubuntu/m361_candidate_capacity_01')","EVIDENCE = None\nTARGET = None\nTARGET_SHA = None\nTARGET_BUILD = None")
    s=replace_once(s,"    parser = argparse.ArgumentParser(); parser.add_argument('manifest_sha'); parser.add_argument('--enable-load-only',action='store_true'); args = parser.parse_args()","    global EVIDENCE,TARGET,TARGET_SHA,TARGET_BUILD\n    parser = argparse.ArgumentParser(); parser.add_argument('manifest_sha'); parser.add_argument('case',choices=('A1','B1','B2','A2')); parser.add_argument('--enable-load-only',action='store_true'); args = parser.parse_args()\n    is_candidate=args.case.startswith('B')\n    TARGET=CANDIDATE if is_candidate else STABLE\n    TARGET_SHA=CAND_SHA if is_candidate else STABLE_SHA\n    TARGET_BUILD='0x4D333537' if is_candidate else '0x4D395832'\n    EVIDENCE=Path('/home/ubuntu/m361_load_comparison_01')/args.case")
    s=replace_once(s,"EVIDENCE.mkdir(mode=0o700,parents=False,exist_ok=False)","EVIDENCE.mkdir(mode=0o700,parents=True,exist_ok=False)")
    s=replace_once(s,"build_id='0x4D333537'","build_id=TARGET_BUILD,case=args.case,io_events=[],common_runner_sha256=sha256(Path(__file__)),cache_policy='natural cache; no clearing; identical policy is not identical cache residency'")
    s=replace_once(s,"write_json(EVIDENCE / 'progress.json', result)","write_json(EVIDENCE / 'progress.json',dict(case=args.case,stage=row,allocated_buffers=result['allocated_buffers'],released_buffers=result['released_buffers']))")
    s=replace_once(s,"        inspected = preflight.inspect", "        patch(preflight,'digest',observe_call(preflight.digest,'release_preflight.digest',mark,result['io_events']))\n        for module in (base,video_server,sys.modules['video_language_runtime'],sys.modules['ps_vision_runtime']):\n            patch(module,'sha256',observe_call(module.sha256,module.__name__+'.sha256',mark,result['io_events']))\n        import tokenizers\n        original_tokenizer=tokenizers.Tokenizer\n        observed_from_file=observe_call(original_tokenizer.from_file,'tokenizer.from_file',mark,result['io_events'])\n        patch(tokenizers,'Tokenizer',tokenizer_proxy(original_tokenizer,observed_from_file))\n        inspected = preflight.inspect")
    s=s.replace('verify_self(CANDIDATE,CAND_SHA)','verify_self(TARGET,TARGET_SHA)')
    s=s.replace("'--candidate',str(CANDIDATE)","'--candidate',str(TARGET)").replace("'--expected-package-manifest-sha256',CAND_SHA","'--expected-package-manifest-sha256',TARGET_SHA")
    s=replace_once(s,"            buffer = original_allocate(*a,**kw); allocations.append(buffer)","            index=len(allocations)\n            if index>=7: raise RuntimeError('Unexpected extra DMA allocation refused')\n            mark('before-DMA-allocation-'+ROLES[index])\n            buffer = original_allocate(*a,**kw); allocations.append(buffer)\n            mark('after-DMA-allocation-'+ROLES[index])")
    s=replace_once(s,"row=dict(bytes=int(buffer.nbytes),address=int(base.physical_address(buffer)))","row=dict(bytes=int(buffer.nbytes),address=int(base.physical_address(buffer)),role=ROLES[index],allocation_order=index)")
    s=replace_once(s,"super().__init__(CANDIDATE/'overlay/m120_m89x2_t32.bit',*a[1:],**kw)","super().__init__(TARGET/'overlay/m120_m89x2_t32.bit',*a[1:],**kw)")
    s=replace_once(s,"        board_cls = m243_video_server.M238PrefillRuntime","        patch(pynq,'Overlay',observe_call(pynq.Overlay,'pynq.Overlay',mark,result['io_events']))\n        board_cls = m243_video_server.M238PrefillRuntime")
    s=replace_once(s,"        loaded = mark('complete-runtime-loaded-retained')","        loaded = mark('complete-runtime-loaded-retained')\n        result['retained_inventory']=retained_inventory(engine,runtime,allocations)\n        result['retained_mappings']=mapping_inventory()")
    # A failed capacity check is still a valid load diagnostic; retain +2s checkpoint in every case.
    s=replace_once(s,"        if not result['loaded_capacity']['meets_threshold']: raise CapacityRejected('M357 complete runtime reserve rejected: '+repr(result['loaded_capacity']))\n",'')
    s=replace_once(s,"        if not result['settled_capacity']['meets_threshold']: raise CapacityRejected('M357 settled reserve rejected: '+repr(result['settled_capacity']))","        result['diagnostic_completed']=True\n        result['boot_unchanged'] = sha256(boot) == before_boot\n        result['cmdline_unchanged'] = Path('/proc/cmdline').read_text(encoding='utf-8') == before_cmd\n        if not result['boot_unchanged'] or not result['cmdline_unchanged']: raise RuntimeError('Protected identities changed')\n        if not (result['loaded_capacity']['meets_threshold'] and result['settled_capacity']['meets_threshold']): raise CapacityRejected('Complete runtime reserve rejected: '+repr(result['loaded_capacity']))")
    s=s.replace('PASS_M357_COMPLETE_RUNTIME_CAPACITY','PASS_COMPLETE_RUNTIME_CAPACITY').replace('FAIL_M357_COMPLETE_RUNTIME_CAPACITY','FAIL_COMPLETE_RUNTIME_CAPACITY')
    s=s.replace('from m361_export_result import emit_saved\n            emit_saved()','from m361_export_result import emit_saved\n            emit_saved(args.case)')
    ast.parse(s,feature_version=(3,10));return s

def prepare():
    assert not PKG.exists() and not OUT.exists()
    prerequisite=w.BASE/'runs/M360-existing-load-analysis-01/RESULT.json'
    assert w.sha(prerequisite)=='807b1c061fcb99507d78651dd6b32151662ab8d3d425d861b810f061f51fa874'
    for p in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert w.sha(prerequisite) in (w.ROOT/p).read_text(encoding='utf-8-sig')
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:assert w.sha(OLD/row['path'])==row['sha256']
    PKG.mkdir(parents=True)
    names=['measurement.py','board_safety.py','m341_build_id_gate.py','m120_board_common.py','m120_board_env_preflight.py','frozen_video_identity.py','memory_lifecycle.py','ps_slot_capacity.py','SOURCE_CLOSURE.json','M348_SOURCE_IDENTITIES.json','HARDWARE_CLOSURE.json','M357_COMPARE_PREREQUISITE.json']
    for name in names:shutil.copyfile(OLD/name,PKG/name)
    for name in ('owned_buffer_release.py','m361_observers.py','m361_export_result.py'):shutil.copyfile(w.HERE/name,PKG/name)
    w.atomic(PKG/'m361_load_only_probe.py',source().encode('utf-8'))
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
[[ $# == 3 && $3 =~ ^(A1|B1|B2|A2)$ ]] || exit 64
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m361_export_result.py" "$3"; exit 0; fi
[[ $2 == Run && ${M361_ENABLE_LOAD_ONLY:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m361_load_comparison_01/$3 ]] || exit 67
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
"$task_python" -B "$task_dir/m361_load_only_probe.py" "$1" "$3" --enable-load-only
task_gate_rc=$?
"$task_python" -B "$task_dir/m361_export_result.py" "$3"
task_export_rc=$?
set -e
echo "M361_DONE case=$3 gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    w.atomic(PKG/'run_m361_load_only.sh',runner.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m361-common-constructor-memory-observer-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    r=dict(status='PREPARED_PENDING_OFFLINE_SUPPORT_VALIDATION',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),package_files=len(rows),package_bytes=sum(x['bytes'] for x in rows),board_executed=False,ordered_cases=['A1','B1','B2','A2'],only_variant_difference='Overlay path; common complete original source/assets/buffer/observer policy',identical_cache_residency_claimed=False,cache_eviction=False,model_forward_calls=0,fpga_transactions=0,required_cma_bytes=64<<20,required_mem_available_bytes=64<<20,next_step='Offline failure/syntax/closure checks, then COM3 auth/upload. Every case collected/synchronized before next; errors other than capacity rejection stop the series.')
    w.atomic(OUT/'RESULT.json',w.encoded(r),immutable=True)
    print(json.dumps(r))

if __name__=='__main__':prepare()
