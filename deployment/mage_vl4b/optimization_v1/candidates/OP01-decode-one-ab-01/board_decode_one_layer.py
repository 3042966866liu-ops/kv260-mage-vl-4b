"""One real layer from KV852, isolated stable/candidate processes, exact outputs."""
import argparse
import hashlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from measurement import sha256, write_json
from op01_support import verify_package, guarded_close_board
from op00_stable_probe import service_stopped, STABLE, STABLE_SHA
from decode_one_board_transaction import BoardTransaction
from decode_one_board_protocol import zero_transaction, STABLE_BUILD
from m120_board_common import snapshot, KERNEL_NAME, DMA_NAME

ROOT = STABLE.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--result', required=True, type=Path)
    parser.add_argument('--mode', required=True, choices=('stable','candidate'))
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--reference-sha256')
    parser.add_argument('--imports-only', action='store_true')
    parser.add_argument('--full-decode', action='store_true')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    verify_package(here, args.manifest_sha256)
    if args.result.exists() or args.result.resolve().is_relative_to(here):
        raise ValueError('Result must be new and outside package')
    result = dict(status='FAIL', scope='Real layer0 only; not full Decode performance', mode=args.mode,
        build_id='0x4F503131' if args.mode=='candidate' else '0x4D395832',
        errors=[], transactions=[], overlay_loads=0, stable_restored=False, performance_pass=False,
        capacity_status='STOPPED_BY_USER_NOT_PASS', formal_promotion_allowed=False)
    if args.full_decode:
        result['scope']='One complete incremental Decode, controlled two-scan preparation; not formal throughput'
    lock = board = model = restore_tx = None
    loaded = launched = unsafe = False
    phase=['imports']; stop=threading.Event()
    def heartbeat():
        while not stop.wait(30): print('LAYER_HEARTBEAT '+phase[0], flush=True)
    threading.Thread(target=heartbeat,daemon=True).start()
    try:
        config=json.loads((here/'sys_config.json').read_text())
        plan=json.loads((here/'checkpoint_plan.json').read_text())
        for name, digest in config['package_manifest_hashes'].items():
            manifest=ROOT/name/'PACKAGE_MANIFEST.json'
            if sha256(manifest)!=digest: raise ValueError('Predecessor manifest changed: '+name)
            for row in json.loads(manifest.read_text())['files']:
                if Path(row['path']).suffix in ('.py','.sh','.json') and sha256(ROOT/name/row['path'])!=row['sha256']:
                    raise ValueError('Predecessor source changed: '+row['path'])
        sys.path[1:1]=[str(ROOT/p) for p in config['python_path']]
        # Derived module lives only in this process; stable module/files are untouched.
        module_path=here/('candidate_base.py' if args.mode=='candidate' else 'stable_base.py')
        spec=importlib.util.spec_from_file_location('board_runtime',module_path)
        base=importlib.util.module_from_spec(spec);sys.modules['board_runtime']=base;spec.loader.exec_module(base)
        import numpy as np
        from m238_prefill_runtime import M238PrefillRuntime
        from m241_video_language_runtime import M241VideoLanguageModel
        from video_language_runtime import KVCache
        from decode_checkpoint import load_checkpoint
        from decode_one_layer_probe import bind_layer_zero
        from decode_one_runtime_adapter import runtime_class
        if args.full_decode:
            from decode_diagnostic import DecodeDiagnostic
            from decode_io_trace import DecodeIOTrace, process_snapshot
            from lifecycle_reads import prepare_reads
            from summarize_decode_trace import summarize
            from transfer_trace import instrument
            instrument(base.copy_window_to_buffer, DecodeIOTrace())
        cls=runtime_class(M238PrefillRuntime,base) if args.mode=='candidate' else M238PrefillRuntime
        if base.BUILD_ID != int(result['build_id'],16): raise ValueError('Loaded runtime Build-ID mismatch')
        phase[0]='restore KV852'
        token,cache=load_checkpoint(ROOT/'optimization_v1/decode_checkpoints/SYS05-prefill',
            plan['checkpoint_manifest_sha256'],plan['identity'],KVCache)
        if token!=1291 or any(a.shape!=(852,8,128) for a in cache.keys+cache.values):
            raise ValueError('Checkpoint token/geometry mismatch')
        result.update(input_token=token, checkpoint_sha256=plan['checkpoint_manifest_sha256'],cache_before=852)
        reference=None
        if args.mode=='candidate' and not args.imports_only:
            if not args.reference or not args.reference_sha256 or sha256(args.reference)!=args.reference_sha256:
                raise ValueError('Exact stable reference required')
            reference=json.loads(args.reference.read_text())
            reference_status='PASS_STABLE_DECODE_REFERENCE' if args.full_decode else 'PASS_STABLE_LAYER_REFERENCE'
            if reference['status']!=reference_status or reference['checkpoint_sha256']!=result['checkpoint_sha256']:
                raise ValueError('Stable layer reference invalid')
            for row in reference['outputs']:
                path=args.reference.parent/row['path']
                if sha256(path)!=row['sha256']: raise ValueError('Reference tensor changed')
        if args.imports_only:
            result['status']='PASS_IMPORT_CHECKPOINT_ONLY'
        else:
            if os.geteuid()!=0: raise RuntimeError('Root required')
            lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result['service']=service_stopped()
            result['boot_before']=sha256('/boot/firmware/boot.scr.uimg')
            result['cmdline_before']=Path('/proc/cmdline').read_text()
            phase[0]='environment preflight'
            for label,script,package,digest in (
                ('stable','m120_board_env_preflight.py',STABLE,STABLE_SHA),
                ('candidate','decode_one_env_preflight.py',here,args.manifest_sha256)):
                dest=args.result.with_name(args.result.stem+'_'+label+'_environment.json')
                run=subprocess.run([sys.executable,'-B',str(here/script),'--candidate',str(package),
                    '--expected-package-manifest-sha256',digest,'--result',str(dest)],timeout=90)
                if run.returncode: raise RuntimeError(label+' preflight failed')
            current={}
            original_wait=base.wait_transaction
            def observed_wait(kernel,dma,timeout):
                start=time.monotonic()
                try: proof=original_wait(kernel,dma,timeout)
                except Exception:
                    result['failed_transaction']=dict(identity=current.copy(),snapshot=base.transaction_snapshot(kernel,dma));raise
                result['transactions'].append(dict(identity=current.copy(),wait_s=time.monotonic()-start,snapshot=proof))
                return proof
            base.wait_transaction=observed_wait
            class Observed(cls):
                def _program_static_registers(self,chain,buffers):
                    nonlocal launched
                    launched=True
                    current.update(layer=chain.get('layer'),family=chain.get('family'),chain_index=chain['chain_index'])
                    return super()._program_static_registers(chain,buffers)
            phase[0]='runtime initialization, outside layer timing'
            bit=here/'overlay/op01_decode_one.bit' if args.mode=='candidate' else STABLE/'overlay/m120_m89x2_t32.bit'
            board=Observed.__new__(Observed);loaded=True
            board.__init__(bit,ROOT/'m120_fulltext_weights_0x4D395832/language_fourport',
                ROOT/'m120_fulltext_weights_0x4D395832/lmhead_fourport',
                STABLE/'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json',
                STABLE/'contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json',weight_mode='staged-low-cma')
            result['overlay_loads']+=1
            model=M241VideoLanguageModel(board,ROOT/'m181_m120_video_board_candidate/text_auxiliary')
            if args.full_decode:
                phase[0]='two verified weight scans, outside Decode timing'
                reads=json.loads((here/'lifecycle_read_plan.json').read_text())
                result['read_preparation']=prepare_reads(reads,snapshot=process_snapshot,
                    progress=lambda message: print(message,flush=True))
                diagnostic=DecodeDiagnostic(model,board,base,trace_factory=DecodeIOTrace)
                result['io_before']=process_snapshot()
                phase[0]='complete one-token Decode'
                start=time.monotonic();output_token,logits=diagnostic.decode(token,cache)
                result['decode_seconds']=time.monotonic()-start
                result['io_after']=process_snapshot()
                print('DECODE_TOKEN_READY '+str(output_token),flush=True)
                phase[0]='post-timing attribution and comparison'
                detail=diagnostic.finalize()
                result['diagnostic']=detail; result['attribution']=summarize(detail['steps'][0])
                result['output_token']=int(output_token)
                if int(output_token)!=311:raise RuntimeError('Fixed-checkpoint output token changed')
                outputs={'logits':logits}
                result['kv_sha256']=[hashlib.sha256(a.tobytes()).hexdigest() for a in cache.keys+cache.values]
                if reference and (result['kv_sha256']!=reference['kv_sha256'] or result['output_token']!=reference['output_token']):
                    raise RuntimeError('Complete KV/token mismatch')
            else:
                layer=bind_layer_zero(model)
                phase[0]='real layer0'
                start=time.monotonic();hidden,cache=layer(token,cache);result['layer_seconds']=time.monotonic()-start
                outputs={'hidden':hidden,'key':cache.keys[0],'value':cache.values[0]}
            result['board_evidence']=board.evidence()
            if board.logical_calls!=(162 if args.full_decode else 5) or any(t['snapshot']['ap_return']!=base.BUILD_ID for t in result['transactions']):
                raise RuntimeError('Layer0 physical/logical call identity mismatch')
            expected_lengths=[853]*36 if args.full_decode else [853]+[852]*35
            if [a.shape[0] for a in cache.keys]!=expected_lengths or [a.shape[0] for a in cache.values]!=expected_lengths:
                raise RuntimeError('Layer0 KV increment mismatch')
            result['outputs']=[];result['comparisons']={}
            phase[0]='post-timing complete tensor comparison/persistence'
            output_dir=args.result.with_suffix('.arrays');output_dir.mkdir(exist_ok=False)
            for name,array in outputs.items():
                if not np.isfinite(array).all(): raise RuntimeError('Non-finite output')
                path=output_dir/(name+'.npy')
                with path.open('xb') as stream:np.save(stream,array,allow_pickle=False)
                result['outputs'].append(dict(name=name,path=str(path.relative_to(args.result.parent)),sha256=sha256(path),shape=list(array.shape)))
                if reference:
                    row=next(x for x in reference['outputs'] if x['name']==name)
                    expected=np.load(args.reference.parent/row['path'],allow_pickle=False)
                    equal=expected.shape==array.shape and expected.dtype==array.dtype and expected.tobytes()==array.tobytes()
                    result['comparisons'][name]=dict(bit_exact=equal)
                    if not equal: raise RuntimeError('Full tensor mismatch: '+name)
            result['status']='PASS_CANDIDATE_LAYER_EXACT' if reference else 'PASS_STABLE_LAYER_REFERENCE'
            if args.full_decode:
                result['status']='PASS_CANDIDATE_DECODE_EXACT' if reference else 'PASS_STABLE_DECODE_REFERENCE'
    except Exception as exc:
        import traceback
        result['errors'].append(repr(exc));result['traceback']=traceback.format_exc();result['failed_phase']=phase[0]
    finally:
        if board is not None:
            cleanup=guarded_close_board(board,base.transaction_snapshot,launched)
            result['cleanup']=cleanup;unsafe=cleanup['recovery_required']
            if unsafe or cleanup['errors']:result['status']='FAIL';result['errors'].extend(cleanup['errors'])
        if model is not None:
            try:model.close()
            except Exception as exc:
                result['status']='FAIL';result['errors'].append('model close: '+repr(exc))
        if loaded and not unsafe:
            try:
                from pynq import Overlay,allocate
                restored=Overlay(str(STABLE/'overlay/m120_m89x2_t32.bit'),download=True)
                kernel,dma=getattr(restored,KERNEL_NAME),getattr(restored,DMA_NAME)
                restore_tx=BoardTransaction(kernel,dma,allocate,lambda:snapshot(kernel,dma))
                result['restore']=restore_tx.run(zero_transaction(build_id=STABLE_BUILD),'stable-restored-zero')
                result['stable_restored']=True
            except Exception as exc:
                result['status']='FAIL';result['errors'].append('restore: '+repr(exc))
                unsafe=restore_tx is not None and restore_tx.recovery_required
        if 'boot_before' in result:
            result['boot_unchanged']=sha256('/boot/firmware/boot.scr.uimg')==result['boot_before']
            result['cmdline_unchanged']=Path('/proc/cmdline').read_text()==result['cmdline_before']
            if not result['boot_unchanged'] or not result['cmdline_unchanged']:result['status']='FAIL'
        result['recovery_required']=unsafe or (loaded and not result['stable_restored'])
        write_json(args.result,result)
        summary={k:v for k,v in result.items() if k not in ('transactions','board_evidence','boot_before','cmdline_before','diagnostic')}
        if args.full_decode and 'attribution' in summary:
            summary['attribution']={k:v for k,v in result['attribution'].items() if k!='families'}
        summary['result_sha256']=sha256(args.result)
        print('LAYER_JSON_BEGIN\n'+json.dumps(summary)+'\nLAYER_JSON_END',flush=True)
        stop.set()
        if unsafe:
            while True:print('LAYER_UNSAFE_DMA_HOLD_DO_NOT_KILL',flush=True);time.sleep(30)
        if lock is not None:os.close(lock)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
