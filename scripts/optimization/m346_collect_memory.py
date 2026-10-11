"""Strict diagnostic chunk recovery and synchronized state; no hardware action."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[2]


def atomic(path,data):
    part=path.with_name(path.name+'.m346-part')
    with part.open('wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(part,path)


def decode(log):
    hashes=re.findall(r'M346_RESULT_SHA256=([0-9a-f]{64})',log)
    if len(hashes)!=1: raise RuntimeError('Missing/duplicate result SHA')
    expected=hashes[0]
    chunks=re.findall(r'M346_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',log)
    if not chunks or len(chunks)!=int(chunks[0][1]): raise RuntimeError('Incomplete chunks')
    raw=bytearray()
    for i,(index,count,encoded) in enumerate(chunks):
        if int(index)!=i or int(count)!=len(chunks): raise RuntimeError('Duplicate/unordered chunks')
        block=base64.b64decode(encoded,validate=True)
        if len(block)>1800: raise RuntimeError('Oversized chunk')
        raw.extend(block)
    raw=bytes(raw)
    if hashlib.sha256(raw).hexdigest()!=expected: raise RuntimeError('Exact-byte result hash mismatch')
    result=json.loads(raw)
    if result['gate_level']!='load-only-memory-diagnostic': raise RuntimeError('Wrong diagnostic')
    if result['status']=='PASS_LOAD_ONLY_DIAGNOSTIC':
        if ('M346_MEMORY_DONE gate_rc=0' not in log or result['errors'] or result['unsafe_buffers_retained'] or not result['safe_buffers_released']
            or result['host_calls']!=0 or result['logical_calls']!=0 or result['model_forward_calls']!=0 or result['blocked_inference_attempts']
            or result['numerical_pass'] or result['performance_pass'] or result['formal_promotion_allowed']):
            raise RuntimeError('Incomplete/unsafe/nonzero-transaction diagnostic PASS')
        expected_stages={'complete-runtime-loaded-retained','retained-runtime-after-PS-GC','retained-runtime-after-PS-glibc-trim',
            'retained-runtime-after-trim-plus-2s','retained-runtime-after-trim-plus-5s','after-safe-close-and-PS-object-disposal'}
        if not expected_stages.issubset({p['name'] for p in result['stages']}): raise RuntimeError('Missing memory observations')
    return expected,raw,result


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--self-test':
        sample=dict(status='PASS_LOAD_ONLY_DIAGNOSTIC',gate_level='load-only-memory-diagnostic',errors=[],unsafe_buffers_retained=False,safe_buffers_released=True,
            host_calls=0,logical_calls=0,model_forward_calls=0,blocked_inference_attempts=[],numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
            stages=[{'name':n} for n in ('complete-runtime-loaded-retained','retained-runtime-after-PS-GC','retained-runtime-after-PS-glibc-trim',
                'retained-runtime-after-trim-plus-2s','retained-runtime-after-trim-plus-5s','after-safe-close-and-PS-object-disposal')],chinese='内存诊断'*700)
        def log_for(value):
            raw=(json.dumps(value,ensure_ascii=False)+'\n').encode('utf-8'); digest=hashlib.sha256(raw).hexdigest()
            blocks=[raw[i:i+1800] for i in range(0,len(raw),1800)]
            return raw,'M346_RESULT_SHA256='+digest+'\n'+''.join('M346_RESULT_CHUNK='+str(i)+'/'+str(len(blocks))+':'+base64.b64encode(b).decode()+'\n' for i,b in enumerate(blocks))+'M346_MEMORY_DONE gate_rc=0\n'
        raw,log=log_for(sample); assert decode(log)[1]==raw
        bad_values=[]
        for key,value in [('host_calls',1),('model_forward_calls',1),('performance_pass',True),('safe_buffers_released',False)]:
            bad=dict(sample); bad[key]=value; bad_values.append(log_for(bad)[1])
        bad_values.extend([log.replace('gate_rc=0','gate_rc=1'),log.replace('M346_RESULT_CHUNK=1/','M346_RESULT_CHUNK=0/'),log+'M346_RESULT_SHA256='+'0'*64])
        for bad in bad_values:
            try: decode(bad)
            except RuntimeError: pass
            else: raise AssertionError('Invalid diagnostic accepted')
        print('M346_COLLECTOR_SELF_TEST_PASS UTF8/raw/hash/duplicate/exit/inference/promoted_rejections'); return
    expected,raw,result=decode((ROOT/'tmp/m346/load-memory_uart.log').read_text(encoding='utf-8-sig'))
    run=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M346-load-memory-board-01'; run.mkdir(parents=True,exist_ok=True)
    path=run/'BOARD_RESULT.json'
    if path.exists() and path.read_bytes()!=raw: raise RuntimeError('Different immutable result exists')
    atomic(path,raw)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        backup=run/(Path(name).name+'.before')
        if not backup.exists(): backup.write_bytes((ROOT/name).read_bytes())
    relative=path.relative_to(ROOT).as_posix(); board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board=json.loads(board_path.read_text(encoding='utf-8'))
    board['latest_m346_load_memory']=dict(status=result['status'],evidence_level='BOARD_LOAD_ONLY_DIAGNOSTIC_NOT_NUMERICAL',build_id=result['build_id'],result=relative,
        sha256=expected,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,unsafe_buffers_retained=result['unsafe_buffers_retained'],
        before_gc=result.get('load_only_eligibility_before_gc'),after_gc=result.get('load_only_eligibility_after_gc'),after_trim=result.get('load_only_eligibility_after_trim'))
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    summary={k:result.get(k) for k in ('status','errors','stages','gc_collected','trim','host_calls','logical_calls','model_forward_calls',
        'load_only_eligibility_before_gc','load_only_eligibility_after_gc','load_only_eligibility_after_trim','release_lifecycle','final_snapshot','safe_buffers_released','unsafe_buffers_retained','next_step')}
    summary['sha256']=expected; atomic(run/'SUMMARY.json',(json.dumps(summary,indent=2)+'\n').encode('utf-8'))
    note=('## M346 只加载内存诊断 '+result['status']+'（2026-10-01）\n\n'
        '稳定Build `0x4D395832`，冻结M345原视频源码/资产，加载原M276/M273/M238/M241完整对象；所有模型forward/Prefill/Decode/FPGA事务入口被拦截。'
        '只记录加载阶段PS RSS/CMA及保留runtime时GC/glibc空闲堆回收，完整结果 `'+relative+'` SHA `'+expected+'`。'
        '错误 `'+json.dumps(result['errors'],ensure_ascii=False)+'`；加载门槛观察 `'+json.dumps({k:summary[k] for k in ('load_only_eligibility_before_gc','load_only_eligibility_after_gc','load_only_eligibility_after_trim')})+'`。'
        '原90.5625MiB门槛/64MiB预留保持；仅load-only诊断，不能证明视觉前向后的CMA、完整视频数值、性能或晋级。'
        '清理使用确实未提交事务的生命周期证据，不能把新Overlay DMASR0当完成DMA空闲。稳定源/服务/回滚/boot/DTB/CMA配置未改，无drop_caches/模型forward/硬件门禁重跑。'
        '收集失败只修复回收。下一步 '+result['next_step']+'。\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        target=ROOT/name; content=target.read_text(encoding='utf-8')
        if expected not in content:
            heading,rest=content.split('\n',1); atomic(target,(heading+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    assert json.loads(board_path.read_text(encoding='utf-8'))['latest_m346_load_memory']['sha256']==expected
    assert all(expected in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    atomic(run/'REPORT.md',('# M346 只加载内存诊断\n\n'+note).encode('utf-8'))
    print(json.dumps(summary))


if __name__=='__main__': main()
