import json
from pathlib import Path

from m351_workflow import ROOT, atomic, encoded, sha, sync


OUT = ROOT / "deployment/mage_vl4b/optimization_v1/runs/M436-com3-open-precheck-02/RESULT.json"
LOG = ROOT / "tmp/m43601/board/sudo_upload_resume03.log"
PRIOR_LOG = ROOT / "tmp/m43601/board/sudo_upload_resume02.log"
CONTROL = ROOT / "scripts/optimization/m436_control_resume03.ps1"

if OUT.exists():
    raise RuntimeError("Immutable M436 COM3 precheck 02 already exists")

result = {
    "status": "BLOCKED_COM3_UNAVAILABLE_BEFORE_COMMAND",
    "port": "COM3",
    "expected_ftdi_serial": "XFL1PL5N11BJB",
    "pnputil_device_identity": "FTDIBUS\\VID_0403+PID_6011+XFL1PL5N11BJB\\0000",
    "pnputil_status": "Started",
    "serial_open": "Access to the path 'COM3' is denied",
    "mode_com3": "Device COM3 is not currently available",
    "visible_process_inventory": ["conhost", "pwsh"],
    "handle_utility_available": False,
    "sudo_command_sent": False,
    "upload_started": False,
    "board_command_sent": False,
    "board_gate_started": False,
    "prior_empty_log_preserved": {
        "path": "tmp/m43601/board/sudo_upload_resume02.log",
        "bytes": PRIOR_LOG.stat().st_size,
        "sha256": sha(PRIOR_LOG),
    },
    "attempt_log": {
        "path": LOG.relative_to(ROOT).as_posix(),
        "bytes": LOG.stat().st_size,
        "sha256": sha(LOG),
    },
    "control_path": CONTROL.relative_to(ROOT).as_posix(),
    "control_sha256": sha(CONTROL),
    "candidate_manifest_sha256": "1fa013addfb4db1351d9155a3ffc7c041009d57bafa1dd5128d30ee003405ed7",
    "interpretation": "The board device is enumerated but unavailable to this process. Available evidence cannot distinguish another process holding the exclusive serial handle from a Windows device access/permission denial. No board command was sent.",
    "next_action": "Do not retry COM3 open until the Windows port becomes available or a handle/permission diagnostic identifies the cause; preserve both empty attempt logs. The candidate package remains unchanged and unuploaded.",
}

atomic(OUT, encoded(result), immutable=True)
digest = sha(OUT)
note = (
    "## M436 COM3 重试仍在打开阶段被拒（2026-10-07）\n\n"
    f"结果 `{OUT.relative_to(ROOT).as_posix()}` SHA `{digest}`。用户说明 COM3 早已释放；本次换用全新日志后实际重试，"
    "Windows PnP 仍列出目标 FTDI COM3（Started），但 SerialPort.Open 返回 Access Denied，`mode COM3:` 报设备当前不可用。"
    "可见进程清单没有 PuTTY/串口工具，且无 handle 工具；现有证据不能区分隐藏占用与访问权限问题。"
    "空日志保留；sudo、上传、板端命令及门禁均未发送。修正版包仍未上传，M435 原始结果不变。"
    "下一步先用本机只读句柄/权限诊断定位原因，端口可用前不重复打开；不测温。\n"
)
sync(
    "latest_m436_com3_open_precheck_02",
    {
        "status": result["status"],
        "result": OUT.relative_to(ROOT).as_posix(),
        "sha256": digest,
        "manifest_sha256": result["candidate_manifest_sha256"],
        "board_command_sent": False,
    },
    note,
)
print("M436_COM3_PRECHECK02_SYNC", digest)
