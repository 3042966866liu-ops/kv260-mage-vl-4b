"""Describe one controlled pair, without promoting a throughput tier."""
import json
from pathlib import Path
import shutil
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
out=base/'runs/OP01-decode-one-ab-comparison-01'
paths=[base/f'runs/OP01-decode-one-ab-{mode}-01/result.json' for mode in ('stable','candidate')]
a,b=[json.loads(p.read_text()) for p in paths]
if a['status']!='PASS_STABLE_DECODE_REFERENCE' or b['status']!='PASS_CANDIDATE_DECODE_EXACT':raise RuntimeError('Missing A/B')
if a['kv_sha256']!=b['kv_sha256'] or not b['comparisons']['logits']['bit_exact']:raise RuntimeError('Numerical mismatch')
if a['checkpoint_sha256']!=b['checkpoint_sha256'] or a['input_token']!=b['input_token']:raise RuntimeError('Different input')
for x in (a,b):
    if x['read_preparation']['protocol']!='two verified Decode-order scans; no drop_caches':raise RuntimeError('Preparation differs')
    if x['attribution']['counters']['logical_calls']!=162 or x['attribution']['closure_error_ns']!=0:raise RuntimeError('Incomplete accounting')
e=[x['attribution']['main_thread_exclusive_s'] for x in (a,b)]
table=[('权重文件读取',*[y.get('weight_file_read',0) for y in e]),
       ('设备完成等待（不是纯PL周期）',*[y.get('device_completion_wait',0) for y in e]),
       ('权重CMA复制',*[y.get('weight_cma_copy',0) for y in e]),
       ('权重缓存同步',*[y.get('weight_cache_sync',0) for y in e]),
       ('完整单步（含插桩）',a['decode_seconds'],b['decode_seconds']),
       ('两遍预读成本（不计入单步）',*[sum(p['wall_s'] for p in x['read_preparation']['passes']) for x in (a,b)])]
ratio=a['decode_seconds']/b['decode_seconds']
report='# Decode-one 同条件单步实板对照\n\n'
report+='固定KV852、输入Token1291，输出Token均为311；36层KV各增长1，72个KV数组哈希一致，完整logits逐字节一致。\n\n'
report+='|指标|稳定核T32（秒）|Decode-one（秒）|\n|---|---:|---:|\n'
report+=''.join(f'|{name}|{v1:.6f}|{v2:.6f}|\n' for name,v1,v2 in table)
report+=f'\n该单次配对观察到总耗时比 {ratio:.3f}×，耗时变化 {(1-b["decode_seconds"]/a["decode_seconds"])*100:.2f}%。尚无重复统计，不是正式吞吐结果。\n\n'
report+='缓存准备协议相同不等于驻留完全相同；以下是整个进程计数，不能全部归为权重设备I/O：\n\n'
for mode,x in zip(('稳定核','候选核'),(a,b)):
    report+=f'- {mode}：Decode read_bytes增量 {x["io_after"]["read_bytes"]-x["io_before"]["read_bytes"]}，rchar增量 {x["io_after"]["rchar"]-x["io_before"]["rchar"]}；调用{ x["attribution"]["counters"]["host_calls"]}，重试{x["attribution"]["counters"]["scale_retry_count"]}。\n'
report+='\n准备/初始化/保存不计入Decode；未隐藏预读成本。权重读取、等待均为软件计时区间。容量专项仍未完成，实验不晋级稳定配置；未达到2 token/s，也未完成128有效Token测试。\n'
record=dict(status='MEASURED_ONE_PAIR_FULL_LOGITS_EXACT',performance_pass=False,formal_promotion_allowed=False,
    stable_s=a['decode_seconds'],candidate_s=b['decode_seconds'],observed_ratio=ratio,
    source_sha256=[sha256(p) for p in paths],next_action='Short continuous Decode with per-step exact reference, then bounded repeated paired timing; choose next optimization from measured dominant cost')
note=f'## Decode-one 完整单步A/B已测（2026-09-25）\n\n稳定核{a["decode_seconds"]:.6f}s，候选{b["decode_seconds"]:.6f}s；本轮单次观察比{ratio:.3f}×，未正式性能晋级。\n完整logits逐字节一致，72个KV哈希一致；两遍预读成本单列，稳定核已恢复。\n证据optimization_v1/runs/OP01-decode-one-ab-comparison-01/REPORT.md。下一步短连续Decode及有界重复配对。\n\n'
with exclusive_lock(base/'evidence.lock'):
    out.mkdir(parents=True,exist_ok=False);backup=out/'state_before_update';backup.mkdir()
    board_path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    for p in (root/'CURRENT_STATE.md',root/'docsMILESTONES.md',board_path,base/'STATE.json'):shutil.copy2(p,backup/p.name)
    for name,p in zip(('stable.json','candidate.json'),paths):shutil.copy2(p,out/name)
    write_json(out/'result.json',record);(out/'REPORT.md').write_text(report,encoding='utf-8')
    for p in (root/'CURRENT_STATE.md',root/'docsMILESTONES.md'):
        old=p.read_bytes();split=old.find(b'\n')+1;tmp=p.with_suffix('.ab.partial')
        tmp.write_bytes(old[:split]+b'\n'+note.encode('utf-8')+old[split:]);tmp.replace(p)
    board=json.loads(board_path.read_text(encoding='utf-8-sig'));board['latest_decode_one_ab_comparison']=record;write_json(board_path,board)
    state=json.loads((base/'STATE.json').read_text(encoding='utf-8-sig'))
    state['results']['decode_one_ab_comparison']=str((out/'result.json').relative_to(root));state['next_action']=record['next_action'];write_json(base/'STATE.json',state)
    write_json(out/'BACKUP_MANIFEST.json',{p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()})
print(report)
