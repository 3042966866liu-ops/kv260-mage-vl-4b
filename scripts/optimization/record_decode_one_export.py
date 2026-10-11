"""Record only newly exported IP evidence; preserve capacity incompleteness."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from measurement import sha256, write_json, exclusive_lock

root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
project=root/'tmp/op01_decode_one_experimental_export'
out=base/'runs/OP01-decode-one-experimental-export'
if out.exists(): raise RuntimeError('Refuse existing evidence')
files=list((root/'tmp/op01_decode_one_rtl/hls/syn/verilog').glob('*.v'))
assert len(files)==50
for p in files:
    assert sha256(p)==sha256(project/'hls/impl/ip/hdl/verilog'/p.name), p.name
archive=project/'op01_decode_one_kernel.zip'
assert sha256(archive)=='4371f7c48b5b40e87bab2780fef6fc0adc89409628688232425326c6c32b2e1f'
record=dict(status='PASS_IP_EXPORT_ONLY_CAPACITY_INCOMPLETE',build_id='0x4F503131',
    archive_sha256=sha256(archive),verilog_files_bit_identical=50,
    capacity_pass=False,formal_promotion_allowed=False,board_deployed=False,performance_pass=False,
    next_action='Isolated full-shell synthesis and place/route, then minimum board gate',
    recorded_utc=datetime.now(timezone.utc).isoformat())
note='''## Decode-one 实验 IP 导出完成（2026-09-25）

候选0x4F503131仅IP导出完成；50个Verilog与已验证综合RTL逐文件SHA一致。
容量专项仍STOPPED_BY_USER_NOT_PASS；没有bitstream、板端或性能PASS，稳定0x4D395832未改变。
修正导出器cosim_export_main在RTL复制前访问impl顶层的问题：显式暂存完整综合RTL，功能RTL未改。
仿真监视器设置none仅用于实验导出；此前关闭监视器本身未解决问题，原失败证据保留。
Vivado用户应用初始化失败在获准正常工具权限后消失，合法BASIC许可证已被接受。
下一步独立tmp/op01_d1_exp整壳综合/布局布线；不重跑CSim或容量长测。
证据：optimization_v1/runs/OP01-decode-one-experimental-export/result.json。

'''
with exclusive_lock(base/'evidence.lock'):
    out.mkdir(parents=True)
    shutil.copy2(archive,out/archive.name)
    shutil.copy2(project/'hls/impl/ip/vivado.log',out/'vivado_export.log')
    write_json(out/'result.json',record)
    backup=out/'state_before_update'; backup.mkdir()
    for p in [root/'CURRENT_STATE.md',root/'docsMILESTONES.md',base/'STATE.json',root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json']:
        shutil.copy2(p,backup/p.name)
    for p in [root/'CURRENT_STATE.md',root/'docsMILESTONES.md']:
        old=p.read_bytes(); split=old.find(b'\n')+1
        tmp=p.with_suffix('.export.partial')
        tmp.write_bytes(old[:split]+b'\n'+note.encode()+old[split:]); tmp.replace(p)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    state=json.loads(p.read_text(encoding='utf-8-sig')); state['latest_decode_one_export']=record; write_json(p,state)
    p=base/'STATE.json'; state=json.loads(p.read_text(encoding='utf-8-sig'))
    state['results']['decode_one_export']=str((out/'result.json').relative_to(root))
    state['next_action']=record['next_action']; write_json(p,state)
    write_json(out/'BACKUP_MANIFEST.json',{p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()})
print('IP_EXPORT_RECORDED_AND_BACKED_UP_NO_BOARD_PASS')
