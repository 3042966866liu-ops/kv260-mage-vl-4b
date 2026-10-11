"""Preserve adapter source and offline evidence; never imply board-layer PASS."""
import json
from pathlib import Path
import shutil
from measurement import sha256,write_json,exclusive_lock

root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
out=base/'runs/OP01-decode-one-layer-preparation-01'
note='''## Decode-one 真实运行时单层入口离线准备（2026-09-25）

新增Decode-only适配器保留M238打包、解析、重试与LM Head路径，仅在显式单token作用域修改候选config bit24；稳定Build-ID及多token输入拒绝。
单层入口从SHA锁定的原decode提取，保留原第一层算术，只限制循环为一层并返回hidden/KV；没有重写Attention/Norm。
6项适配器单测通过；真实M238方法分派及原Decode单层软件对照在Windows/WSL均通过，hidden归一化输出与KV一致。
尚未单layer上板或性能A/B，不改变上轮真实单chain通过的证据；稳定overlay/boot未动。
证据optimization_v1/runs/OP01-decode-one-layer-preparation-01/result.json，源代码和更新前状态已备份。
下一步封装隔离候选board_runtime（仅Build-ID与核名变化），恢复同一KV852进行稳定/候选单layer输出与KV比较，再执行完整Decode A/B。

'''
with exclusive_lock(base/'evidence.lock'):
    out.mkdir(parents=True,exist_ok=False)
    backup=out/'state_before_update';backup.mkdir()
    for p in (root/'CURRENT_STATE.md',root/'docsMILESTONES.md',base/'STATE.json'):
        shutil.copy2(p,backup/p.name)
    sources={}
    for name in ('decode_one_runtime_adapter.py','decode_one_layer_probe.py',
                 'test_decode_one_runtime_adapter.py','check_decode_one_runtime_integration.py'):
        path=Path(__file__).with_name(name);shutil.copy2(path,out/name);sources[name]=sha256(path)
    write_json(out/'result.json',dict(status='PASS_OFFLINE_LAYER_ENTRY_ONLY',board_executed=False,
        test_count=6,unit_test_tool_chunk='38e0ee',windows_wsl_integration_tool_chunk='2a3f47',
        source_sha256=sources,full_decode_performance_pass=False))
    (out/'REPORT.md').write_text('# 单层入口准备\n\n'+note,encoding='utf-8')
    for p in (root/'CURRENT_STATE.md',root/'docsMILESTONES.md'):
        raw=p.read_bytes();split=raw.find(b'\n')+1;tmp=p.with_suffix('.layerprep.partial')
        tmp.write_bytes(raw[:split]+b'\n'+note.encode('utf-8')+raw[split:]);tmp.replace(p)
    state=json.loads((base/'STATE.json').read_text(encoding='utf-8-sig'))
    state['results']['decode_one_layer_preparation']=str((out/'result.json').relative_to(root))
    state['next_action']='Package isolated candidate runtime and test same-KV852 stable/candidate layer0 hidden and KV; then full Decode A/B'
    write_json(base/'STATE.json',state)
    write_json(out/'BACKUP_MANIFEST.json',{p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()})
print('OFFLINE_LAYER_PREPARATION_RECORDED_NOT_BOARD_PASS')
