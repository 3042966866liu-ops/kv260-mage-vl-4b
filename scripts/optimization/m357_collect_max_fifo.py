"""Collect the one maximum-descriptor/backpressure simulation without rerunning."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from m356_collect_rtl import read_tv_checked,paired_shard_events
import m351_workflow as w
from m357_uvm_log_evidence import evaluate

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
ap=argparse.ArgumentParser();ap.add_argument('--debug',action='store_true');ap.add_argument('--chunked',action='store_true');args=ap.parse_args()
directory=ROOT/('tmp/m357_chunked_max_04' if args.chunked else ('tmp/m357_guarded_max_03' if args.debug else 'tmp/m357_guarded_max_02'))
receipt=directory/'verilog/m357_max_exit.json'
if not receipt.exists():raise RuntimeError('Maximum FIFO process not finished')
logpath=directory/'verilog/m357_max_xsim.log'
log=logpath.read_text(encoding='utf-8-sig',errors='replace')
uvm_clean,uvm_evidence=evaluate(directory/'verilog',log)
checks=dict(process_rc=json.loads(receipt.read_text(encoding='utf-8'))['simulation_rc']==0,
    no_engine_failure='ERROR:' not in log and 'Fatal:' not in log and 'necessary license' not in log,
    no_uvm_errors=uvm_clean,
    completed_transaction='RTL Simulation : 1 / 1' in log,
    shared_output_hold=('M357_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000' if args.chunked else 'M357_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=600000') in log,
    shared_axi_address_hold='M357_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000' in log)
tvdir=directory/'tv/rtldatafile';prefix='rtl.m89x_runtime_kernel.autotvout_'
collection_errors=[]
raw=b''.join(v.to_bytes(8,'little') for v in read_tv_checked(tvdir/(prefix+'rx_V_data_V.dat'),collection_errors))
golden=(directory/'golden.bin').read_bytes()
checks['complete_wire_exact']=raw==golden and len(raw)==2621440
for field in ('keep','strb'):
    values=read_tv_checked(tvdir/(prefix+'rx_V_'+field+'_V.dat'),collection_errors)
    checks[field+'_exact']=len(values)==327680 and all(v==255 for v in values)
last=read_tv_checked(tvdir/(prefix+'rx_V_last_V.dat'),collection_errors)
checks['one_final_tlast']=len(last)==327680 and sum(last)==1 and last[-1]==1
checks['build_return']=read_tv_checked(tvdir/(prefix+'ap_return.dat'),collection_errors)==[0x4d333537]
trace=directory/'verilog/m357_trace.csv'
rows=list(csv.DictReader(trace.open(encoding='utf-8',newline=''))) if trace.exists() else []
if not trace.exists():collection_errors.append('Trace CSV missing')
starts,dones,initial,paired=paired_shard_events(rows)
checks['all_10_descriptors_4_shards']=paired and len(starts)==len(dones)==40 and all(sum(int(r['shard'])==i for r in starts)==sum(int(r['shard'])==i for r in dones)==10 for i in range(4))
checks['top_done_count']=any(r['event']=='ap_done' and int(r['value'])==327680 for r in rows)
stats=re.findall(r'M357_SHARD i=(\d+) AR=(\d+) R=(\d+) RSTALL=(\d+) FIFO_MAX=(\d+)',log)
checks['fifo_bound_and_actual_full']=len(stats)==4 and all(0<=int(r[4])<=8192 for r in stats) and any(int(r[4])==8192 for r in stats)
metrics=re.findall(r'M357_AXI_METRICS shard=(\d+) requested=(\d+) received=(\d+) awaiting_with_pending=(\d+) address_stalls=(\d+)',log)
checks['all_requested_beats_received']=len(metrics)==4 and all(int(r[1])==int(r[2])>0 for r in metrics)
checks['actual_axi_address_backpressure']=any(r[0]=='0' and int(r[4])>0 for r in metrics)
held=re.findall(r'M357_OUTPUT_HELD_VALID_CYCLES=(\d+)',log)
checks['actual_valid_output_backpressure']=len(held)==1 and int(held[0])>0
result=dict(status='PASS_MAX_DESCRIPTOR_FIFO_RTL' if all(checks.values()) else 'FAIL_MAX_DESCRIPTOR_FIFO_RTL',
    build_id='0x4D333537',checks=checks,uvm_evidence=uvm_evidence,collection_errors=collection_errors,output_bytes=len(raw),wire_sha256=hashlib.sha256(raw).hexdigest(),
    reference_sha256=hashlib.sha256(golden).hexdigest(),start_events=starts,done_events=dones,
    fifo_statistics=stats,axi_metrics=metrics,output_held_valid_cycles=held,
    scope='Legal G1 W4 10 maximum-row descriptors, zero scales, deterministic shared w0 ARREADY hold and600000-cycle continuous shared AXIS backpressure; no board bandwidth claim',
    evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in [receipt,logpath,trace,*sorted(tvdir.glob('*.dat'))] if p.exists()],
    board=False,promoted=False)
stop=directory/'verilog/m357_wall_stop.json'
if stop.exists():
    result['software_wall_budget_exceeded']=True
    result['software_wall_stop']=json.loads(stop.read_text(encoding='utf-8-sig'))
    result['evidence'].append(dict(path=stop.relative_to(ROOT).as_posix(),sha256=w.sha(stop)))
if args.chunked:
    result['scope']='Same maximum10 descriptor/row/FIFO fixture, verified10000-cycle w0 hold and100000-cycle held-valid output pause with actual8192 occupancy, bounded Tcl clock checkpoints; no board bandwidth claim'
    result['same_level_repair_preparation_sha256']=w.sha(BASE/'runs/M357-chunked-max-preparation-01/RESULT.json')
    result['preserved_failed_attempt_sha256']=w.sha(BASE/'runs/M357-max-fifo-rtl-02/RESULT.json')
if args.debug:
    result['metadata_only_repair_sha256']=w.sha(BASE/'runs/M357-debug-guard-compile-01/RESULT.json')
    result['preserved_failed_attempt_sha256']=w.sha(BASE/'runs/M357-max-fifo-rtl-01/RESULT.json')
ev=BASE/('runs/M357-max-fifo-rtl-03/RESULT.json' if args.chunked else ('runs/M357-max-fifo-rtl-02/RESULT.json' if args.debug else 'runs/M357-max-fifo-rtl-01/RESULT.json'))
w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M357_max_fifo_rtl',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
    'M357 最大10descriptor/四FIFO8192/有界输出与AXI背压完整2621440B输出、TLAST/keep/strb/return/ap_done/所有AXI beats检查 '+result['status']+'；只为RTL协议与数值证据，无板端收益。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha,checks=checks)))
if not all(checks.values()):raise SystemExit(1)
