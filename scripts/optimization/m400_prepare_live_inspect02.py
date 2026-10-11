"""Retry only owner inspection with demonstrated bounded GDB startup settings."""
import ast
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync


def main():
    old=BASE/'candidates/M400-owner-live-inspect-01';pkg=BASE/'candidates/M400-owner-live-inspect-02'
    if pkg.exists():raise RuntimeError('Fresh owner-inspection02 package required')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior=board['latest_m400_native_stack_board_02']
    r=json.loads((ROOT/prior['result']).read_bytes())
    if sha(ROOT/prior['result'])!=prior['sha256'] or r['gate_return_code'] or 'M400_ATTACH_COMPLETE' not in r['gdb_log']:
        raise RuntimeError('Actual no-auto-solib startup proof required')
    driver=(old/'m400_live_inspect_driver.py').read_text(encoding='utf-8').replace('m400_live_owner_inspect_01','m400_live_owner_inspect_02')
    anchor="['/usr/bin/gdb','--nx','--nh','--batch','-p',str(pid)"
    if driver.count(anchor)!=1:raise RuntimeError('GDB startup anchor changed')
    driver=driver.replace(anchor,"['/usr/bin/gdb','--nx','--nh','--readnever','--batch','-iex','set auto-load off','-iex','set auto-solib-add off','-p',str(pid)")
    # Preserve the partial stdout even if a later function call times out.
    driver=driver.replace("    except BaseException:r['traceback']=traceback.format_exc()", "    except subprocess.TimeoutExpired as exc:\n        r['traceback']=traceback.format_exc();r['gdb_log']=(exc.output or b'').decode(errors='replace')\n    except BaseException:r['traceback']=traceback.format_exc()")
    driver=driver.replace("+'set $m400_gil = (int)PyGILState_Ensure()\\n'", "+'echo M400_LIVE_ATTACH_COMPLETE\\n\\n'\n            +'set $m400_gil = (int)PyGILState_Ensure()\\n'\n            +'echo M400_LIVE_GIL_ACQUIRED\\n\\n'")
    ast.parse(driver,feature_version=(3,10));pkg.mkdir(parents=True)
    for name in ('PIN.json','m400_live_owner_inspect.py','m400_owner_readonly_probe.py','run_m400_live_inspect.sh'):
        atomic(pkg/name,(old/name).read_bytes(),immutable=True)
    atomic(pkg/'m400_live_inspect_driver.py',driver.encode(),immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(pkg.iterdir())]
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    out=BASE/'runs/M400-owner-live-inspect-preparation-02/RESULT.json'
    value=dict(status='PREPARED_LIVE_OWNER_INSPECTION_FIXED_GDB_STARTUP',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
               actual_startup_proof_sha256=prior['sha256'],inspector_payload_unchanged_sha256=sha(pkg/'m400_live_owner_inspect.py'),
               timeout_s=12,partial_stdout_saved_on_timeout=True,resources_release_planned=False,new_overlay_loads=0)
    atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m400_owner_live_inspect_preparation_02',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),
         f'## M400 owner内部只读检查02准备（2026-10-04）\n\nSHA `{d}`；只修已取得板端证据的GDB启动符号加载组织，实际scope检查器/PID/原包/失败SHA保持，加入attach/GIL标记及超时stdout。12秒同预算、原保留循环短暂恢复后再次挂起，绝不close/释放/Overlay/模型重跑。未执行，不解锁回收或单层。')
    print(value['status'],value['manifest_sha256'])


if __name__=='__main__':main()
