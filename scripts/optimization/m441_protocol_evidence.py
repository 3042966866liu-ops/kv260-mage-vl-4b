"""Pure saved-evidence predicates shared by protocol collector and fault checks."""
import collections
import re
from m356_collect_rtl import read_tv
from m357_uvm_log_evidence import evaluate


def native(log,marker):return bool(re.search(r'^'+re.escape(marker)+r'\s*$',log,re.M))


def clean_engine(log):
    return not re.search(r'(?mi)^\s*(?:ERROR:|Fatal:|FATAL:)|failed to start|necessary license|simulation failed to initialize',log)


def validate_max(p,receipt,log,data,golden,source_directory):
    n=p['expected']['output_words'];errors=[]
    prefix='rtl.m89x_runtime_kernel.autotvout_'
    def read(name):
        try:return read_tv(data/(prefix+name+'.dat'))
        except Exception as exc:errors.append(name+':'+repr(exc));return []
    raw=b''.join(v.to_bytes(8,'little') for v in read('rx_V_data_V'))
    clean,uvm=evaluate(source_directory,log)
    checks=dict(original_rc=receipt['original_rc']==0 and receipt['gate_rc']==0,
                wall_budget=not receipt['software_wall_budget_exceeded'],
                wire=raw==golden and len(raw)==p['expected']['output_bytes'],Build=read('ap_return')==[int(p['build_id'],16)],
                TLAST=read('rx_V_last_V')==[0]*(n-1)+[1],keep=read('rx_V_keep_V')==[255]*n,strb=read('rx_V_strb_V')==[255]*n,
                uvm_visible_no_error=clean,engine_complete='RTL Simulation : 1 / 1' in log and clean_engine(log),
                shared_AR_hold=native(log,'M441MAX_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000'),
                shared_output_hold=native(log,'M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000'))
    def rows(prefix):return [{k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',s)} for s in re.findall(r'^'+prefix+r'[^\r\n]*$',log,re.M)]
    metrics=rows('M441MAX_METRIC');protocol=rows('M441MAX_PROTOCOL')
    done=re.findall(r'^M441MAX_DONE cycles=(\d+) output=(\d+) tlast=(\d+)\s*$',log,re.M)
    checks['done_once']=len(done)==1 and 0<int(done[0][0])<=p['virtual_cycle_budget'] and done[0][1:]==(str(n),'1')
    checks['four_shards']=len(metrics)==len(protocol)==4 and sorted(x['shard'] for x in metrics)==sorted(x['shard'] for x in protocol)==[0,1,2,3]
    checks['MAC']=len(metrics)==4 and all(x['mac_calls']==2560 and x['iterations']==40960 for x in metrics)
    checks['read_protocol']=len(metrics)==4 and all(x['R']==10880 and x['pending']==x['bad_RLAST']==x['bad_RRESP']==0 for x in metrics)
    checks['descriptors']=len(protocol)==4 and all(x['descriptors']==10 for x in protocol)
    checks['FIFO8192']=len(protocol)==4 and all(0<=x['FIFO_MAX']<=8192 for x in protocol) and any(x['FIFO_MAX']==8192 for x in protocol)
    checks['FIFO34']=len(protocol)==4 and all(x['queue_writes']==x['queue_reads']==10880 and x['queue_high']==34 and x['queue_full']>0 and x['queue_final']==0 for x in protocol)
    held=re.findall(r'^M441MAX_HELD_VALID=(\d+) STABLE_OUTPUT_CYCLES=(\d+)\s*$',log,re.M)
    checks['stalled_output_stable']=len(held)==1 and all(int(v)>0 for v in held[0])
    checks['stalled_AR_stable']=len(protocol)==4 and any(x['shard']==0 and x['AR_STABLE']>0 for x in protocol) and any(x['shard']==0 and x['ARSTALL']>0 for x in metrics)
    ars=[dict(shard=int(i),address=int(addr,16),length=int(length)+1,size=int(size),burst=int(burst)) for i,addr,length,size,burst in re.findall(r'^M441MAX_AR shard=(\d+) address=([0-9a-fA-F]+) len=(\d+) size=(\d+) burst=(\d+)\s*$',log,re.M)]
    checks['address_shards_valid']=all(x['shard'] in range(4) for x in ars)
    coverage=[]
    for i in range(4):
        transactions=[x for x in ars if x['shard']==i];words=collections.Counter();hist=collections.Counter();valid=bool(transactions)
        for x in transactions:
            valid=valid and x['size']==4 and x['burst']==1 and 1<=x['length']<=64 and x['address']%16==0 and (x['address']&4095)+16*x['length']<=4096
            if 1<=x['length']<=256:
                for j in range(x['length']):words[x['address']//16+j]+=1
            hist[x['length']]+=1
        valid=valid and words==collections.Counter({j:10 for j in range(1088)}) and len(transactions)==next((x['AR'] for x in metrics if x['shard']==i),-1)
        coverage.append(dict(shard=i,requests=len(transactions),burst_histogram=dict(hist),valid=valid))
    checks['full_address_coverage']=all(x['valid'] for x in coverage)
    return dict(checks=checks,errors=errors,details=dict(done=done,metrics=metrics,protocol=protocol,held=held,coverage=coverage,uvm_evidence=uvm),
                output_bytes=len(raw),accepted=all(checks.values()) and not errors)


def validate_timeout(receipt,log,same_snapshot):
    checks=dict(expected_marker=native(log,'M441MAX_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200'),
                actual_fatal=bool(re.search(r'(?m)^\s*(?:Fatal:|FATAL:)[^\r\n]*M441MAX bounded timeout expired before ap_done',log)),
                original_gate_rejected=receipt['gate_rc']==1 and receipt['timeout_observed'],
                within_wall=not receipt['software_wall_budget_exceeded'],
                no_done=not re.search(r'^M441MAX_DONE\b',log,re.M),no_complete='RTL Simulation : 1 / 1' not in log,
                initialized='necessary license' not in log and 'failed to initialize' not in log.lower(),same_snapshot=same_snapshot)
    return dict(checks=checks,accepted=all(checks.values()),scope='Expected 200-cycle failure after actual start, not numerical or performance PASS')
