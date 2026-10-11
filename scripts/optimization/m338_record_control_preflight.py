"""Record COM3 control prerequisites without implying a hardware gate."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M338-control-preflight-02'


def atomic(path, content):
    temporary = path.with_name(path.name + '.m338-part')
    temporary.write_bytes(content)
    os.replace(temporary, path)


def main():
    login = ROOT / 'tmp/m338/login_recheck_02_uart.log'
    sudo = ROOT / 'tmp/m338/sudo_recheck_02_uart.log'
    if 'ubuntu@kria:~$' not in login.read_text(encoding='utf-8-sig'):
        raise RuntimeError('Authenticated prompt not observed')
    if '__M75C_UART_RC_1__' not in sudo.read_text(encoding='utf-8-sig'):
        raise RuntimeError('Expected sudo failure marker absent')
    RUN.mkdir(parents=True, exist_ok=False)
    sources = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md',
                 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        path = ROOT / name
        content = path.read_bytes()
        content.decode('utf-8-sig')
        sources[name] = hashlib.sha256(content).hexdigest()
        (RUN / path.name).write_bytes(content)
    result = dict(status='BLOCKED_SUDO_PREOVERLAY', authenticated_shell_observed=True,
                  sudo_noninteractive_pass=False, overlay_loaded=False,
                  hardware_gate_run=False, performance_pass=False,
                  stable_build_expected='0x4D395832', stable_rollback_modified=False,
                  recovery_source_sha256=sources,
                  evidence_logs=[str(login.relative_to(ROOT)), str(sudo.relative_to(ROOT))],
                  next_step='Continue offline/import-only integration; same COM3 sudo authorization '
                            'must pass before any overlay operation')
    payload = (json.dumps(result, indent=2) + '\n').encode()
    atomic(RUN / 'RESULT.json', payload)
    board = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    state = json.loads(board.read_text(encoding='utf-8-sig'))
    state['latest_m338_control_preflight'] = dict(
        status=result['status'], hardware_gate_run=False, overlay_loaded=False,
        result=str((RUN / 'RESULT.json').relative_to(ROOT)).replace('\\', '/'),
        sha256=hashlib.sha256(payload).hexdigest(), performance_pass=False)
    atomic(board, (json.dumps(state, ensure_ascii=False, indent=2)+'\n').encode())
    note = ('## M338 COM3 登录已恢复，sudo 前置未通过（2026-10-01）\n\n'
            '用户释放 COM3 后核验 `ubuntu@kria:~$`；同终端 `sudo -n true` 返回 1，'
            '提示需要密码。未执行 overlay、模型或 FPGA 门禁，不是硬件 FAIL。'
            '证据 `deployment/mage_vl4b/optimization_v1/runs/M338-control-preflight-02/RESULT.json`，'
            '原始日志 `tmp/m338/login_recheck_02_uart.log` 和 `sudo_recheck_02_uart.log`；'
            'BOARD_GATE_RESULT.json 仅增加 control-preflight 记录，旧硬件结果保持。'
            '稳定 Build 0x4D395832、回滚/boot/DTB/CMA 不变。下一步继续无需 sudo 的离线及导入验证，'
            '任何 overlay 前必须重新通过同 COM3 授权和固定环境门禁。\n\n')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        path = ROOT / name
        original = path.read_text(encoding='utf-8-sig')
        heading, rest = original.split('\n', 1)
        atomic(path, (heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(result['status'])


if __name__ == '__main__':
    main()
