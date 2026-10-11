"""Close the pre-import user-permission rejection; preserve immutable evidence."""
from pathlib import Path
import m351_workflow as w

root=w.ROOT
log=root/'tmp/m357_board/buildid_syntax.log'
text=log.read_text(encoding='utf-8-sig')
assert 'Permission denied' in text and '__M357_SYNTAX_RC_126__' in text
assert not (root/'tmp/m357_board/buildid_uart.log').exists()
control=root/'scripts/optimization/m357_control.ps1'
src=control.read_text(encoding='utf-8-sig')
assert 'sudo -n bash -n $taskRemote/m357_gate_runner.sh' in src
assert src.index('-LogPath "tmp/m357_board/${taskLabel}_sudo.log"') < src.index('sudo -n bash -n $taskRemote/m357_gate_runner.sh')
transfer=root/'deployment/mage_vl4b/optimization_v1/runs/M357-artifact-transfer-01/BOARD_RESULT.json'
assert w.sha(transfer)=='ee811aff76b67acee810bdec52950b25a3db8a95669186d6b2ff795ca9d9a3ac'
path=root/'deployment/mage_vl4b/optimization_v1/runs/M357-root-syntax-repair-01/RESULT.json'
r=dict(status='CLOSED_PRE_IMPORT_PERMISSION_REJECTION',build_id='0x4D333537',
 original_syntax_rc=126,log=str(log.relative_to(root)),log_sha256=w.sha(log),
 controller_sha256=w.sha(control),transfer_sha256=w.sha(transfer),
 overlay_loaded=False,fpga_transactions=0,board_gate_executed=False,
 package_modified=False,permissions_modified=False,self_test_pass=True,
 change='After same-terminal sudo-n confirmation, syntax-check the root-only transferred runner with sudo-n bash-n; retain original failure log.',
 next_step='First Build-ID gate only; no prior hardware attempt occurred.')
w.atomic(path,w.encoded(r),immutable=True)
digest=w.sha(path)
note=f'## M357 上板前语法检查权限拒绝已闭合（2026-10-02）\n\nBuild0x4D333537；整包传输已通过且临时地址恢复。普通用户 bash-n 无法进入 root-only 候选目录，原 rc126 与日志保留；0 Overlay/FPGA 事务。控制端改为先 sudo-n，再 root bash-n，SelfTest 通过；包及板端权限不改。证据 `{path.relative_to(root).as_posix()}`，SHA `{digest}`。下一步首次 Build-ID 门禁。'
w.sync('latest_m357_root_syntax_repair',dict(status=r['status'],sha256=digest,result=path.relative_to(root).as_posix()),note)
print(r['status'],digest)
