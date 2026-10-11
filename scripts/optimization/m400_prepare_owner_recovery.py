"""Freeze a strictly pristine-abort cooperative owner recovery after live proof."""
import ast
import json
from types import SimpleNamespace as N
from unittest.mock import patch
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m400_owner_recovery_endpoint import close_pristine
from m400_prepare_live_inspect import fixture


def offline_checks():
    checks=[]
    ns=fixture();events=[];s=ns['layer_scope'];tail=s.tail;r=ns['result'];rt=ns['runtime']
    def scope_close():
        if s.retained:raise RuntimeError('Actual contract retained refusal')
        s.closed=True;tail.closed=True;events.append('original_scope_close')
    def engine_close():
        if not s.closed:raise RuntimeError('Scope still active')
        for i in range(6,-1,-1):
            ns['allocations'][i].freebuffer.state='released';r['released_buffers'].append(r['allocated_buffers'][i])
        rt._m368_closed=True;events.append('original_engine_close')
    def restore(**kw):
        if kw!=dict(completion_proven=True,release_proven=True):raise RuntimeError('Unsafe restore')
        ns['registry'].entries.clear();events.append('original_registry_restore')
    s.close=scope_close;ns['engine'].close=engine_close;ns['registry'].restore_all=restore
    ns['policy'].stop_sampling=lambda:events.append('original_observer_drain')
    result=close_pristine(ns)
    assert result['release_wrapper_states']==['released']*7 and events==['original_observer_drain','original_scope_close','original_engine_close','original_registry_restore']
    checks.append('actual recovery core checks ordering with explicit fake close/backend/MMIO')
    ns=fixture();ns['policy'].active=True
    try:close_pristine(ns)
    except RuntimeError:checks.append('active policy refuses before all close calls')
    else:raise RuntimeError('Active policy accepted')
    ns=fixture();ns['policy'].stop_sampling=lambda:None
    def failed_close():raise RuntimeError('Explicit fake scope close failure')
    ns['layer_scope'].close=failed_close
    try:close_pristine(ns)
    except RuntimeError:assert ns['layer_scope'].retained;checks.append('scope close failure restores retained and refuses engine close')
    else:raise RuntimeError('Scope failure accepted')
    return checks


def main():
    pkg=BASE/'candidates/M400-controlled-owner-recovery-01'
    if pkg.exists():raise RuntimeError('Fresh recovery package required')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior=board['latest_m400_owner_live_inspect_board_02']
    r=json.loads((ROOT/prior['result']).read_bytes())
    if sha(ROOT/prior['result'])!=prior['sha256'] or r['gate_return_code'] or not r['live_owner']['proof']['pristine_source_abort_conditions_passed']:
        raise RuntimeError('Actual pristine Python ownership proof required')
    checks=offline_checks();pkg.mkdir(parents=True)
    for n in ('m400_owner_recovery_endpoint.py','m400_owner_recovery_driver.py','m400_live_owner_inspect.py','m400_owner_readonly_probe.py'):
        ast.parse((HERE/n).read_bytes(),feature_version=(3,10));atomic(pkg/n,(HERE/n).read_bytes(),immutable=True)
    atomic(pkg/'PIN.json',(BASE/'candidates/M400-owner-live-inspect-02/PIN.json').read_bytes(),immutable=True)
    runner=b'''#!/usr/bin/env bash\nset -euo pipefail\n[[ $EUID == 0 && $# == 1 ]] || exit 65\ntask_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)\nexec /usr/local/share/pynq-venv/bin/python -B "$task_dir/m400_owner_recovery_driver.py" --enable-controlled-owner-recovery "$1"\n'''
    atomic(pkg/'run_m400_owner_recovery.sh',runner,immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(pkg.iterdir())]
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    out=BASE/'runs/M400-controlled-owner-recovery-preparation-01/RESULT.json'
    value=dict(status='PREPARED_CONTROLLED_PRISTINE_ABORT_RECOVERY',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
               actual_owner_proof_sha256=prior['sha256'],checks=checks,fake_close_backends_in_offline_tests=True,
               source_compatibility_guard_original_SHA_preserved=True,owner_kill_planned=False,
               trigger='install in original main thread, then cooperative SIGUSR1',
               scope_exception='only rechecked pristine pre-binding source abort; original scope close remains authoritative',
               seven_release_callbacks='original engine.close and OwnedBufferRelease checks, reverse order exactly once',
               stable_restore='original fixed environment preflight in original owner before Overlay reload',
               original_failure_raw_immutable=True,new_DMA_allocations=0,model_forward_calls=0)
    atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m400_controlled_owner_recovery_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),
         f'## M400 原owner协作回收准备（2026-10-04）\n\nSHA `{d}`；实际内部pristine证明已通过，重新检查所有scope/worker/七资源身份后，仅此源码检查前失败允许原scope.close；原engine.close/每块OwnedBufferRelease安全检查、逆序一次回收和patch恢复保持。原主线程安装协作SIGUSR1入口，处理后原Python正常SystemExit1，原失败raw不改；固定原环境前置及稳定bit SHA后才恢复Overlay。不kill/外部free/新DMA/模型重跑，超时保留。3个核心顺序/拒绝测试明确fake close/MMIO，3.10仅语法；尚未执行。')
    print(value['status'],value['manifest_sha256'])


if __name__=='__main__':main()
