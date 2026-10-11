"""Recover exact COM3 result bytes and synchronize recovery evidence."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M338-real-import-01'


def atomic(path, data):
    temp = path.with_name(path.name+'.m338-part')
    temp.write_bytes(data)
    os.replace(temp, path)


def main():
    log = (ROOT / 'tmp/m338/real_import_probe_uart.log').read_text(encoding='utf-8-sig')
    digest = re.search(r'M338_RESULT_SHA256=([0-9a-f]{64})', log).group(1)
    payload = base64.b64decode(re.search(r'M338_RESULT_BASE64=([A-Za-z0-9+/=]+)', log).group(1), validate=True)
    if hashlib.sha256(payload).hexdigest() != digest: raise RuntimeError('Board payload hash mismatch')
    result = json.loads(payload)
    sudo_log = (ROOT / 'tmp/m338/sudo_recheck_03_uart.log').read_text(encoding='utf-8-sig')
    if '__M75C_UART_RC_0__' not in sudo_log: raise RuntimeError('Sudo PASS absent')
    RUN.mkdir(parents=True, exist_ok=False)
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        data = (ROOT / name).read_bytes()
        data.decode('utf-8-sig')
        (RUN / Path(name).name).write_bytes(data)
    atomic(RUN / 'BOARD_RESULT.json', payload)
    board = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    value = json.loads(board.read_text(encoding='utf-8-sig'))
    value['latest_m338_real_import'] = dict(status=result['status'], sha256=digest,
        result=str((RUN / 'BOARD_RESULT.json').relative_to(ROOT)).replace('\\','/'),
        overlay_loaded=False, hardware_gate_run=False, performance_pass=False,
        sudo_checked_pass=True, next_step='Freeze diagnostic integration package; no measurement yet')
    atomic(board, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())
    note = ('## M338 同 COM3 授权恢复，真实运行时导入接口通过（2026-10-01）\n\n'
            '用户续期后 COM3 shell 和 `sudo -n true` 返回 0。独立哈希核验的固定 runner '
            '在 PYNQ Python 导入已安装发布版 board_runtime/M238/M241，接口和权重复制规范化源码 SHA '
            '通过，所有导入路径均在发布根内；未实例化模型/overlay，未执行 FPGA，不是性能或部署 PASS。'
            '精确 COM3 结果 `deployment/mage_vl4b/optimization_v1/runs/M338-real-import-01/BOARD_RESULT.json` '
            'SHA-256 `'+digest+'`。源码探针与 runner 的板端 SHA 分别 '
            '`3c9744374b2c5ade1ce809840fcaad90d75938bbee64c2bf7eb7d5c4b572f07b`、'
            '`57be5501a8664516e374eeff2b963feb85a55b4bb590a27ae92f0638471096a9`。'
            'BOARD_GATE_RESULT.json 新增 import-only 证据；旧 sudo 阻塞历史保留，稳定 '
            'Build 0x4D395832、回滚/boot/DTB/CMA 未改。下一步将诊断组件接入独立 M276/M241 '
            '候选 runner，冻结依赖/包并检查真实接入；overlay 前再次同 COM3 sudo/环境预检，'
            '随后只跑一次冻结 159-Token 画像，不根据导入 PASS 宣称收益。\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        path = ROOT / name
        heading, rest = path.read_text(encoding='utf-8-sig').split('\n',1)
        atomic(path, (heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(result['status'], digest)


if __name__ == '__main__': main()
