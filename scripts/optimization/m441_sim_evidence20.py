"""Saved-only supplemental W2/W4 RTL adjudication; never launches tools."""
import collections
import hashlib
import json
import re
from m351_workflow import ROOT, BASE, HERE, encoded, sha, sync
from m441_host_io08 import atomic
from m356_collect_rtl import read_tv
from m357_uvm_log_evidence import evaluate
from m441_progress03 import validate_progress
from m441_protocol_evidence import clean_engine, validate_timeout

RUN=BASE/'runs/M441-W2-W4-simulation-coverage-19'
PREP=RUN/'PREPARATION.json'


def parsed(p,receipt,log,payload,golden,ports,uvm_clean):
    e=p['expected'];n=e['output_words'];errors=[]
    def rows(tag):return [{k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',s)} for s in re.findall(r'^'+tag+r'[^\r\n]*$',log,re.M)]
    m=rows('M441MAX_METRIC');q=rows('M441MAX_PROTOCOL');o=rows('M441C19_OVERLAP')
    checks=dict(original_rc=receipt['original_rc']==0 and receipt['gate_rc']==0,
                wall_budget=not receipt['software_wall_budget_exceeded'],
                complete_output=payload==golden and len(payload)==e['output_bytes'],
                Build=ports['ap_return']==[0x4D343431],
                TLAST=ports['rx_V_last_V']==[0]*(n-1)+[1],
                keep=ports['rx_V_keep_V']==[255]*n,strb=ports['rx_V_strb_V']==[255]*n,
                uvm_clean=uvm_clean,engine_complete='RTL Simulation : 1 / 1' in log and clean_engine(log),
                AR_hold='M441MAX_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000' in log,
                RX_hold='M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000' in log)
    done=re.findall(r'^M441MAX_DONE cycles=(\d+) output=(\d+) tlast=(\d+)\s*$',log,re.M)
    checks['done_once']=len(done)==1 and 0<int(done[0][0])<=p['cycle_budget'] and done[0][1:]==(str(n),'1')
    checks['four_shards']=all(len(v)==4 and sorted(x['shard'] for x in v)==list(range(4)) for v in (m,q,o))
    checks['MAC']=len(m)==4 and all(x['mac_calls']==e['mac_calls_per_shard'] and x['iterations']==16*e['mac_calls_per_shard'] for x in m)
    checks['reads']=len(m)==4 and all(x['R']==e['weight_beats_per_shard'] and x['pending']==x['bad_RLAST']==x['bad_RRESP']==0 for x in m)
    checks['descriptors']=len(q)==4 and all(x['descriptors']==e['descriptors'] for x in q)
    checks['FIFO34']=len(q)==4 and all(x['queue_writes']==x['queue_reads']==e['weight_beats_per_shard'] and x['queue_high']==34 and x['queue_full']>0 and x['queue_final']==0 for x in q)
    checks['FIFO8192_bounds']=len(q)==4 and all(0<=x['FIFO_MAX']<=8192 for x in q)
    if p['maximum_pressure']:checks['FIFO8192_full']=len(q)==4 and any(x['FIFO_MAX']==8192 for x in q)
    checks['read_accepted_MAC_overlap']=len(o)==4 and all(x['accepted']>0 for x in o)
    hold=re.findall(r'^M441_BOUNDARY_LAST_HOLD valid_cycles=(\d+) accepted_before=(\d+)\s*$',log,re.M)
    checks['final_TLAST_hold128']=hold==[('128',str(n-1))]
    held=re.findall(r'^M441MAX_HELD_VALID=(\d+) STABLE_OUTPUT_CYCLES=(\d+)\s*$',log,re.M)
    checks['output_payload_stable']=len(held)==1 and all(int(v)>0 for v in held[0])
    checks['AR_payload_stable']=len(q)==4 and any(x['shard']==0 and x['AR_STABLE']>=10000 for x in q)
    progress=validate_progress(log,p,'B');checks.update(progress['checks'])
    checks['all_input_consumed']=progress['final'].get('tx')==e['input_words']
    samples=re.findall(r'^M441_DELAY channel=(\w+) count=(\d+) sum=(\d+)\s*$',log,re.M)
    wanted={f'axi_latency_w{i}_get_rdata_lat' for i in range(4)}|{'svr_latency_rx_get_transfer_lat'}
    channels={ch for ch,c,t in samples if int(c)>=4096 and 0<int(t)<=8*int(c)}
    checks['bounded_delays']=bool(samples) and all(0<=int(t)<=8*int(c) for _,c,t in samples)
    checks['nonzero_four_R_and_RX_delay']=wanted<=channels
    ars=[(int(i),int(a,16),int(l)+1,int(s),int(b)) for i,a,l,s,b in re.findall(r'^M441MAX_AR shard=(\d+) address=([0-9a-fA-F]+) len=(\d+) size=(\d+) burst=(\d+)\s*$',log,re.M)]
    expected=collections.Counter();chain=p['chain'];base=chain['staged_base_words']
    for d in chain['descriptors']:
        start=(int(d['encoded_u64'],16)&0xffffffff)-base
        count=chain['groups']*(d['rows_per_shard']//8)*(1+4*chain['bits'])
        expected.update(range(start,start+count))
    coverage=[]
    for i in range(4):
        rows_i=[x for x in ars if x[0]==i];covered=collections.Counter();hist=collections.Counter();valid=bool(rows_i)
        for _,a,l,s,b in rows_i:
            valid=valid and s==4 and b==1 and 1<=l<=64 and a%16==0 and (a&4095)+16*l<=4096
            if 1<=l<=64:covered.update(range(a//16,a//16+l))
            hist[l]+=1
        valid=valid and covered==expected and sum(l*c for l,c in hist.items())==e['weight_beats_per_shard'] and len(rows_i)==next((x['AR'] for x in m if x['shard']==i),-1)
        coverage.append(dict(shard=i,valid=valid,requests=len(rows_i),burst_histogram=dict(hist)))
    checks['exact_AR_address_coverage']=all(x['valid'] for x in coverage) and all(x[0] in range(4) for x in ars)
    if p['maximum_pressure']:
        splits={i:collections.Counter((a,l) for j,a,l,_,_ in ars if j==i) for i in range(4)}
        checks['W2_actual_4KiB_split_four_ports']=all(x[(252*16,4)]==10 and x[(256*16,5)]==10 for x in splits.values())
    return dict(accepted=all(checks.values()),checks=checks,errors=errors,
                details=dict(done=done,metrics=m,queues=q,accepted_overlap=o,coverage=coverage,progress=progress),
                output_sha256=hashlib.sha256(payload).hexdigest(),golden_sha256=hashlib.sha256(golden).hexdigest())


def collect(case,receipt,snapshot):
    p=json.loads(PREP.read_bytes());name=case['name'];folder=ROOT/case['path'];sim=folder/'verilog'
    for row in case['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    log=(sim/'pressure.log').read_text(encoding='utf-8-sig',errors='replace')
    data=sim/'pressure_result';errors=[];ports={}
    for field in ('rx_V_data_V','rx_V_last_V','rx_V_keep_V','rx_V_strb_V','ap_return'):
        try:ports[field]=read_tv(data/('rtl.m89x_runtime_kernel.autotvout_'+field+'.dat'))
        except (OSError,ValueError,AssertionError) as exc:ports[field]=[];errors.append(repr(exc))
    payload=b''.join(x.to_bytes(8,'little') for x in ports['rx_V_data_V'])
    good,uvm=evaluate(sim,log)
    v=parsed(case,receipt,log,payload,(folder/'golden.bin').read_bytes(),ports,good)
    ev=RUN/(name+'_RESULT.json')
    r=dict(status='PASS_M441_SUPPLEMENTAL_W2_W4_RTL' if v['accepted'] and not errors else 'FAIL_M441_SUPPLEMENTAL_W2_W4_RTL',
           case=name,bits=case['bits'],build_id=p['build_id'],preparation_sha256=sha(PREP),
           original_rc=receipt['original_rc'],gate_rc=receipt['gate_rc'],elapsed_s=receipt['elapsed_s'],
           checks=v['checks'],errors=errors,details=v['details'],output_sha256=v['output_sha256'],reference_sha256=v['golden_sha256'],
           snapshot_sha256=snapshot,full_real_numerical=case['full_real_numerical'],maximum_pressure=case['maximum_pressure'],
           protocol_zero_scale_only=not case['full_real_numerical'],uvm_evidence=uvm,board=False,performance=False,promoted=False,
           evidence=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in [sim/'pressure_exit.json',sim/'pressure.log',sim/'pressure.args',*sorted(data.glob('*.dat'))]])
    atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_simulation19_'+name,dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441补充仿真19/{name}（2026-10-10）\n\nSHA {sha(ev)}；{r["status"]}，Build0x4D343431，W{case["bits"]}原rc{receipt["original_rc"]}/gate{receipt["gate_rc"]}，完整输出及原参考SHA独立核对，固定有界延迟/背压/结束协议/FIFO以实际checks为准。零scale最大夹具仅协议；原数值PASS/RandomFAIL不改，0板端/请求性能/生产修改。')
    return r


def collect_timeout(receipt,snapshot):
    sim=ROOT/'tmp/m441_sim_coverage_19/timeout/verilog';log=(sim/'timeout.log').read_text(encoding='utf-8-sig',errors='replace')
    v=validate_timeout(receipt,log,bool(snapshot))
    v['checks']['failure_snapshot']='M441_BOUNDARY_TIMEOUT_SNAPSHOT ' in log
    r=dict(status='PASS_M441_SUPPLEMENTAL_W2_TIMEOUT' if all(v['checks'].values()) else 'FAIL_M441_SUPPLEMENTAL_W2_TIMEOUT',
           checks=v['checks'],original_rc=receipt['original_rc'],gate_rc=receipt['gate_rc'],snapshot_sha256=snapshot,
           preparation_sha256=sha(PREP),board=False,performance=False,
           evidence=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in [sim/'timeout.log',sim/'timeout_exit.json',sim/'timeout.args']])
    ev=RUN/'timeout_RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_simulation19_timeout',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441 W2同快照超时负例19（2026-10-10）\n\nSHA {sha(ev)}；{r["status"]}，实际start后200周期原工具rc{receipt["original_rc"]}/门禁rc{receipt["gate_rc"]}保留，不当数值/性能PASS；同新编译快照SHA绑定。')
    return r


def fault_checks():
    # Actual saved W4 pressure data, explicitly augmented only as a parser
    # component fixture. This does NOT prove new W2 or accepted-MAC overlap.
    src=ROOT/'tmp/m441_boundary_protocol_07';sim=src/'verilog'
    log=(sim/'max.log').read_text(encoding='utf-8-sig',errors='replace')
    log+=''.join(f'M441C19_OVERLAP shard={i} accepted=1\n' for i in range(4))
    receipt=json.loads((sim/'max_exit.json').read_bytes())
    ports={field:read_tv(sim/'max_result'/('rtl.m89x_runtime_kernel.autotvout_'+field+'.dat')) for field in ('rx_V_data_V','rx_V_last_V','rx_V_keep_V','rx_V_strb_V','ap_return')}
    payload=b''.join(x.to_bytes(8,'little') for x in ports['rx_V_data_V']);golden=(src/'golden.bin').read_bytes()
    case=dict(expected=dict(output_words=327680,output_bytes=2621440,weight_beats_per_shard=10880,mac_calls_per_shard=2560,descriptors=10,input_words=170),
              cycle_budget=4000000,maximum_pressure=False,
              chain=dict(groups=1,bits=4,staged_base_words=0,descriptors=[dict(encoded_u64='0x120000000000',rows_per_shard=512)]*10))
    assert parsed(case,receipt,log,payload,golden,ports,True)['accepted']
    bads=[('truncated_output',payload[:-8],log,ports,receipt,True),
          ('one_data_bit',bytes([payload[0]^1])+payload[1:],log,ports,receipt,True)]
    for field in ('rx_V_last_V','rx_V_keep_V','rx_V_strb_V','ap_return'):
        changed=dict(ports);changed[field]=list(ports[field]);changed[field][-1]^=1
        bads.append((field,payload,log,changed,receipt,True))
    for tag,old,new in [('lost_done','M441MAX_DONE','BROKEN_DONE'),('missing_overlap','M441C19_OVERLAP shard=3','BROKEN_OVERLAP shard=3'),
                        ('wrong_R',' R=10880 ',' R=10879 '),('wrong_FIFO','queue_final=0','queue_final=1'),
                        ('tail_not_128','valid_cycles=128','valid_cycles=127'),('missing_delay','M441_DELAY channel=axi_latency_w3_get_rdata_lat','MISSING_DELAY channel=w3'),
                        ('wrong_descriptor','descriptors=10','descriptors=9'),('missing_hold','M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED','MISSING_HOLD'),
                        ('wrong_address','address=ff0','address=ff1'),('extra_done','END_IMPOSSIBLE', 'END_IMPOSSIBLE')]:
        if tag=='extra_done':changed_log=log+'M441MAX_DONE cycles=867668 output=327680 tlast=1\n'
        else:assert old in log,old;changed_log=log.replace(old,new)
        bads.append((tag,payload,changed_log,ports,receipt,True))
    bads.extend([('tool_rc',payload,log,ports,dict(receipt,original_rc=1),True),
                 ('wall_budget',payload,log,ports,dict(receipt,software_wall_budget_exceeded=True),True),
                 ('uvm_error',payload,log,ports,receipt,False)])
    rejected=[]
    for name,raw,l,ps,rc,u in bads:
        assert not parsed(case,rc,l,raw,golden,ps,u)['accepted'],name
        rejected.append(name)
    ev=RUN/'COLLECTOR_CHECKS.json';r=dict(status='PASS_SAVED_EVIDENCE_COLLECTOR_COMPONENT19',rejected=rejected,
        fixture='Original saved W4 pressure07, synthetic accepted-overlap marker only for parser testing; not new RTL or W2 evidence',
        evidence_level='host component only',board=False,new_simulation_proven=False)
    atomic(ev,encoded(r),immutable=True)
    return sha(ev)
