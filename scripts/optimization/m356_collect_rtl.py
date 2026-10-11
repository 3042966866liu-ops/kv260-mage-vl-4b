"""Strict complete frozen Q output / protocol / schedule collection for either RTL."""
import argparse
import csv
import json
import re
from pathlib import Path
import m351_workflow as w
from m357_uvm_log_evidence import evaluate
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'

def read_tv(path):
    text=path.read_text(encoding='utf-8-sig')
    values=re.findall(r'(?m)^\s*(0x[0-9a-fA-F]+|[0-9]+)\s*$',text)
    # Headers use a number on the transaction line, not a bare value.
    assert text.count('[[transaction]]')==1 and text.count('[[/transaction]]')==1
    return [int(value,16 if value.startswith('0x') else 10) for value in values]

def read_tv_checked(path,errors):
    try:return read_tv(path)
    except (OSError,ValueError,AssertionError) as exc:
        errors.append(path.name+': '+type(exc).__name__+': '+str(exc))
        return []

def paired_shard_events(rows,allow_stable_initial_idle=False):
    active=[False]*4;starts=[];dones=[];initial=[];valid=True
    for row in rows:
        if row['event'] not in ('start','done'):continue
        i=int(row['shard']);cycle=int(row['cycle'])
        if not 0<=i<4:valid=False;continue
        if row['event']=='start':
            if active[i]:valid=False
            active[i]=True;starts.append(row)
        elif active[i]:active[i]=False;dones.append(row)
        elif allow_stable_initial_idle and cycle==1 and not starts:initial.append(row)
        else:valid=False
    if initial and (len(initial)!=4 or sorted(int(r['shard']) for r in initial)!=list(range(4))):valid=False
    return starts,dones,initial,valid and not any(active)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('variant',choices=['stable','candidate']);a=ap.parse_args()
    name='m356_stable_q_trace' if a.variant=='stable' else 'm357_candidate_q_trace'
    directory=ROOT/'tmp'/name;tag='m356' if a.variant=='stable' else 'm357';upper=tag.upper()
    runlog=directory/'verilog'/('m356_xsim_03.log' if a.variant=='stable' else 'm357_xsim.log')
    receipt=directory/'verilog'/('m356_exit_03.json' if a.variant=='stable' else 'm357_exit.json')
    if not receipt.exists():raise RuntimeError('RTL process not finished; do not collect incomplete output')
    exit_data=json.loads(receipt.read_text(encoding='utf-8-sig'));log=runlog.read_text(encoding='utf-8-sig',errors='replace')
    build=0x4d395832 if a.variant=='stable' else 0x4d333537
    checks={};collection_errors=[]
    checks['engine_success']=exit_data.get('simulation_rc',exit_data.get('process_rc'))==0 and not exit_data['engine_error']
    checks['uvm_no_errors'],uvm_evidence=evaluate(directory/'verilog',log)
    checks['no_engine_failure']='ERROR:' not in log and 'Fatal:' not in log and 'necessary license' not in log
    checks['completed_transaction']='RTL Simulation : 1 / 1' in log
    tvdir=directory/'tv/rtldatafile';prefix='rtl.m89x_runtime_kernel.autotvout_'
    data=read_tv_checked(tvdir/(prefix+'rx_V_data_V.dat'),collection_errors)
    golden=(ROOT/'tmp/m356_stable_q_trace/golden.bin').read_bytes()
    raw=b''.join(value.to_bytes(8,'little') for value in data)
    checks['full_wire_bits_exact']=raw==golden and len(raw)==524288
    for field in ('keep','strb'):
        values=read_tv_checked(tvdir/(prefix+'rx_V_'+field+'_V.dat'),collection_errors)
        checks[field+'_full_exact']=len(values)==65536 and all(value==255 for value in values)
    lasts=read_tv_checked(tvdir/(prefix+'rx_V_last_V.dat'),collection_errors)
    checks['one_final_tlast']=len(lasts)==65536 and sum(lasts)==1 and lasts[-1]==1
    checks['build_return_exact']=read_tv_checked(tvdir/(prefix+'ap_return.dat'),collection_errors)==[build]
    trace=directory/'verilog'/(tag+'_trace.csv')
    rows=list(csv.DictReader(trace.open(encoding='utf-8',newline=''))) if trace.exists() else []
    if not trace.exists():collection_errors.append('Trace CSV missing')
    starts,dones,initial_idle_done,lifecycle_valid=paired_shard_events(rows,a.variant=='stable')
    apdone=[r for r in rows if r['event']=='ap_done']
    checks['all_shard_start_finish']=lifecycle_valid and len(starts)==len(dones)==8 and all(sum(int(r['shard'])==i for r in starts)==2 and sum(int(r['shard'])==i for r in dones)==2 for i in range(4))
    checks['top_ap_done']=bool(apdone) and int(apdone[0]['value'])==65536
    statistics=re.findall(upper+r'_SHARD i=(\d+) AR=(\d+) R=(\d+) RSTALL=(\d+) FIFO_MAX=(\d+)',log)
    checks['four_fifo_bounds']=len(statistics)>=4 and all(0<=int(row[4])<=8192 for row in statistics)
    result=dict(status='PASS_FULL_FROZEN_Q_RTL' if all(checks.values()) else 'FAIL_FULL_FROZEN_Q_RTL',build_id=hex(build),variant=a.variant,
        checks=checks,uvm_evidence=uvm_evidence,collection_errors=collection_errors,output_bytes=len(raw),output_sha256=w.sha(directory/'golden.bin') if (directory/'golden.bin').exists() else None,
        wire_sha256=__import__('hashlib').sha256(raw).hexdigest(),reference_sha256=__import__('hashlib').sha256(golden).hexdigest(),
        start_events=starts,done_events=dones,initial_idle_done_events=initial_idle_done,top_done_events=apdone,statistics=statistics,
        complete_summary=re.findall(upper+r'_TRACE_DONE[^\r\n]+',log),
        model='Original random-stall VIP, 0-256-cycle latency distribution, seed 356. Same model does not imply identical delay consumption when scheduling changes. Not PS DDR arbitration or board speedup.',
        evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in [receipt,runlog,trace,*sorted(tvdir.glob('*.dat'))] if p.exists()],board=False,promoted=False)
    ev=BASE/('runs/M356-stable-q-rtl-01/RESULT.json' if a.variant=='stable' else 'runs/M357-candidate-q-rtl-01/RESULT.json')
    if ev.exists():
        rejected=json.loads(ev.read_text(encoding='utf-8'))
        repair_key='uvm_no_errors' if a.variant=='candidate' else 'all_shard_start_finish'
        assert rejected['status']=='FAIL_FULL_FROZEN_Q_RTL' and rejected['checks'][repair_key] is False
        assert all(v for k,v in rejected['checks'].items() if k!=repair_key),'Cannot reinterpret a real DUT failure'
        assert rejected['wire_sha256']==result['wire_sha256']
        for row in rejected['evidence']:assert w.sha(ROOT/row['path'])==row['sha256'],'Original run bytes changed'
        result['rejected_collection_sha256']=w.sha(ev)
        result['collection_only_repair']=('Missing quiet UVM summary; macro/default-action/source audit added.' if a.variant=='candidate' else 'Four initial cycle1 idle done signals preceded every start; pair every actual start with a later done, retain raw initial events. Generated stable child sets done when idle and ap_start=0.')+' No RTL simulation rerun or source change.'
        ev=BASE/('runs/M357-candidate-q-rtl-02/RESULT.json' if a.variant=='candidate' else 'runs/M356-stable-q-rtl-02/RESULT.json')
    w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
    w.sync('M356_stable_q_rtl' if a.variant=='stable' else 'M357_candidate_q_rtl',dict(status=result['status'],build_id=result['build_id'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix()),
        tag.upper()+' '+a.variant+' 固定原始0:q RTL完整输出/65536words/TLAST/keep/strb/return/四FIFO/启动完成核对 '+result['status']+'；原随机背压模型，不是板端净收益。证据 '+sha)
    print(json.dumps(dict(status=result['status'],sha256=sha,checks=checks),ensure_ascii=True))
    if not all(checks.values()):raise SystemExit(1)
if __name__=='__main__':main()
