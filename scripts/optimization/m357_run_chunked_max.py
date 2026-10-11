"""Run exactly one prepared offline simulation with independent wall bound."""
import argparse
import json
import subprocess
import time
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
OUT=ROOT/'tmp/m357_chunked_max_04/verilog'
ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');a=ap.parse_args()
if not a.run:raise RuntimeError('Default disabled')
prep=BASE/'runs/M357-chunked-max-preparation-01/RESULT.json';spec=json.loads(prep.read_text(encoding='utf-8'))
for row in spec['files']:assert w.sha(ROOT/row['path'])==row['sha256']
if (OUT/'m357_max_xsim.log').exists():raise RuntimeError('Existing attempt; collect only')
for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert w.sha(prep) in (ROOT/name).read_text(encoding='utf-8')
started=time.monotonic();wall=False
with (OUT/'m357_max_console.log').open('wb') as log:
    proc=subprocess.Popen(['D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat','m357_guarded_debug','-f','chunked.args'],cwd=OUT,stdout=log,stderr=subprocess.STDOUT)
    print('M357_CHUNKED_MAX_STARTED wrapper_pid='+str(proc.pid),flush=True)
    try:rc=proc.wait(timeout=spec['wall_budget_s'])
    except subprocess.TimeoutExpired:
        wall=True
        stopped=subprocess.run(['taskkill.exe','/PID',str(proc.pid),'/T','/F'],capture_output=True,text=True)
        if stopped.returncode:raise RuntimeError('Offline software stop failed')
        rc=proc.wait(timeout=10)
        w.atomic(OUT/'m357_wall_stop.json',w.encoded(dict(software_only=True,board=False,wall_budget_s=spec['wall_budget_s'],elapsed_s=time.monotonic()-started)))
w.atomic(OUT/'m357_max_exit.json',w.encoded(dict(simulation_rc=rc,software_wall_budget_exceeded=wall,elapsed_s=time.monotonic()-started)))
print(json.dumps(dict(simulation_rc=rc,wall_budget_exceeded=wall,elapsed_s=time.monotonic()-started)))
raise SystemExit(rc)
