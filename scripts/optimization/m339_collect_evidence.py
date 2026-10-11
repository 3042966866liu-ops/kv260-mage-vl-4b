"""Verify exact COM3 evidence bytes, atomically persist then synchronize state."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]


def atomic(path, data):
    temp = path.with_name(path.name+'.m339-part')
    temp.write_bytes(data)
    os.replace(temp, path)


def main():
    mode = sys.argv[1]
    if mode not in ('preflight','results'): raise ValueError(mode)
    log = (ROOT / f'tmp/m339/export_{mode}_uart.log').read_text(encoding='utf-8-sig')
    if 'M339_EXPORT_COMPLETE' not in log: raise RuntimeError('Incomplete export')
    meta = json.loads(re.search(r'M339_EXPORT_META=(\{[^\r\n]+\})', log).group(1))
    chunks = re.findall(r'M339_EXPORT_DATA=([A-Za-z0-9+/=]+)', log)
    payload = base64.b64decode(''.join(chunks), validate=True)
    if len(payload) != meta['bytes'] or hashlib.sha256(payload).hexdigest() != meta['sha256']:
        raise RuntimeError('Archive byte/hash mismatch')
    run = ROOT / f'deployment/mage_vl4b/optimization_v1/runs/M339-profile-04-{mode}'
    run.mkdir(parents=True, exist_ok=True)
    expected = {row['path']:row for row in meta['files']}
    allowed = {'result.json','environment.json','m277_fixed_video.json','prefill_trace.json','video_forward.log'}
    if not set(expected) <= allowed: raise RuntimeError('Evidence whitelist violation')
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        if {m.name for m in archive.getmembers()} != set(expected): raise RuntimeError('Member mismatch')
        for item in archive.getmembers():
            if not item.isfile(): raise RuntimeError('Non-file evidence')
            data = archive.extractfile(item).read()
            row = expected[item.name]
            if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
                raise RuntimeError('Member byte/hash mismatch')
            destination = run / item.name
            if destination.exists() and destination.read_bytes() != data:
                raise RuntimeError('Existing evidence differs; refusing overwrite')
            atomic(destination, data)
    atomic(run / 'EXPORT_MANIFEST.json', (json.dumps(meta,indent=2)+'\n').encode())
    result = json.loads((run / 'result.json').read_text(encoding='utf-8'))
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        backup = run / (Path(name).name+'.before')
        if not backup.exists(): backup.write_bytes((ROOT / name).read_bytes())
    board = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    value = json.loads(board.read_text(encoding='utf-8-sig'))
    value['latest_m339_'+mode] = dict(status=result['status'], build_id_expected='0x4D395832',
        result=str((run / 'result.json').relative_to(ROOT)).replace('\\','/'),
        sha256=expected['result.json']['sha256'], performance_pass=False,
        overlay_requested=(mode=='results'), diagnostic_only=True)
    atomic(board,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
    note = ('## M339 隔离 Prefill 画像 '+mode+'（2026-10-01）\n\n'
        '状态 `'+result['status']+'`，原稳定 Build `0x4D395832`，诊断而非提速验收。'
        '证据 `'+str(run.relative_to(ROOT)).replace('\\','/')+'/result.json`，SHA `'+expected['result.json']['sha256']+'`；'
        '全部导出成员按板端原字节 SHA 重建。'+
        ('环境/包/导入前置，不加载 overlay。' if mode=='preflight' else '模型及调用完成情况以该结果为准；插桩结果不作正式性能成绩。')+
        '隔离包 9 载荷/37026 B，manifest `0f8b314af2ae8a463d22e40f41f472e7f4a397e24696b9d6daa9e65a677050f6`。'
        '本地 attempt01 哈希常量拼写错误已拒绝，02/03 仅本地设计迭代，均未上板；04 为首个完整传板包。'
        'WSL bash-n 沙箱拒绝，已以板端 bash-n 通过替代。稳定源/回滚/boot/DTB/CMA 未改。'
        '下一步 '+('失败则仅修正该前置级；通过后同终端预检运行一次固定159-Token诊断。' if mode=='preflight' else '归因分析主线程去重时间与后台重叠，选择一个有明确依据的候选。')+'\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        path = ROOT / name
        heading, rest = path.read_text(encoding='utf-8-sig').split('\n',1)
        atomic(path,(heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(json.dumps(dict(status=result['status'],error=result.get('first_exception'),evidence=str(run))))


if __name__ == '__main__': main()
