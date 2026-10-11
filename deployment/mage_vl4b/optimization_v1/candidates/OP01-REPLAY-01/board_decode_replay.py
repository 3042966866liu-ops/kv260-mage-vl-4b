"""One real checkpoint Decode on retained hardware; diagnostic, not promotion."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import threading
import time
from measurement import sha256,write_json
from op01_support import verify_package,guarded_close_board

ROOT=Path('/home/ubuntu/tellme_m120_m89x2_20260901')
STABLE=ROOT/'m175_m120_fixed_text_candidate'


def memory():
    return dict(peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                meminfo=Path('/proc/meminfo').read_text(),status=Path('/proc/self/status').read_text())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--result',type=Path,required=True);parser.add_argument('--imports-only',action='store_true')
    args=parser.parse_args();here=Path(__file__).resolve().parent
    verify_package(here,args.manifest_sha256)
    if args.result.exists():raise RuntimeError('Immutable result exists')
    config=json.loads((here/'sys_config.json').read_text());plan=json.loads((here/'checkpoint_plan.json').read_text())
    result=dict(status='FAIL',scope='Checkpoint language-only diagnostic; vision allocations absent; no performance or numerical acceptance',
        package_manifest_sha256=args.manifest_sha256,timing_eligible=False,numerical_acceptance=False,
        errors=[],model_executed=False,overlay_loads=0)
    board=model=None;fd=None;original_wait=None;current={};transactions=[];unsafe=False
    stop=threading.Event();started=time.perf_counter();phase=['imports']
    def heartbeat():
        while not stop.wait(30):print('REPLAY_HEARTBEAT '+json.dumps(dict(phase=phase[0],current=current,
            physical_calls=len(transactions),elapsed_s=time.perf_counter()-started)),flush=True)
    threading.Thread(target=heartbeat,daemon=True).start()
    try:
        result['boot_before']=sha256('/boot/firmware/boot.scr.uimg');result['cmdline_before']=Path('/proc/cmdline').read_text()
        for name,expected in config['package_manifest_hashes'].items():
            manifest=ROOT/name/'PACKAGE_MANIFEST.json'
            if sha256(manifest)!=expected:raise RuntimeError('Base manifest changed: '+name)
            for row in json.loads(manifest.read_text())['files']:
                if Path(row['path']).suffix in ('.py','.sh','.json') and sha256(ROOT/name/row['path'])!=row['sha256']:
                    raise RuntimeError('Base executable/config changed: '+row['path'])
        sys.path[1:1]=[str(ROOT/p) for p in config['python_path']]
        import numpy as np
        import board_runtime as base
        from m238_prefill_runtime import M238PrefillRuntime
        from m241_video_language_runtime import M241VideoLanguageModel
        from video_language_runtime import KVCache
        from decode_checkpoint import load_checkpoint
        from decode_diagnostic import DecodeDiagnostic
        from decode_io_trace import DecodeIOTrace,process_snapshot
        from transfer_trace import instrument
        from op00_stable_probe import service_stopped
        from summarize_decode_trace import summarize
        instrument(base.copy_window_to_buffer,DecodeIOTrace())
        if not callable(getattr(M241VideoLanguageModel,'decode',None)):raise RuntimeError('Decode interface')
        snapshot=process_snapshot()
        if 'read_bytes' not in snapshot or 'rchar' not in snapshot:raise RuntimeError('I/O interface')
        phase[0]='restore verified real KV'
        token,cache=load_checkpoint(ROOT/'optimization_v1/decode_checkpoints/SYS05-prefill',
            plan['checkpoint_manifest_sha256'],plan['identity'],KVCache)
        if token!=1291 or len(cache.keys)!=36 or any(a.shape!=(852,8,128) for a in cache.keys+cache.values):
            raise RuntimeError('Real checkpoint identity/shape')
        result.update(checkpoint_sha256=plan['checkpoint_manifest_sha256'],input_token=token,cache_before=852,
            memory_after_restore=memory())
        if args.imports_only:
            result.update(status='PASS_IMPORT_RESTORE_ONLY',overlay_loads=0)
        else:
            if os.geteuid()!=0:raise RuntimeError('Root authorization required before overlay')
            fd=os.open('/tmp/tellme_kv260_execution.lock',os.O_RDWR|os.O_CREAT,0o600)
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result['service_before']=service_stopped()
            phase[0]='fixed environment preflight'
            env_path=args.result.with_name(args.result.stem+'_environment.json')
            preflight=subprocess.run([sys.executable,str(STABLE/'runtime/m120_board_env_preflight.py'),
                '--candidate',str(STABLE),'--expected-package-manifest-sha256',config['package_manifest_hashes'][STABLE.name],
                '--result',str(env_path)],timeout=90)
            if preflight.returncode:raise RuntimeError('Environment preflight failed')
            result['environment']=json.loads(env_path.read_text())
            original_wait=base.wait_transaction
            def observed_wait(kernel,dma,timeout):
                start=time.perf_counter_ns()
                try:evidence=original_wait(kernel,dma,timeout)
                except Exception:
                    result['failed_transaction']=dict(current=current.copy(),snapshot=base.transaction_snapshot(kernel,dma));raise
                transactions.append(dict(current=current.copy(),elapsed_ns=time.perf_counter_ns()-start,
                    ap_return=int(evidence['ap_return']),ap_ctrl=int(evidence['ap_ctrl']),
                    mm2s_dmasr=int(evidence['mm2s_dmasr']),s2mm_dmasr=int(evidence['s2mm_dmasr'])))
                return evidence
            base.wait_transaction=observed_wait
            class ObservedRuntime(M238PrefillRuntime):
                def _program_static_registers(self,chain,buffers):
                    current.clear();current.update(chain_index=chain['chain_index'],layer=chain.get('layer'),family=chain.get('family','lm_head'))
                    return super()._program_static_registers(chain,buffers)
            phase[0]='load stable language runtime only'
            board=ObservedRuntime.__new__(ObservedRuntime)
            board.__init__(STABLE/'overlay/m120_m89x2_t32.bit',
                ROOT/'m120_fulltext_weights_0x4D395832/language_fourport',ROOT/'m120_fulltext_weights_0x4D395832/lmhead_fourport',
                STABLE/'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json',STABLE/'contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json',weight_mode='staged-low-cma')
            result['overlay_loads']=1
            model=M241VideoLanguageModel(board,ROOT/'m181_m120_video_board_candidate/text_auxiliary')
            captures={};original_family=model._family
            def capture_family(layer,family,values):
                selected=layer==0 and family=='gate_up'
                if selected:
                    if captures:raise RuntimeError('Repeated capture')
                    captures['input']=np.asarray(values).copy()
                output=original_family(layer,family,values)
                if selected:
                    for name,value in output.items():captures[name]=np.asarray(value).copy()
                return output
            model._family=capture_family
            diagnostic=DecodeDiagnostic(model,board,base,trace_factory=DecodeIOTrace)
            result['memory_before_decode']=memory();phase[0]='one real incremental Decode'
            result['model_executed']=True
            start=time.perf_counter_ns();output_token,logits=diagnostic.decode(token,cache)
            result['outer_decode_s']=(time.perf_counter_ns()-start)/1e9
            print('REPLAY_TOKEN_READY '+str(output_token),flush=True)
            result['memory_after_decode']=memory();phase[0]='post-token trace/capture persistence'
            detail=diagnostic.finalize();result['diagnostic']=detail
            result['attribution']=summarize(detail['steps'][0])
            result['board_evidence']=board.evidence()
            if len(transactions)!=board.host_calls or any(int(t['ap_return'])!=0x4D395832 for t in transactions):
                raise RuntimeError('Physical identity/calls')
            if board.logical_calls!=162 or not np.isfinite(logits).all() or len(captures)!=3:
                raise RuntimeError('Decode plan/output/capture incomplete')
            capture_root=args.result.with_suffix('.captures');capture_root.mkdir(exist_ok=False)
            captures['decode_logits']=logits;members=[]
            for i,(name,array) in enumerate(captures.items()):
                if not np.isfinite(array).all() or array.nbytes>1024*1024:raise RuntimeError('Capture finite/size bound')
                path=capture_root/f'array{i:02d}.npy'
                with path.open('xb') as stream:np.save(stream,array,allow_pickle=False)
                members.append(dict(name=name,file=path.name,shape=list(array.shape),dtype=str(array.dtype),sha256=sha256(path)))
            write_json(capture_root/'manifest.json',dict(checkpoint_sha256=plan['checkpoint_manifest_sha256'],input_token=token,
                package_manifest_sha256=args.manifest_sha256,files=members,numerical_acceptance=False))
            result.update(status='MEASURED',model_executed=True,output_token=int(output_token),cache_after=853,
                captures=members,capture_manifest_sha256=sha256(capture_root/'manifest.json'),build_id='0x4D395832')
    except Exception as exc:
        import traceback
        result['errors'].append(repr(exc));result['traceback']=traceback.format_exc();result['failed_phase']=phase[0]
    finally:
        stop.set()
        if board is not None:
            cleanup=guarded_close_board(board,base.transaction_snapshot,bool(current));result['cleanup']=cleanup
            unsafe=cleanup['recovery_required']
            if unsafe or cleanup['errors']:result['status']='FAIL';result['errors'].extend(cleanup['errors'])
        if model is not None:
            try:model.close()
            except Exception as exc:result['status']='FAIL';result['errors'].append(repr(exc))
        if original_wait is not None:base.wait_transaction=original_wait
        result['transactions']=transactions;result['elapsed_s']=time.perf_counter()-started
        result['boot_unchanged']=result.get('boot_before')==sha256('/boot/firmware/boot.scr.uimg')
        result['cmdline_unchanged']=result.get('cmdline_before')==Path('/proc/cmdline').read_text()
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:result['status']='FAIL'
        write_json(args.result,result)
        summary={k:result.get(k) for k in ('status','scope','errors','build_id','package_manifest_sha256','input_token','output_token','outer_decode_s','cache_before','cache_after','overlay_loads','cleanup','failed_phase')}
        summary['full_result_sha256']=sha256(args.result)
        print('REPLAY_JSON_BEGIN');print(json.dumps(summary));print('REPLAY_JSON_END',flush=True)
        if unsafe:
            while True:print('REPLAY_UNSAFE_DMA_HOLD',flush=True);time.sleep(30)
        if fd is not None:os.close(fd)
    return 0 if result['status'] in ('MEASURED','PASS_IMPORT_RESTORE_ONLY') else 1

if __name__=='__main__':raise SystemExit(main())
