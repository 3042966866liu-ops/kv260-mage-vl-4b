"""One finite HLS attempt; a budget failure preserves the original process."""
import argparse
import json
import subprocess
import time
from m441_host_io08 import atomic
from m351_workflow import ROOT, BASE, encoded, sha, sync
from m441_supervisor04 import boot, process, classify

RUN = BASE / 'runs/M443-pair-pipeline-hls-01'
OUT = ROOT / 'tmp/m443_pair_pipeline_01'
PREP = BASE / 'runs/M443-pair-pipeline-preparation-01/RESULT.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if not args.run:
        raise RuntimeError('Explicit run required')
    if RUN.exists() or (OUT / 'hls_console.log').exists() or (ROOT / 'tmp/m443_hls_project_01').exists():
        raise RuntimeError('Existing attempt: observe or collect only')
    prep = json.loads(PREP.read_bytes())
    for row in prep['files']:
        assert sha(ROOT / row['path']) == row['sha256']
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        assert sha(PREP) in (ROOT / name).read_text(encoding='utf-8-sig')
    RUN.mkdir(parents=True)
    command = ['D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat', '--mode', 'hls', '--tcl', str(OUT / 'run_m443_hls.tcl'), '--log', str(OUT / 'm443_hls')]
    started = time.monotonic()
    start_boot = boot()
    budget = 7200
    rc = None
    retained = False
    with (OUT / 'hls_console.log').open('xb') as stream:
        child = subprocess.Popen(command, cwd=ROOT / 'tmp', stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        identity = process(child.pid)
        born = identity.get('creation_FILETIME')
        active = dict(status='RUNNING_M443_HLS01', tool_pid=child.pid, tool_creation_FILETIME=born, start_boot=start_boot,
                      preparation_sha256=sha(PREP), controller_sha256=sha(__file__), command=command, wall_budget_s=budget, process_killed=False)
        atomic(RUN / 'ACTIVE.json', encoded(active), immutable=True)
        sync('latest_m443_hls_active', dict(status=active['status'], result=(RUN / 'ACTIVE.json').relative_to(ROOT).as_posix(), sha256=sha(RUN / 'ACTIVE.json'), board=False),
             f'## M443独立HLS实际启动（2026-10-10）\n\nSHA {sha(RUN / "ACTIVE.json")}；新Build0x4D343433，PID{child.pid}；同4.8ns/1.3ns，先原数值CSim再综合。2h有限预算，超限保留工具不kill；原M441项目不改。当前不是数值/II/资源/RTL或板端PASS。')
        print(json.dumps(active), flush=True)
        while child.poll() is None:
            state = process(child.pid, born)
            current_boot = boot()
            atomic(RUN / 'PROGRESS.json', encoded(dict(status=classify(start_boot, current_boot, state), process=state,
                   elapsed_s=time.monotonic()-started, budget_s=budget, boot=current_boot)))
            if time.monotonic()-started > budget:
                retained = True
                break
            time.sleep(10)
        if not retained:
            rc = child.returncode
    receipt = dict(status='M443_HLS_TOOL_EXIT_REQUIRES_STRICT_COLLECTION' if rc == 0 else 'STOP_M443_HLS01', original_rc=rc,
                   elapsed_s=time.monotonic()-started, budget_exceeded=retained, process_retained=retained, process_killed=False,
                   tool_pid=child.pid, tool_creation_FILETIME=born, preparation_sha256=sha(PREP), command=command,
                   console_sha256=sha(OUT / 'hls_console.log'), numerical_pass=False, board=False)
    atomic(RUN / 'EXIT.json', encoded(receipt), immutable=True)
    if retained or rc:
        atomic(RUN / 'STOP.json', encoded(receipt), immutable=True)
        sync('latest_m443_hls_stop', dict(status=receipt['status'], result=(RUN / 'STOP.json').relative_to(ROOT).as_posix(), sha256=sha(RUN / 'STOP.json'), board=False),
             f'## M443独立HLS本级停止（2026-10-10）\n\nSHA {sha(RUN / "STOP.json")}；原rc{rc}，budget_exceeded={retained}。原日志/工具保留，未扩大RTL/整壳/板端。只调当前级，不重跑已PASS原M441。')
    print(json.dumps(receipt), flush=True)
    return 1 if retained or rc else 0


if __name__ == '__main__':
    raise SystemExit(main())
