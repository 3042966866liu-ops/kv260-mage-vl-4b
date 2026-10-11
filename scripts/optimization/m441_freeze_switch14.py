"""Preserve unexecuted13 package; freeze observer preflight repair in fresh14."""
from pathlib import Path
import json
import m351_workflow as w
from m441_host_io08 import atomic

source=(w.HERE/'m441_switch_workflow13.py').read_text(encoding='utf-8')
for old,new in [('M441-first-switch-CMA-13','M441-first-switch-CMA-14'),('cma13','cma14'),('CMA13','CMA14'),('control13.ps1','control14.ps1'),('workflow13.py','workflow14.py'),('candidate_13','candidate_14'),('evidence_13','evidence_14')]:source=source.replace(old,new)
source=source.replace('raw=(w.HERE/n).read_bytes();ast.parse(raw,feature_version=(3,10));atomic(PKG/n,raw,immutable=True)',
                     "raw=(w.HERE/n).read_bytes().replace(b'first_switch_cma_evidence_13',b'first_switch_cma_evidence_14').replace(b'first_switch_cma13',b'first_switch_cma14');ast.parse(raw,feature_version=(3,10));atomic(PKG/n,raw,immutable=True)")
atomic(w.HERE/'m441_switch_workflow14.py',source.encode(),immutable=True)
old_control=w.HERE/'m441_switch_control13.ps1'
old_sha=w.sha(old_control)
log=w.ROOT/'tmp/m441_cma13/Upload_sudo.log'
assert 'a password is required' in log.read_text(encoding='utf-8-sig')
value=dict(status='BLOCKED_M441_CMA13_SUDO_EXPIRED',log_sha256=w.sha(log),original_controller_sha256=old_sha,
           uploaded_files=0,overlay_calls=0,model_requests=0,diagnostic_not_executed=True,
           successor='m441_switch_control14.ps1',next_step='User sudo-v then close PuTTY; directly Upload and one Run14, no old13 replay',
           offline_repair='Trace observer capability setup before marking programming active; unsupported tracing leaves old completed owner safely releasable')
out=w.BASE/'runs/M441-CMA-authorization-13/RESULT.json'
atomic(out,w.encoded(value),immutable=True);sha=w.sha(out)
w.sync('latest_m441_CMA_authorization',dict(status=value['status'],result=out.relative_to(w.ROOT).as_posix(),sha256=sha),
       f'## M441 切核诊断sudo过期13（2026-10-09）\n\nSHA {sha}；COM3 shell正常但sudo需要密码，0上传/Overlay/请求。原日志保留，不重复探测；只读源码/旧FAIL已完整闭合。另冻结14观察器能力前置，避免trace前置失败误成未知编程，尚未执行；人工续期后直接新入口Upload/Run一次。')
print(value['status'],sha)
