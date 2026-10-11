"""Finite fixed revision03 sequence. Never board, restart, kill or extra samples."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync

PY = Path('C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
PS = PY.parents[1] / 'native/powershell/pwsh.exe'
HERE = ROOT / 'scripts/optimization'
RUN = BASE / 'runs/M441-revision03-continuation-01'
PREP = RUN / 'PREPARATION.json'
FINAL = RUN / 'RESULT.json'
GUARD = BASE / 'runs/M441-guard03-component-02/RESULT.json'
AUDIT = BASE / 'runs/M441-random-budget-audit-01/RESULT.json'


def synced(path):
    digest = sha(path)
    assert all(digest in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert any(digest in json.dumps(v) for v in board.values())
    return json.loads(path.read_bytes())


def prepare():
    assert not RUN.exists()
    g = synced(GUARD)
    assert g['status'] == 'PASS_M441_ACTUAL_SV_GUARD_COMPONENT_ONLY'
    assert sha(HERE / 'm441_observer03.py') == g['guard_logic_sha256']
    a = synced(AUDIT)
    assert a['estimate']['proposed_fixed_cycle_budget'] == 80000000
    zero = {}
    for v in ('A', 'B'):
        p = BASE / f'runs/M441-long-{v}-gate_up-zero-02/RESULT.json'
        assert synced(p)['status'] == 'PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL'
        zero[v] = sha(p)
    names = ['m441_continue03.py', 'm441_prepare_long_rtl03.py', 'm441_run_long_rtl03.ps1', 'm441_collect_long_rtl03.py',
             'm441_observer03.py', 'm441_progress03.py', 'm351_workflow.py', 'm438_prepare.py', 'm439_prepare_rtl.py',
             'm441_collect_long_rtl.py', 'm441_uvm_evidence.py']
    # Resolve the collector's actual imported UVM module, never invent a path.
    names = [n for n in names if (HERE / n).exists()]
    import re
    collector_source = (HERE / 'm441_collect_long_rtl03.py').read_text(encoding='utf-8-sig')
    for module in re.findall(r'^from (m\w+) import', collector_source, re.M):
        if module + '.py' not in names:
            names.append(module + '.py')
    proof = dict(status='PREPARED_M441_REVISION03_FIXED_SEQUENCE', guard_sha256=sha(GUARD), audit_sha256=sha(AUDIT),
                 prior_zero_sha256=zero, cycle_budget=80000000, child_wall_budget_s=86400, supervisor_wall_budget_s=432000,
                 remaining_formal_runs=10, fixed_sequence=['gate_up Random A/B', 'mlp_down Zero A/B', 'mlp_down Random A/B', 'q Zero A/B', 'q Random A/B'],
                 no_dynamic_budget=True, no_extra_samples=True, default_disabled=True,
                 files=[dict(path=(HERE / n).relative_to(ROOT).as_posix(), sha256=sha(HERE / n)) for n in names],
                 board=False, performance=False, protocol_or_OOC_auto_start=False)
    atomic(PREP, encoded(proof), immutable=True)
    sync('latest_m441_revision03_continuation_preparation', dict(status=proof['status'], result=PREP.relative_to(ROOT).as_posix(), sha256=sha(PREP), board=False),
         f'## M441 独立03固定诊断协议准备（2026-10-08）\n\nSHA {sha(PREP)}；实际SV守卫三例/15+11组件检查同SHA，原Zero复用；固定80M/每工具24h/监督120h，剩余10个RTL运行，不改DUT/数学/模型分布、不追加样本；Fatal零返回也拒绝。默认关闭，0新实际DUT运行/板端；失败原字节回收同步，超时不kill。下一步显式Run原版Random诊断后按固定序列裁决。')
    print(proof['status'], sha(PREP))


def run():
    p = synced(PREP)
    assert not (RUN / 'START.json').exists() and not FINAL.exists(), 'Existing run: collect/read only'
    started = time.time()
    atomic(RUN / 'START.json', encoded(dict(pid=__import__('os').getpid(), epoch=started, preparation_sha256=sha(PREP))), immutable=True)
    events, comparisons = [], []
    def save(**row):
        events.append(dict(epoch=time.time(), **row))
        atomic(RUN / 'PROGRESS.json', encoded(events))
        print(json.dumps(row), flush=True)
    def call(tag, args):
        for f in p['files']:
            assert sha(ROOT / f['path']) == f['sha256'], f['path']
        log = RUN / (tag + '.log')
        assert not log.exists(), 'No tool rerun'
        with log.open('wb') as stream:
            child = subprocess.Popen(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            began = time.time()
            save(stage=tag, status='RUNNING', pid=child.pid)
            while child.poll() is None:
                if time.time() - began > p['child_wall_budget_s'] or time.time() - started > p['supervisor_wall_budget_s']:
                    save(stage=tag, status='BUDGET_STOP_CHILD_RETAINED', pid=child.pid)
                    raise TimeoutError('Keep child and original buffers; no kill/restart')
                time.sleep(5)
        atomic(RUN / (tag + '_exit.json'), encoded(dict(original_rc=child.returncode)), immutable=True)
        save(stage=tag, status='RETURNED', original_rc=child.returncode)
        return child.returncode
    def collect(v, family, mode):
        ev = BASE / f'runs/M441-long-{v}-{family}-{mode}-03/RESULT.json'
        if not ev.exists():
            call(f'collect_{v}_{family}_{mode}', [str(PY), '-B', str(HERE / 'm441_collect_long_rtl03.py'), v, family, mode, '03'])
        return synced(ev)
    def tool(v, family, mode):
        rc = call(f'tool_{v}_{family}_{mode}', [str(PS), '-NoProfile', '-File', str(HERE / 'm441_run_long_rtl03.ps1'), '-Variant', v, '-Family', family, '-Mode', mode.capitalize(), '-Enable'])
        # Collection is mandatory even after tool-level failure. Missing saved
        # logs stop collection; never repeat the tool to repair collection.
        r = collect(v, family, mode)
        assert rc == 0 and r['status'].startswith('PASS_M441_'), r['status']
        return r
    def compare(family, mode, a, b, reused=False):
        ac, bc = a['done']['cycles'], b['done']['cycles']
        ok = bc <= ac if mode == 'zero' else bc < ac
        row = dict(family=family, mode=mode, A_cycles=ac, B_cycles=bc, cycle_reduction_pct=100 * (ac - bc) / ac, pass_gate=ok, reused_original_zero=reused)
        comparisons.append(row)
        save(stage='comparison', **row)
        assert ok, 'Fixed comparison gate failed; no extra samples'
    try:
        za, zb = [synced(BASE / f'runs/M441-long-{v}-gate_up-zero-02/RESULT.json') for v in ('A', 'B')]
        compare('gate_up', 'zero', za, zb, True)
        for family in ('gate_up', 'mlp_down', 'q'):
            for v in ('A', 'B'):
                ev = BASE / f'runs/M441-long-{v}-{family}-RTL-preparation-03/RESULT.json'
                if not ev.exists():
                    rc = call(f'prepare_{v}_{family}', [str(PY), '-B', str(HERE / 'm441_prepare_long_rtl03.py'), v, family])
                    assert rc == 0
                synced(ev)
                tool(v, family, 'compile')
            if family != 'gate_up':
                a, b = [tool(v, family, 'zero') for v in ('A', 'B')]
                compare(family, 'zero', a, b)
            a, b = [tool(v, family, 'random') for v in ('A', 'B')]
            compare(family, 'random', a, b)
        final = dict(status='PASS_M441_REVISION03_COMPLETE_LONG_CHAIN_RTL', errors=[])
    except Exception as exc:
        final = dict(status='STOP_M441_REVISION03_FIXED_SEQUENCE', errors=[repr(exc)])
    final.update(preparation_sha256=sha(PREP), comparisons=comparisons, events=events, elapsed_s=time.time() - started,
                 board=False, performance=False, processes_killed=False, promoted=False,
                 next='Inspect saved diagnosis and bind later gates independently; no automatic OOC/full shell/board.')
    atomic(FINAL, encoded(final), immutable=True)
    sync('latest_m441_revision03_continuation_result', dict(status=final['status'], result=FINAL.relative_to(ROOT).as_posix(), sha256=sha(FINAL), board=False),
         f'## M441 独立03固定诊断协议闭合（2026-10-08）\n\nSHA {sha(FINAL)}；{final["status"]}；原02失败保留，固定次数/预算未追加，原日志/返回码同步，0kill/板端/请求收益。下一步审查本级诊断，不自动后级。')
    print(final['status'], sha(FINAL), flush=True)
    if final['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['Prepare', 'Run'])
    parser.add_argument('--enable', action='store_true')
    args = parser.parse_args()
    if args.mode == 'Prepare':
        prepare()
    elif args.enable:
        run()
    else:
        parser.error('Run disabled; use --enable for the authorized fixed protocol')
