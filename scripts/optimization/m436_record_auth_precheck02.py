from pathlib import Path

from m351_workflow import ROOT, atomic, encoded, sha, sync


OUT = ROOT / "deployment/mage_vl4b/optimization_v1/runs/M436-authorization-precheck-02/RESULT.json"
LOG = ROOT / "tmp/m43601/board/sudo_upload_resume04.log"
CONTROL = ROOT / "scripts/optimization/m436_control_resume04.ps1"

if OUT.exists():
    raise RuntimeError("Immutable M436 authorization precheck 02 already exists")

result = {
    "status": "BLOCKED_M436_SUDO_EXPIRED_BEFORE_UPLOAD",
    "port": "COM3",
    "serial_shell_prompt": "ubuntu@kria:~$",
    "serial_open": "PASS",
    "command": "sudo -n true",
    "command_return_code": 1,
    "captured_error": "sudo: a password is required",
    "log_path": LOG.relative_to(ROOT).as_posix(),
    "log_sha256": sha(LOG),
    "control_path": CONTROL.relative_to(ROOT).as_posix(),
    "control_sha256": sha(CONTROL),
    "manifest_sha256": "1fa013addfb4db1351d9155a3ffc7c041009d57bafa1dd5128d30ee003405ed7",
    "upload_started": False,
    "board_command_after_precheck": False,
    "board_gate_started": False,
    "next_action": "Renew sudo interactively in PuTTY on COM3. Then keep the authorized serial shell available for the fixed controller; if closing PuTTY invalidates the sudo timestamp, run the upload runner in that same shell/session rather than retrying a fresh sudo check.",
}
atomic(OUT, encoded(result), immutable=True)
digest = sha(OUT)
note = (
    "## M436 COM3 已可访问，但 sudo 授权过期（2026-10-07）\n\n"
    f"结果 `{OUT.relative_to(ROOT).as_posix()}` SHA `{digest}`。受限环境外的固定控制器已成功打开 COM3，并确认提示符 `ubuntu@kria:~$`；"
    "随后 `sudo -n true` 返回 rc1 / `sudo: a password is required`。因此未查询板端包目录、未上传任何文件，也未运行门禁。"
    "这解释了此前的 COM3 争议：本地沙箱低完整性进程无法打开端口；当前已证明端口可由授权控制器访问。"
    "下一步需要在 PuTTY 的 COM3 手动续期 sudo；须维持同一串口授权上下文，避免关闭后票据失效。"
    "不测温、不覆盖 M435 原始结果。\n"
)
sync(
    "latest_m436_authorization_precheck_02",
    {
        "status": result["status"],
        "result": OUT.relative_to(ROOT).as_posix(),
        "sha256": digest,
        "manifest_sha256": result["manifest_sha256"],
        "upload_started": False,
    },
    note,
)
print("M436_AUTH_PRECHECK02_SYNC", digest)
