"""Authorized stable-T32 SYS measurement. No new hardware or numerical acceptance.

Reuse immutable lower-level stable gates. Never release live DMA buffers on a
failure: persist diagnostics and hold the process/lock for operator recovery.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import threading
import time
from measurement import sha256,write_json
from board_safety import safe_to_release
from op01_support import verify_package,guarded_close_board,compact_summary

ROOT=Path('/home/ubuntu/tellme_m120_m89x2_20260901')
BASE=ROOT/'optimization_v1'
STABLE=ROOT/'m175_m120_fixed_text_candidate'
STABLE_SHA='406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f'


def resources():
    result={'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            'meminfo':Path('/proc/meminfo').read_text(),'frequencies_khz':{},'temperature_mC':{}}
    for pattern,key in (('/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq','frequencies_khz'),
                        ('/sys/class/thermal/thermal_zone*/temp','temperature_mC')):
        import glob
        for name in glob.glob(pattern):
            try:result[key][name]=int(Path(name).read_text())
            except (OSError,ValueError):result[key][name]=None
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--result',type=Path,required=True)
    parser.add_argument('--max-new-tokens',type=int,choices=(2,8,32,128),default=2)
    parser.add_argument('--imports-only',action='store_true')
    args=parser.parse_args()
    here=Path(__file__).resolve().parent
    verify_package(here,args.manifest_sha256)
    if args.result.exists():raise RuntimeError('Immutable SYS result exists')
    config=json.loads((here/'sys_config.json').read_text())
    sys.path[0:0]=[str(ROOT/p) for p in config['python_path']]
    from op00_stable_probe import service_stopped
    if args.imports_only:
        import importlib
        entries={}
        for name in ('numpy','cv2','torch','tokenizers','transformers','m238_prefill_runtime',
                     'm241_video_language_runtime','m222_vectorized_w4_runtime','sys_request','video_contract_v2'):
            module=importlib.import_module(name)
            entries[name]=dict(path=module.__file__,sha256=sha256(module.__file__))
        result=dict(status='PASS_IMPORT_ONLY',overlay_loaded=False,model_loaded=False,imports=entries,
                    package_manifest_sha256=args.manifest_sha256)
        write_json(args.result,result)
        print('OP01_IMPORTS_JSON_BEGIN');print(json.dumps(result));print('OP01_IMPORTS_JSON_END')
        return 0
    result=dict(status='FAIL',scope='OP01 SYS development measurement; numerical/quality gate separate',
        build_id=None,stable_boot_changed=False,overlay_loads=0,runtime_loads=0,errors=[],
        numerical_acceptance=False,achieved_level=None,recovery_required=False)
    board=vision=model=None
    fd=None;unsafe=False;wait_original=None;phase=['preflight'];stop=threading.Event()
    current={};transactions=[];started=time.perf_counter()
    def heartbeat():
        while not stop.wait(30):
            print('OP01_SYS_HEARTBEAT '+json.dumps(dict(phase=phase[0],physical_completed=len(transactions),
                current=current,elapsed_s=time.perf_counter()-started)),flush=True)
    threading.Thread(target=heartbeat,daemon=True).start()
    try:
        if os.geteuid()!=0:raise RuntimeError('Root authorization required')
        fd=os.open('/tmp/tellme_kv260_execution.lock',os.O_RDWR|os.O_CREAT,0o600)
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result['service_before']=service_stopped()
        result['boot_sha256_before']=sha256('/boot/firmware/boot.scr.uimg')
        result['cmdline_before']=Path('/proc/cmdline').read_text()
        result['resources_before']=resources()
        for package,expected in config['package_manifest_hashes'].items():
            if sha256(ROOT/package/'PACKAGE_MANIFEST.json')!=expected:
                raise RuntimeError('Previously verified runtime manifest changed: '+package)
            manifest=json.loads((ROOT/package/'PACKAGE_MANIFEST.json').read_text())
            # Recheck executable/config dependencies, not multiple GiB of already verified weights.
            for row in manifest['files']:
                if Path(row['path']).suffix in ('.py','.sh','.json'):
                    if sha256(ROOT/package/row['path'])!=row['sha256']:
                        raise RuntimeError('Runtime source changed: '+row['path'])
        decoder_manifest=BASE/'dependencies/opencv411_arm64_v1/INSTALLED_MANIFEST.json'
        if sha256(decoder_manifest)!='88be2d8b1f74aac57d87debe941dbf67b701242e68c53bdf0eb61d35e6317bf7':
            raise RuntimeError('Decoder identity changed')
        env_result=args.result.with_name(args.result.stem+'_environment.json')
        preflight=subprocess.run([sys.executable,str(STABLE/'runtime/m120_board_env_preflight.py'),
            '--candidate',str(STABLE),'--expected-package-manifest-sha256',STABLE_SHA,
            '--result',str(env_result)],timeout=90)
        if preflight.returncode:raise RuntimeError('Stable environment preflight failed')
        result['preflight']=json.loads(env_result.read_text())
        import board_runtime as base
        from m238_prefill_runtime import M238PrefillRuntime
        from m241_video_language_runtime import M241VideoLanguageModel
        from m222_vectorized_w4_runtime import M222PSVisionRuntime
        from board_preprocess import preprocess
        from tokenizers import Tokenizer
        import torch
        from sys_request import run_raw_contract_request
        torch.set_num_threads(4)
        wait_original=base.wait_transaction
        def observed_wait(kernel,dma,timeout):
            before=time.perf_counter_ns()
            try:
                evidence=wait_original(kernel,dma,timeout)
            except Exception:
                result['failed_transaction']=dict(current=current.copy(),snapshot=base.transaction_snapshot(kernel,dma))
                raise
            transactions.append(dict(current=current.copy(),elapsed_ns=time.perf_counter_ns()-before,
                ap_return=int(evidence['ap_return']),ap_ctrl=int(evidence['ap_ctrl']),
                mm2s_dmasr=int(evidence['mm2s_dmasr']),s2mm_dmasr=int(evidence['s2mm_dmasr'])))
            return evidence
        base.wait_transaction=observed_wait
        class ObservedRuntime(M238PrefillRuntime):
            def _program_static_registers(self,chain,buffers):
                current.clear();current.update(chain_index=chain['chain_index'],layer=chain.get('layer'),
                    family=chain.get('family','lm_head'),input_bytes=chain['input_bytes'],output_bytes=chain['output_bytes'])
                return super()._program_static_registers(chain,buffers)
        phase[0]='load model and stable runtime'
        board=ObservedRuntime.__new__(ObservedRuntime)
        board.__init__(STABLE/'overlay/m120_m89x2_t32.bit',
            ROOT/'m120_fulltext_weights_0x4D395832/language_fourport',
            ROOT/'m120_fulltext_weights_0x4D395832/lmhead_fourport',
            STABLE/'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json',
            STABLE/'contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json',weight_mode='staged-low-cma')
        result['overlay_loads']=1
        model=M241VideoLanguageModel(board,ROOT/'m181_m120_video_board_candidate/text_auxiliary')
        package=ROOT/'m181_m120_video_board_candidate'
        vision=M222PSVisionRuntime(package/'ps_vision_payload',package/'vision_layout',
            package/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
        tokenizer=Tokenizer.from_file(str(package/'text_auxiliary/tokenizer.json'))
        result['runtime_loads']=1
        result['load_s']=time.perf_counter()-started
        result['resources_hot']=resources()
        phase[0]='SYS raw-video, vision, prefill and causal decode'
        request=run_raw_contract_request(video_path=BASE/'OP00-import-decode-01/dev-0001.mp4',
            video_sha256=config['video_sha256'],question=config['question'],vision=vision,model=model,
            tokenizer=tokenizer,preprocess=preprocess,board=board,max_new_tokens=args.max_new_tokens,
            cpu_linear_fallback=False,on_token=lambda token:print('OP01_TOKEN_READY id='+str(token),flush=True))
        result['request']=request
        result['board_evidence']=board.evidence()
        if request['status']!='PASS':raise RuntimeError('SYS request failed: '+str(request.get('error',request.get('generation',{}).get('errors'))))
        if len(transactions)!=board.host_calls or not transactions or any(t['ap_return']!=int('4D395832',16) for t in transactions):
            raise RuntimeError('Physical transaction count / actual Build mismatch')
        result.update(status='PROVISIONAL',build_id='0x4D395832',fpga_execution_verified=True)
        request['hardware_proof_verified']=True
        # The stable source route delegates every language Linear and LM Head;
        # PS vision remains explicitly CPU. Numeric/semantic acceptance is separate.
        result['fallback_scope']='Language Linear/LM Head only; vision intentionally PS'
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        stop.set()
        if board is not None:
            import board_runtime as base
            cleanup=guarded_close_board(board,base.transaction_snapshot,bool(current))
            result['cleanup']=cleanup;unsafe=cleanup['recovery_required']
            if hasattr(board,'overlay'):result['overlay_loads']=1
            if unsafe or cleanup['errors']:
                result.update(status='FAIL',recovery_required=unsafe)
                result['errors'].extend(cleanup['errors'])
        for name,obj in (('model',model),('vision',vision)):
            if obj is not None:
                try:obj.close()
                except Exception as exc:
                    result['status']='FAIL';result['errors'].append(name+' close: '+repr(exc))
        if wait_original is not None:base.wait_transaction=wait_original
        result['resources_after']=resources()
        result['transactions']=transactions
        result['elapsed_s']=time.perf_counter()-started
        result['boot_unchanged']=result.get('boot_sha256_before')==sha256('/boot/firmware/boot.scr.uimg')
        result['cmdline_unchanged']=result.get('cmdline_before')==Path('/proc/cmdline').read_text()
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:
            result['status']='FAIL';result['errors'].append('Boot/cmdline mismatch')
        write_json(args.result,result)
        # Large per-transaction evidence remains in file; UART compact summary plus
        # hash is not a substitute for collecting the full result before acceptance.
        summary=compact_summary(result)
        summary.update(full_result_path=str(args.result),full_result_sha256=sha256(args.result),
            physical_transaction_count=len(transactions),board_evidence_summary={k:result.get('board_evidence',{}).get(k)
            for k in ('host_calls','logical_calls','scale_retry_count','stage_ms','stage_bytes')})
        print('OP01_SYS_JSON_BEGIN',flush=True);print(json.dumps(summary,allow_nan=False),flush=True);print('OP01_SYS_JSON_END',flush=True)
        if unsafe:
            while True:
                print('OP01_UNSAFE_DMA_HOLD no buffers released; operator recovery required',flush=True)
                time.sleep(30)
        if fd is not None:os.close(fd)
    return 0 if result['status']=='PROVISIONAL' else 1


if __name__=='__main__':raise SystemExit(main())
