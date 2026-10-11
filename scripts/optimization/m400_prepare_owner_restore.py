"""Restore-only follow-up to saved partial closure; no second close/free."""
import ast
import json
from types import SimpleNamespace as N
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m400_owner_restore_endpoint import verify_closed
from m400_prepare_live_inspect import fixture


def main():
    pkg=BASE/'candidates/M400-controlled-owner-restore-02'
    if pkg.exists():raise RuntimeError('Fresh restore-only package required')
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior=b['latest_m400_controlled_owner_recovery_board']
    r=json.loads((ROOT/prior['result']).read_bytes())
    if sha(ROOT/prior['result'])!=prior['sha256'] or not prior['original_seven_DMA_released'] or prior['stable_overlay_restored']:
        raise RuntimeError('Exact partial release without stable restore required')
    ns=fixture();s=ns['layer_scope'];s.closed=True;s.retained=False;s.tail=None
    ns['runtime']._m368_closed=True
    for k in ('language','vision','tokenizer'):setattr(ns['engine'],k,None)
    ns['registry'].entries=[]
    for x in ns['allocations']:x.freebuffer.state='released'
    ns['result']['released_buffers']=list(reversed(ns['result']['allocated_buffers']))
    assert verify_closed(ns)['no_release_retried']
    ns['allocations'][0].freebuffer.state='owned'
    try:verify_closed(ns)
    except RuntimeError:pass
    else:raise RuntimeError('Unreleased resource accepted')
    # Reuse proven bounded GDB/driver protocol, change only installed restore endpoint.
    old=BASE/'candidates/M400-controlled-owner-recovery-01'
    driver=(old/'m400_owner_recovery_driver.py').read_text(encoding='utf-8')
    driver=driver.replace('m400_controlled_owner_recovery_01','m400_controlled_owner_restore_02')
    driver=driver.replace('import m400_owner_recovery_endpoint as endpoint','import m400_owner_restore_endpoint as endpoint')
    # Old owner now sleeps after partial close; fixed original identity still mandatory.
    driver=driver.replace('from m400_owner_readonly_probe import verify,owner_snapshot','from m400_owner_readonly_probe import verify')
    anchor="HERE=Path(__file__).resolve().parent"
    identity='''def owner_snapshot(pid):
    p=Path('/proc')/str(pid);raw=(p/'stat').read_text();rest=raw[raw.rindex(')')+2:].split()
    fields=dict(line.split(':',1) for line in (p/'status').read_text().splitlines() if ':' in line)
    if fields['Uid'].strip().split()[0]!='0' or fields['State'].strip()[0] not in ('S','T','t'):
        raise RuntimeError('Exact original root owner must remain in its retained loop')
    return dict(start_ticks=rest[19],command=(p/'cmdline').read_bytes().split(b'\\0')[:-1])


'''
    driver=driver.replace(anchor,identity+anchor)
    ast.parse(driver,feature_version=(3,10));pkg.mkdir(parents=True)
    atomic(pkg/'m400_owner_recovery_driver.py',driver.encode(),immutable=True)
    for n in ('m400_owner_restore_endpoint.py','m400_owner_readonly_probe.py'):
        ast.parse((HERE/n).read_bytes(),feature_version=(3,10));atomic(pkg/n,(HERE/n).read_bytes(),immutable=True)
    for n in ('PIN.json','run_m400_owner_recovery.sh'):atomic(pkg/n,(old/n).read_bytes(),immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(pkg.iterdir())]
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    out=BASE/'runs/M400-controlled-owner-restore-preparation-02/RESULT.json'
    value=dict(status='PREPARED_RESTORE_ONLY_ALREADY_RELEASED_OWNER',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
               prior_partial_sha256=prior['sha256'],no_release_retried=True,new_DMA_allocations=0,
               checks=['actual closed-state checker with explicit fake buffers/MMIO passes',
                       'one unresolved wrapper refuses','global/local frame namespace merged before stable restore',
                       'frozen engine.close retains the closed board object; require identity and closed flag'],
               sourceclose='release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/tmp/m223_realtime/m223_realtime_delta/video_server.py:275')
    atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m400_controlled_owner_restore_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),
         f'## M400 已释放owner仅恢复/退出准备02（2026-10-04）\n\nSHA `{d}`；原释放失败记录不改，只修globals/locals合并后的稳定恢复。重查scope关闭/七包装器released/逆序ledger/registry空/模型调用0，任何未解状态拒绝；新入口不调用close/free。已核对冻结engine.close保留closed board属性，使用身份+closed旗标。固定原环境/稳定SHA后原主线程恢复Overlay再SystemExit1；不kill/新DMA/模型重跑，尚未执行。')
    print(value['status'],value['manifest_sha256'])


if __name__=='__main__':main()
