"""Freeze interpretation; only local evidence writes, no board operation."""
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M347-asset-memory-board-01'
RAW_SHA='de66152ad095d677f4d3c605fe9462b785697d51eacc63d76b6d660505360d63'
NEXT=('先离线追踪视觉权重及安装包的全部哈希读取调用与后续mmap/加载消费者，'
      '评估隔离的只读哈希I/O候选是否能减少新增页缓存，保留全文件SHA与原检查范围。'
      'O_DIRECT仅列为待验证方案，先核对实际内核/文件系统、对齐、尾块、短读及缓冲读取回退；'
      '不得在mmap/模型加载期间并发混用，不默认开启。审计完成后只准备无Overlay的小文件组件门禁。'
      '不清缓存、不skip hash、不改稳定源码；真实完整runtime的90.5625MiB容量条件仍未通过，'
      '不进入模型重跑、视频数值或性能。')


def atomic(path,data):
    part=path.with_name(path.name+'.m347-finalize-part')
    with part.open('wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(part,path)


def main():
    raw=(RUN/'BOARD_RESULT.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==RAW_SHA
    r=json.loads(raw)
    assert r['status']=='PASS_ASSET_HASH_MEMORY_DIAGNOSTIC' and not r['errors']
    assert len(r['files'])==r['planned_files']==35
    assert not r['overlay_loaded'] and r['fpga_transactions']==r['model_forward_calls']==0
    rows={x['name']:x for x in r['files']}
    keys=('name','path','cma_delta_bytes','cached_delta_bytes','rss_delta_bytes','physical_read_bytes_delta')
    interpretation=dict(status='PASS_PER_FILE_LOCALIZATION_MEMORY_CAPACITY_NOT_PROVEN',raw_sha256=RAW_SHA,
        natural_cache=True,complete_runtime_loaded=False,
        total_assets_hashed_bytes=r['planned_asset_bytes'],
        total_physical_read_bytes_delta=r['final']['process_io']['read_bytes']-r['initial']['process_io']['read_bytes'],
        initial_cma_free_bytes=r['initial']['memory']['system_bytes']['CmaFree'],
        final_cma_free_bytes=r['final']['memory']['system_bytes']['CmaFree'],
        largest_negative_cma_intervals=[{k:rows[n][k] for k in keys} for n in ('vision_weights','lmhead_shard_2','runtime_wheel_bundle','language_shard_1')],
        inference='Most negative per-file interval in this natural-cache run was original BF16 vision asset hashing, with negligible process RSS change and increased system Cached.',
        causal_limit='System-wide snapshots cannot establish CMA page ownership, reclaimability, fragmentation, or repeatable per-file effect; other intervals show natural CMA recovery.',
        candidate_state='SUSPENDED_AT_VIDEO_CMA_FAILURE', required_cma_free_bytes=94961664,
        numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,next_step=NEXT,
        proposed_io_candidate_status='PLAN_ONLY_NOT_IMPLEMENTED_OR_BOARD_TESTED',
        primary_source=dict(url='https://man7.org/linux/man-pages/man2/open.2.html',
            constraints=['O_DIRECT can impose address/count/offset alignment and may fail or fall back for misaligned requests.',
                         'Avoid mixing direct reads and normal reads or file mmap; assess the whole loading path before adoption.',
                         'Direct I/O can reduce cache effects but can degrade throughput; no performance gain assumed.']))
    encoded=(json.dumps(interpretation,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    path=RUN/'INTERPRETATION.json'
    if path.exists(): assert path.read_bytes()==encoded
    else: atomic(path,encoded)
    interpretation_sha=hashlib.sha256(encoded).hexdigest()
    board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board=json.loads(board_path.read_text(encoding='utf-8'))
    assert board['latest_m347_asset_memory']['sha256']==RAW_SHA
    board['latest_m347_asset_memory'].update(interpretation_path=path.relative_to(ROOT).as_posix(),
        interpretation_sha256=interpretation_sha,candidate_state=interpretation['candidate_state'],next_step=NEXT)
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    note=('## M347 内存定位闭合：视觉资产哈希读取是本次最大负区间（2026-10-01）\n\n'
        '稳定Build `0x4D395832`；35次原哈希全部同SHA通过、82个≤1800B分块严格回收、无Overlay/模型forward/FPGA事务。'
        '原始SHA `'+RAW_SHA+'`，解读SHA `'+interpretation_sha+'`。'
        '自然缓存条件下，vision_bf16.safetensors读取期间CMA减101.359375MiB、Cached增459.261719MiB、RSS仅增0.035156MiB、实际读取630.164062MiB；'
        'LM head shard2 CMA减21.023438MiB，runtime wheel bundle减8.558594MiB。'
        '全检查CMA由127.121094MiB至48.800781MiB，其他文件区间也出现自然回收；不能据此确认页归属、可回收性或碎片原因。'
        '本次没有加载完整runtime，不是容量、数值或性能PASS；双bank候选继续暂停，原90.5625MiB门槛保持。'
        '没有清缓存、GC/trim、skip hash、源/服务/回滚/boot/DTB/CMA修改或硬件门禁重跑。'
        'O_DIRECT仅为文档查证后的待评估方案，尚无实现或板端试验。证据 `'+path.relative_to(ROOT).as_posix()+'`。下一步：'+NEXT+'\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        p=ROOT/name; text=p.read_text(encoding='utf-8')
        if interpretation_sha not in text:
            heading,rest=text.split('\n',1); atomic(p,(heading+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    report=RUN/'REPORT.md'; old=report.read_text(encoding='utf-8')
    if interpretation_sha not in old:
        heading,rest=old.split('\n',1)
        summary=('\n\n本次已将最大CMA下降定位到视觉BF16资产的哈希读取区间，尚未证明可稳定改善运行时容量。\n\n'
            '| 读取区间 | CMA变化 MiB | Cached变化 MiB | 进程RSS变化 MiB | 实际读取 MiB |\n'
            '| --- | ---: | ---: | ---: | ---: |\n')
        for n in ('vision_weights','lmhead_shard_2','runtime_wheel_bundle'):
            x=rows[n]
            summary+=f"| {n} | {x['cma_delta_bytes']/1048576:.3f} | {x['cached_delta_bytes']/1048576:.3f} | {x['rss_delta_bytes']/1048576:.3f} | {x['physical_read_bytes_delta']/1048576:.3f} |\n"
        summary+='\n下一步：'+NEXT+'\n\n'
        summary+='候选约束依据：[Linux open(2) 官方手册](https://man7.org/linux/man-pages/man2/open.2.html)。仅说明对齐和混用约束，不能证明本板收益。\n\n'
        summary+='解读证据 `INTERPRETATION.json` SHA `'+interpretation_sha+'`；三份记录已同步。\n\n'
        atomic(report,(heading+summary+rest.lstrip('\n')).encode('utf-8'))
    assert hashlib.sha256((RUN/'BOARD_RESULT.json').read_bytes()).hexdigest()==RAW_SHA
    assert all(interpretation_sha in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert json.loads(board_path.read_text(encoding='utf-8'))['latest_m347_asset_memory']['interpretation_sha256']==interpretation_sha
    print(json.dumps(dict(status='M347_INTERPRETATION_SYNCHRONIZED',raw_sha256=RAW_SHA,
                          interpretation_sha256=interpretation_sha,next_step=NEXT),ensure_ascii=True))


if __name__=='__main__': main()
