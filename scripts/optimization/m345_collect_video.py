"""Exact-byte bounded video result recovery; synchronize all three records."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[2]


def atomic(path,data):
    part=path.with_name(path.name+'.m345-part')
    with part.open('wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(part,path)


def decode(log):
    hashes=re.findall(r'M345_RESULT_SHA256=([0-9a-f]{64})',log)
    if len(hashes)!=1: raise RuntimeError('Missing/duplicate result identity')
    expected=hashes[0]
    chunks=re.findall(r'M345_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',log)
    if not chunks or len(chunks)!=int(chunks[0][1]): raise RuntimeError('Missing result chunk')
    data=bytearray()
    for index,(observed,count,encoded) in enumerate(chunks):
        if int(observed)!=index or int(count)!=len(chunks): raise RuntimeError('Wrong/duplicate chunk order')
        chunk=base64.b64decode(encoded,validate=True)
        if len(chunk)>1800: raise RuntimeError('Oversized result chunk')
        data.extend(chunk)
    data=bytes(data)
    if hashlib.sha256(data).hexdigest()!=expected: raise RuntimeError('Board raw result hash mismatch')
    result=json.loads(data)
    if result['gate_level']!='fixed159-video-E2E': raise RuntimeError('Wrong gate level')
    if result['status']=='PASS' and ('M345_VIDEO_DONE gate_rc=0' not in log or result['errors'] or result['unsafe_buffers_retained']
        or not result['safe_buffers_released'] or not all(result['exact_comparison'].values())
        or not all(result[k] for k in ('direct_bitwise_video_hidden_equal','direct_bitwise_logits_equal','direct_bitwise_72_kv_equal'))):
        raise RuntimeError('Incomplete/unsafe numerical PASS')
    return expected,data,result


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--self-test':
        sample=dict(status='PASS',gate_level='fixed159-video-E2E',errors=[],unsafe_buffers_retained=False,safe_buffers_released=True,
            exact_comparison={'logits':True},direct_bitwise_video_hidden_equal=True,direct_bitwise_logits_equal=True,direct_bitwise_72_kv_equal=True,chinese='逐位一致'*700)
        raw=(json.dumps(sample,ensure_ascii=False)+'\n').encode('utf-8'); digest=hashlib.sha256(raw).hexdigest()
        chunks=[raw[i:i+1800] for i in range(0,len(raw),1800)]
        log='M345_RESULT_SHA256='+digest+'\n'+''.join('M345_RESULT_CHUNK='+str(i)+'/'+str(len(chunks))+':'+base64.b64encode(c).decode()+'\n' for i,c in enumerate(chunks))+'M345_VIDEO_DONE gate_rc=0\n'
        assert decode(log)[1]==raw
        for bad in (log.replace('gate_rc=0','gate_rc=1'),log.replace(digest,'0'*64),log.replace('M345_RESULT_CHUNK=1/','M345_RESULT_CHUNK=0/'),log+'M345_RESULT_SHA256='+digest):
            try: decode(bad)
            except RuntimeError: pass
            else: raise AssertionError('Invalid recovery accepted')
        print('M345_COLLECTOR_SELF_TEST_PASS UTF8/raw_chunks/hash/nonzero/duplicate_rejection'); return
    expected,data,result=decode((ROOT/'tmp/m345/fixed-video_uart.log').read_text(encoding='utf-8-sig'))
    run=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M345-fixed-video-board-01'; run.mkdir(parents=True,exist_ok=True)
    path=run/'BOARD_RESULT.json'
    if path.exists() and path.read_bytes()!=data: raise RuntimeError('Different immutable result exists')
    atomic(path,data)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        backup=run/(Path(name).name+'.before')
        if not backup.exists(): backup.write_bytes((ROOT/name).read_bytes())
    relative=path.relative_to(ROOT).as_posix(); board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board=json.loads(board_path.read_text(encoding='utf-8'))
    board['latest_m345_fixed_video']=dict(status=result['status'],evidence_level='L5_FIXED159_VIDEO_NUMERICAL_ONLY' if result['status']=='PASS' else 'FAILED_FIXED159_VIDEO',
        build_id=result['build_id'],result=relative,sha256=expected,performance_pass=False,formal_promotion_allowed=False,
        full_logits_and_72_kv_exact=result.get('direct_bitwise_logits_equal',False) and result.get('direct_bitwise_72_kv_equal',False),
        unsafe_buffers_retained=result['unsafe_buffers_retained'])
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    summary=dict(status=result['status'],sha256=expected,errors=result['errors'],performance_pass=False,
        passes=[{k:p.get(k) for k in ('label','token','logical_calls','host_calls','retry_count','language_retries','head_retries','stage_bytes','semantic')} for p in result['passes']],
        exact=result.get('exact_comparison'),prefetch=result.get('prefetch'),final_snapshot=result.get('final_snapshot'),
        next_step=result['next_step'],elapsed_s_diagnostic_not_performance=result['elapsed_s_diagnostic_not_performance'])
    atomic(run/'SUMMARY.json',(json.dumps(summary,indent=2)+'\n').encode('utf-8'))
    note=('## M345 固定159视频数值 '+result['status']+'（2026-10-01）\n\n'
        '稳定Build `0x4D395832`，冻结原四帧窗口、沿用M276最后一帧两视图/98视觉Token/159总Token，原M238调度及M241全部数学未改。'
        '同Overlay完整基线安全结束后才在候选Prefill启动权重预取；比较完整151936 logits、36K/36V、实际视频hidden、全部family字节和缩放重试/完整FPGA计数，原文件权重窗口SHA独立核对。'
        '证据 `'+relative+'` SHA `'+expected+'`，错误 `'+json.dumps(result['errors'],ensure_ascii=False)+'`。'
        '实际计数、真实runtime与候选视觉后CMA、26.5625MiB第二bank加64MiB余量、A-B交替和寄存器/安全释放见SUMMARY与原始JSON。'
        '仅L5固定159视频数值验收，总耗时带观察/资产哈希且两次视觉缓存条件不同，不能作为性能成绩；无任意提示/Web或晋级。'
        '本轮拒绝尝试以准备RESULT及错误字段为准；稳定源/服务/回滚/boot/DTB/CMA配置未改。收集失败仅修复回收，不重跑硬件。下一步 '+result['next_step']+'。\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        target=ROOT/name; content=target.read_text(encoding='utf-8')
        if expected not in content:
            heading,rest=content.split('\n',1); atomic(target,(heading+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    assert json.loads(board_path.read_text(encoding='utf-8'))['latest_m345_fixed_video']['sha256']==expected
    assert all(expected in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    atomic(run/'REPORT.md',('# M345 固定159视频数值门禁\n\n'+note).encode('utf-8'))
    print(json.dumps(summary))


if __name__=='__main__': main()
