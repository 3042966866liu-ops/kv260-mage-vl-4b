"""Ordered real-descriptor then double-bank chain gates; no E2E/speed claim."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace
sys.dont_write_bytecode=True
import numpy as np
from board_safety import safe_to_release
from measurement import sha256, write_json
from m341_build_id_gate import verify_self, service_stopped, STABLE, STABLE_SHA
from m120_board_common import (BUILD_ID,KERNEL_NAME,DMA_NAME,REG_POINTERS,REG_CONFIG,REG_AP_CTRL,
                              physical_address,write_u64,wait_transaction,snapshot)
from m120_fixture import load_fixture,build_case
from weight_prefetch import WeightPrefetchSession,RetainedBuffersError
HERE=Path(__file__).resolve().parent
EVIDENCE=Path('/home/ubuntu/m342_prefetch_fixture_evidence_01')
FIXTURE=Path('/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate/reference/m128_m120_real_record_csim_fixture.bin')


def digest_bytes(data):return hashlib.sha256(data).hexdigest()


def canonicalize(value):
    # Exact existing M157 rule; only FP16 subnormal lanes become signed zero.
    words=np.frombuffer(value,dtype=np.uint8).copy().reshape(-1,8)
    count=0
    for start in (0,4):
        bits=words[:,start:start+2].copy().view('<u2').reshape(-1)
        selected=((bits&np.uint16(0x7C00))==0)&((bits&np.uint16(0x03FF))!=0)
        count+=int(np.count_nonzero(selected));bits[selected]&=np.uint16(0x8000)
        words[:,start:start+2]=bits.view(np.uint8).reshape(-1,2)
    return words.tobytes(),count


def cma_free():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('CmaFree:'):return int(line.split()[1])*1024
    raise RuntimeError('CmaFree unavailable')


def main():
    p=argparse.ArgumentParser();p.add_argument('level',choices=('single-descriptor','single-chain'))
    p.add_argument('manifest_sha');p.add_argument('--previous-sha');a=p.parse_args()
    path=EVIDENCE/(a.level+'.json')
    if path.exists():raise RuntimeError('Immutable gate evidence exists')
    result=dict(status='FAIL',gate_level=a.level,build_id='0x4D395832',performance_pass=False,
                prefetch_candidate_executed=False,model_math_changed=False,transactions=[],errors=[],overlay_loaded=False)
    buffers=[];kernel=dma=session=lock=None;transaction_started=False;unsafe=False
    started=time.monotonic()
    try:
        verify_self(HERE,a.manifest_sha)
        previous=HERE/'BUILD_ID_PREREQUISITE.json'
        prior=json.loads(previous.read_text(encoding='utf-8'))
        if prior['status']!='PASS' or prior['build_id']!='0x4D395832' or prior['unsafe_dma_buffers_retained']:
            raise RuntimeError('Build-ID prerequisite rejected')
        result['build_id_prerequisite_sha256']=sha256(previous)
        if a.level=='single-chain':
            prerequisite=EVIDENCE/'single-descriptor.json'
            if not a.previous_sha or sha256(prerequisite)!=a.previous_sha:raise RuntimeError('Exact descriptor prerequisite required')
            descriptor=json.loads(prerequisite.read_text(encoding='utf-8'))
            if descriptor['status']!='PASS' or descriptor['gate_level']!='single-descriptor':raise RuntimeError('Descriptor gate not PASS')
            result['descriptor_prerequisite_sha256']=a.previous_sha
        if os.geteuid()!=0:raise RuntimeError('Root required')
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result['initial_service']=service_stopped()
        boot=Path('/boot/firmware/boot.scr.uimg');result['boot_sha256_before']=sha256(boot)
        result['cmdline_before']=Path('/proc/cmdline').read_text()
        closure=json.loads((HERE/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
        if closure['status']!='PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED':raise RuntimeError('Hardware closure rejected')
        if sha256(FIXTURE)!='f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9':raise RuntimeError('Fixture identity mismatch')
        result['fixture_sha256']=sha256(FIXTURE)
        policy=json.loads((HERE/'M157_FTZ_POLICY.json').read_text(encoding='utf-8'))
        contract=policy['contracts'][a.level]
        built=build_case(load_fixture(FIXTURE)[0],int(contract['descriptor_count']))
        expected,subnormals=canonicalize(built['expected'])
        if digest_bytes(built['expected'])!=contract['original_sha256'] or digest_bytes(expected)!=contract['canonical_sha256'] or subnormals!=contract['canonicalized_subnormal_count']:
            raise RuntimeError('Independent golden or frozen FTZ rule differs')
        envpath=EVIDENCE/(a.level+'-environment.json')
        env=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(STABLE),
            '--expected-package-manifest-sha256',STABLE_SHA,'--result',str(envpath)],timeout=90)
        if env.returncode:raise RuntimeError('Fixed environment preflight rejected')
        result['environment']=json.loads(envpath.read_text());result['environment_sha256']=sha256(envpath)
        # Import only the verified installed copy implementation, never runtime init.
        sys.path.insert(0,str(STABLE/'runtime'))
        import board_runtime as original
        if sha256(Path(original.__file__))!='5d53ea406e57de88f8c14d9bc4e1cb0c0049ff0b8f4bcf620e05745fcd82b201':raise RuntimeError('Stable runtime source differs')
        from pynq import Overlay,allocate
        overlay=Overlay(str(STABLE/'overlay/m120_m89x2_t32.bit'),download=True)
        result['overlay_loaded']=True
        kernel,dma=getattr(overlay,KERNEL_NAME),getattr(overlay,DMA_NAME)
        maximum=6963200 if a.level=='single-chain' else len(built['weights'][0])
        for size in [maximum]*4+[len(built['packet']),built['output_bytes']]:
            buffers.append(allocate((size,),dtype=np.uint8))
            if physical_address(buffers[-1])+size>original.LOW_END:raise RuntimeError('DMA buffer outside low DDR')
        bank,input_buffer,output_buffer=buffers[:4],buffers[4],buffers[5]
        for source,buffer in zip(built['weights'],bank):
            buffer[:len(source)]=np.frombuffer(source,np.uint8);buffer.sync_to_device()
        input_buffer[:]=np.frombuffer(built['packet'],np.uint8);input_buffer.sync_to_device()
        def execute(weights,identity):
            nonlocal transaction_started
            for offset,buffer in zip(REG_POINTERS,weights):write_u64(kernel,offset,physical_address(buffer))
            kernel.write(REG_CONFIG,built['config'])
            transaction_started=True
            dma.recvchannel.transfer(output_buffer,nbytes=built['output_bytes'])
            kernel.write(REG_AP_CTRL,1)
            dma.sendchannel.transfer(input_buffer,nbytes=len(built['packet']))
            proof=wait_transaction(kernel,dma,10.0,identity,len(built['packet']),built['output_bytes'])
            output_buffer.sync_from_device()
            raw=bytes(memoryview(output_buffer)[:built['output_bytes']])
            released=snapshot(kernel,dma)
            row=dict(identity=identity,chain_identity=built['identity'],input_bytes=len(built['packet']),output_bytes=built['output_bytes'],
                output_sha256=digest_bytes(raw),expected_sha256=digest_bytes(expected),exact=raw==expected,
                completion=proof,release_snapshot=released,bank_addresses=[physical_address(b) for b in weights])
            result['transactions'].append(row)
            if not safe_to_release(released):raise RetainedBuffersError('Unsafe transaction completion')
            transaction_started=False
            if raw!=expected:raise RuntimeError('Independent full-output mismatch')
        # Warm/prove the fresh DMA channels with a real golden transaction. Initial
        # DMASR=0 on a new overlay is deliberately NOT treated as an idle proof.
        execute(bank,'baseline-'+a.level)
        if a.level=='single-chain':
            root=EVIDENCE/'isolated-layout';root.mkdir(parents=True,exist_ok=False)
            count=int(contract['descriptor_count']);size=len(built['weights'][0]);plan=[];tiles=[]
            for i,source in enumerate(built['weights']):(root/f'weights{i}.bin').write_bytes(source*3)
            per_descriptor=size//count
            layout=SimpleNamespace(root=root,manifest=dict(files=[dict(path=f'weights{i}.bin') for i in range(4)],modules=[]))
            for position in range(3):
                descriptors=[]
                for d in range(count):
                    offset=position*size+d*per_descriptor;index=position*count+d
                    tiles.append(dict(tile_index=index,shard_offsets=[offset]*4,record_bytes_per_shard=per_descriptor))
                    descriptors.append(dict(module='fixture',tile_index=index,offset_words=offset//16))
                chain=dict(chain_index=position,groups=40,bits=2,descriptor_count=count,descriptors=descriptors)
                plan.append((layout,chain))
            layout.manifest['modules']=[dict(module='fixture',tiles=tiles)]
            runtime=SimpleNamespace(weight_mode='staged-low-cma',staged_buffers=bank,maximum_weight_window_bytes=maximum,
                allocate=allocate,kernel=kernel,dma=dma,stage_bytes=0,stage_ms=0.0,_stage=lambda *args:None)
            base=SimpleNamespace(LOW_END=original.LOW_END,physical_address=physical_address,chain_window=original.chain_window,
                transaction_snapshot=lambda *args:snapshot(kernel,dma),copy_window_to_buffer=original.copy_window_to_buffer)
            result['cma_free_after_base_allocations']=cma_free()
            session=WeightPrefetchSession(runtime,base,plan,cma_free_bytes=result['cma_free_after_base_allocations'])
            with session:
                result['prefetch_candidate_executed']=True
                result['cma_free_with_extra_bank']=cma_free()
                for position,item in enumerate(plan):
                    staged,words=runtime._stage(*item)
                    if words!=position*size//16:raise RuntimeError('Staged base mismatch')
                    hashes=[digest_bytes(bytes(memoryview(b)[:size])) for b in staged]
                    if hashes!=[digest_bytes(w) for w in built['weights']]:raise RuntimeError('Staged weight bytes differ')
                    execute(staged,'candidate-bank-'+str(position&1)+'-chain-'+str(position))
                result['stage_bytes']=runtime.stage_bytes
            result['prefetch']=session.record
            if session.record['stages']!=3 or result['stage_bytes']!=3*4*size:raise RuntimeError('Stage counts/bytes differ')
            addresses=[row['bank_addresses'] for row in result['transactions'][1:]]
            if addresses[0]!=addresses[2] or set(addresses[0])&set(addresses[1]):raise RuntimeError('Banks not distinct A-B-A')
        result['boot_unchanged']=sha256(boot)==result['boot_sha256_before']
        result['cmdline_unchanged']=Path('/proc/cmdline').read_text()==result['cmdline_before']
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected identities changed')
        result['status']='PASS'
    except BaseException as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}');result['traceback']=traceback.format_exc()
    finally:
        if kernel is not None and dma is not None:
            result['final_snapshot']=snapshot(kernel,dma)
            unsafe=transaction_started and not safe_to_release(result['final_snapshot'])
        if session is not None and not session.closed:
            try:session.close()
            except RetainedBuffersError:unsafe=True
            result['prefetch']=session.record
        result['unsafe_buffers_retained']=unsafe;result['elapsed_ms']=(time.monotonic()-started)*1000
        result['next_step']='Remain at failed level' if result['status']!='PASS' else ('single-chain' if a.level=='single-descriptor' else 'single-layer numerical gate; no full video/speed promotion')
        write_json(path,result);raw=path.read_bytes()
        print('M342_RESULT_SHA256='+digest_bytes(raw),flush=True)
        print('M342_RESULT_BASE64='+base64.b64encode(raw).decode(),flush=True)
        print('M342_RESULT_SUMMARY='+json.dumps(dict(status=result['status'],level=a.level,errors=result['errors'],transactions=len(result['transactions']),unsafe=unsafe)),flush=True)
        if unsafe:
            print('M342_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        for buffer in reversed(buffers):buffer.freebuffer()
        if lock is not None:os.close(lock)
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
