"""Saved-only maximum protocol/timeout adjudication; no simulator commands."""
import argparse,collections,hashlib,json,re
from pathlib import Path
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m356_collect_rtl import read_tv
from m357_uvm_log_evidence import evaluate

ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('compile','max','timeout'));a=ap.parse_args()
prep=BASE/'runs/M439-max-protocol-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
assert sha(Path(__file__))==p['collector_sha256']
out=ROOT/'tmp/m439_max_protocol_01';sim=ROOT/'tmp/m439_timeout_negative_01/verilog' if a.mode=='timeout' else out/'verilog'
receipt=sim/(a.mode+'_exit.json');saved=json.loads(receipt.read_bytes());rc=saved['original_rc']
logpath=sim/(a.mode+'_console.log' if a.mode=='compile' else a.mode+'.log')
log=logpath.read_text(encoding='utf-8-sig',errors='replace');errors=[];detail={}
checks=dict(receipt_identity=saved['preparation_sha256']==sha(prep),wall_budget=not saved['software_wall_budget_exceeded'])
for row in p['files']:
    if sha(ROOT/row['path'])!=row['sha256']:errors.append('Frozen input changed: '+row['path'])
if a.mode=='compile':
    checks.update(original_rc=rc==0 and saved['gate_rc']==0,snapshot='Built simulation snapshot m439_max_trace' in log,no_error='ERROR:' not in log)
    good='PASS_M439_MAXIMUM_PROTOCOL_COMPILED';bad='FAIL_M439_MAXIMUM_PROTOCOL_COMPILE'
elif a.mode=='timeout':
    prerequisite=json.loads((sim.parent/'PREREQUISITE.json').read_bytes())
    checks.update(expected_marker='M439_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200' in log,
                  actual_fatal='M439 bounded timeout expired before ap_done' in log,
                  fail_closed=saved['gate_rc']==1 and saved['timeout_observed'],
                  no_ap_done='M439_DONE' not in log,no_complete_transaction='RTL Simulation : 1 / 1' not in log,
                  engine_initialized='necessary license' not in log and 'simulation failed to initialize' not in log.lower(),
                  same_snapshot=prerequisite['same_compiled_candidate_snapshot'] and prerequisite['source_preparation_sha256']==sha(prep))
    detail.update(prerequisite=prerequisite,budget_cycles_after_actual_start=200,negative_only=True)
    good='PASS_M439_EXPECTED_TIMEOUT_NEGATIVE';bad='FAIL_M439_TIMEOUT_NEGATIVE'
else:
    tvdir=sim/'max_result';prefix='rtl.m89x_runtime_kernel.autotvout_'
    def read(name):
        try:return read_tv(tvdir/(prefix+name+'.dat'))
        except Exception as e:errors.append(name+':'+repr(e));return []
    raw=b''.join(v.to_bytes(8,'little') for v in read('rx_V_data_V'))
    golden=(out/'golden.bin').read_bytes();n=p['expected']['output_words']
    clean,uvm=evaluate(sim,log)
    checks.update(original_rc=rc==0 and saved['gate_rc']==0,complete_wire_exact=raw==golden and len(raw)==2621440,
                  Build=read('ap_return')==[0x4d343339],TLAST=read('rx_V_last_V')==[0]*(n-1)+[1],
                  keep=read('rx_V_keep_V')==[255]*n,strb=read('rx_V_strb_V')==[255]*n,
                  uvm_visible_no_error=clean,engine_complete='RTL Simulation : 1 / 1' in log and not re.search(r'ERROR:|Fatal:|failed to start|necessary license',log),
                  shared_address_hold='M439_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000' in log,
                  shared_output_hold='M439_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000' in log)
    done=re.findall(r'M439_DONE cycles=(\d+) output=(\d+) tlast=(\d+)',log)
    checks['done_once']=len(done)==1 and 0<int(done[0][0])<=p['cycle_budget'] and done[0][1:]==('327680','1')
    metrics=[{k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',s)} for s in re.findall(r'M439_METRIC[^\r\n]+',log)]
    protocols=[dict(shard=int(i),descriptors=int(d),FIFO_MAX=int(f)) for i,d,f in re.findall(r'M439_MAX_PROTOCOL shard=(\d+) descriptors=(\d+) FIFO_MAX=(\d+)',log)]
    checks['four_shards']=len(metrics)==4 and sorted(x['shard'] for x in metrics)==[0,1,2,3]
    checks['MAC_operations']=len(metrics)==4 and all(x['mac_calls']==2560 and x['iterations']==40960 for x in metrics)
    checks['read_protocol']=len(metrics)==4 and all(x['R']==10880 and x['pending']==x['bad_RLAST']==x['bad_RRESP']==0 for x in metrics)
    checks['all_descriptors']=len(protocols)==4 and sorted(x['shard'] for x in protocols)==[0,1,2,3] and all(x['descriptors']==10 for x in protocols)
    checks['actual_maximum_FIFO']=len(protocols)==4 and all(0<=x['FIFO_MAX']<=8192 for x in protocols) and any(x['FIFO_MAX']==8192 for x in protocols)
    held=re.findall(r'M439_MAX_HELD_VALID=(\d+)',log)
    checks['actual_held_valid']=len(held)==1 and int(held[0])>0
    checks['actual_address_backpressure']=any(x['shard']==0 and x['ARSTALL']>0 for x in metrics)
    ars=[dict(shard=int(i),address=int(addr,16),length=int(length)+1,size=int(size),burst=int(burst)) for i,addr,length,size,burst in re.findall(r'M439_AR shard=(\d+) address=([0-9a-fA-F]+) len=(\d+) size=(\d+) burst=(\d+)',log)]
    coverage=[]
    for i in range(4):
        rows=[x for x in ars if x['shard']==i];words=collections.Counter();hist=collections.Counter()
        valid=bool(rows)
        for x in rows:
            valid=valid and x['size']==4 and x['burst']==1 and 1<=x['length']<=64 and x['address']%16==0 and (x['address']&4095)+16*x['length']<=4096
            for j in range(x['length']):words[x['address']//16+j]+=1
            hist[x['length']]+=1
        valid=valid and words==collections.Counter({j:10 for j in range(1088)})
        valid=valid and len(rows)==next((x['AR'] for x in metrics if x['shard']==i),-1)
        coverage.append(dict(shard=i,requests=len(rows),burst_histogram=dict(hist),all1088_words_read_exactly10_times=valid))
    checks['address_coverage']=all(x['all1088_words_read_exactly10_times'] for x in coverage)
    detail.update(done=done,metrics=metrics,protocols=protocols,coverage=coverage,addresses=ars,held_valid_cycles=held,uvm_evidence=uvm,
                  wire_sha256=hashlib.sha256(raw).hexdigest(),reference_sha256=sha(out/'golden.bin'),output_bytes=len(raw))
    good='PASS_M439_MAXIMUM_PROTOCOL_RTL';bad='FAIL_M439_MAXIMUM_PROTOCOL_RTL'
ok=all(checks.values()) and not errors
r=dict(status=good if ok else bad,build_id='0x4D343339',checks=checks,errors=errors,original_rc=rc,gate_rc=saved['gate_rc'],
       preparation_sha256=sha(prep),details=detail,board=False,promotion=False,
       scope='Same-version maximum protocol fixture or expected timeout negative; zero-scale protocol output does not replace real-record numerical evidence.',
       evidence=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in [receipt,logpath,sim/(a.mode+'_console.log'),sim/(a.mode+'.args')] if x.exists()])
if a.mode=='max':
    r['evidence'] += [dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in sorted((sim/'max_result').glob('*.dat'))]
name={'compile':'M439-max-protocol-compile-01','max':'M439-max-protocol-rtl-01','timeout':'M439-timeout-negative-01'}[a.mode]
ev=BASE/'runs'/name/'RESULT.json';atomic(ev,encoded(r),immutable=True)
sync('latest_m439_protocol_'+a.mode,dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
     '## M439 协议 '+a.mode+' 闭合（2026-10-07）\n\nSHA '+sha(ev)+'；'+r['status']+'，原rc'+str(rc)+'、gate rc'+str(saved['gate_rc'])+'。只读回收保存证据，不重跑；0板端/晋级，原真实数值与M437证据保留。失败仅本级调查，不构建整壳。')
print(r['status'],sha(ev));print(json.dumps(checks,indent=2))
if not ok:raise SystemExit(1)
if a.mode in ('compile','max'):atomic(sim/(a.mode+'_validated.json'),encoded(dict(status=r['status'],raw_sha256=sha(ev))),immutable=True)
