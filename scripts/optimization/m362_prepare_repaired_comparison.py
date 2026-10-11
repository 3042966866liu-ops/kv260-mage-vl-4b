"""New revision only: preserve M361 failure and reject schema before big hashes."""
import ast
import json
import shutil
import m351_workflow as w
from m361_prepare_load_comparison import source
from m358_prepare_capacity import replace_once

PKG=w.BASE/'candidates/M362-common-load-observer-01'

def main():
    assert not PKG.exists()
    failed=w.BASE/'runs/M361-load-A1-board-01/BOARD_RESULT.json'
    r=json.loads(failed.read_text(encoding='utf-8'));assert w.sha(failed)=='d03bc5fe44799f289220eae67991514f93a7c569325aea6d5d687fb452c46f7a'
    assert not r['overlay_loaded'] and not r['allocated_buffers'] and not r['fpga_transactions'] and "KeyError: 'file_count'" in r['traceback']
    closure=dict(status='CLOSED_PRE_OVERLAY_MANIFEST_SCHEMA_FAILURE',raw_sha256=w.sha(failed),overlay_loaded=False,allocated_buffers=0,fpga_transactions=0,original_gate_rc=1,export_rc=0,rerun_original_forbidden=True,repair='Fresh M362 revision accepts exact pinned legacy schema with full whitelist/file sizes/SHA; reject package compatibility before big asset hashing')
    out=failed.parent/'INTERPRETATION.json';w.atomic(out,w.encoded(closure),immutable=True);digest=w.sha(out)
    note=f'## M361 共同加载入口清单格式拒绝闭合\n\n稳定发布清单没有现代file_count字段，通用verify_self误套导致KeyError；原rc1/export0、0Overlay/分配/模型/FPGA，原SHA `{w.sha(failed)}` 保留。诊断未完成，不是CMA或稳定版数值失败。闭合SHA `{digest}`。仅在独立M362修复兼容并提前校验；原A1不重执行。'
    w.sync('latest_m361_schema_failure_closure',dict(status=closure['status'],sha256=digest,result=out.relative_to(w.ROOT).as_posix()),note)
    review=w.ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md';text=review.read_text(encoding='utf-8-sig')
    if digest not in text:
        title,rest=text.split('\n',1);w.atomic(review,(title+'\n\n'+note+'\n\n固定发布包与新诊断包清单schema分别离线验证，不把缺少现代统计字段当作包损坏；全部路径、逐文件大小与SHA仍需严格核对。兼容检查必须先于大资产SHA阶段。\n\n'+rest).encode('utf-8'))
    old=w.BASE/'candidates/M361-common-load-observer-01';PKG.mkdir(parents=True)
    for p in old.iterdir():
        if p.name in ('PACKAGE_MANIFEST.json','m361_load_only_probe.py','m361_export_result.py','run_m361_load_only.sh','m361_observers.py'):continue
        shutil.copyfile(p,PKG/p.name)
    shutil.copyfile(w.HERE/'m361_observers.py',PKG/'m362_observers.py')
    shutil.copyfile(w.HERE/'m362_package_identity.py',PKG/'m362_package_identity.py')
    s=source().replace('M361','M362').replace('m361','m362')
    s=replace_once(s,'from owned_buffer_release import OwnedBufferRelease','from owned_buffer_release import OwnedBufferRelease\nfrom m362_package_identity import verify_frozen_package')
    s=replace_once(s,"        verify_self(TARGET,TARGET_SHA)\n",'')
    s=replace_once(s,"        result['initial_service'] = service_stopped()","        result['initial_service'] = service_stopped()\n        result['target_package_identity']=verify_frozen_package(TARGET,TARGET_SHA,legacy_manifest=not is_candidate)")
    # Clarify that the fixed stable constructor uses its actual original bit.
    s=s.replace('Original complete video runtime with M357 bit;','Original complete video runtime with selected stable/M357 bit;')
    ast.parse(s,feature_version=(3,10));w.atomic(PKG/'m362_load_only_probe.py',s.encode('utf-8'))
    for source_name,target in [('m361_export_result.py',PKG/'m362_export_result.py'),('run_m361_load_only.sh',PKG/'run_m362_load_only.sh')]:
        w.atomic(target,(old/source_name).read_text(encoding='utf-8').replace('M361','M362').replace('m361','m362').encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m362-common-load-observer-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    for name in ('m361_collect_load_comparison.py','m361_control.ps1','m361_close_load_comparison.py','m361_record_transfer.py','m361_verify_support.py'):
        generated=(w.HERE/name).read_text(encoding='utf-8').replace('M361','M362').replace('m361','m362')
        # Shared observer source also needs a local host module, outside the frozen package.
        w.atomic(w.HERE/name.replace('m361','m362'),generated.encode('utf-8'),immutable=True)
    shutil.copyfile(w.HERE/'m361_observers.py',w.HERE/'m362_observers.py')
    out=w.BASE/'runs/M362-load-comparison-preparation-01/RESULT.json'
    raw=dict(status='PREPARED_PENDING_OFFLINE_VALIDATION',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),files=len(rows),bytes=sum(x['bytes'] for x in rows),rejected_original_sha256=w.sha(failed),board_executed=False,legacy_schema_early_check=True)
    w.atomic(out,w.encoded(raw),immutable=True)
    print(json.dumps(raw))

if __name__=='__main__':main()
