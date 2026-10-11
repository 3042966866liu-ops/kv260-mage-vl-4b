"""Actual combined collector checks on explicitly fake full-size saved evidence."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_boundary_evidence06 import validate_boundary,validate_boundary_timeout


def main():
    ev=BASE/'runs/M441-boundary-collector-checks-06/RESULT.json';assert not ev.exists()
    prep=BASE/'runs/M441-bounded-boundary-preparation-04/RESULT.json';p=json.loads(prep.read_bytes())
    p['expected']['weight_beats_per_shard']=10880
    source=ROOT/'tmp/m441_boundary_protocol_05';fixture=ROOT/'tmp/m441_protocol_evidence_checks_02'
    golden=(source/'golden.bin').read_bytes();assert len(golden)==2621440 and golden==bytes(len(golden))
    lines=['M441MAX_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000','M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000',
        'M441MAX_HELD_VALID=100 STABLE_OUTPUT_CYCLES=99','M441MAX_DONE cycles=800001 output=327680 tlast=1','RTL Simulation : 1 / 1',
        'M441_BOUNDARY_LAST_HOLD valid_cycles=128 accepted_before=327679']
    bursts=[]
    for record in range(0,1088,17):
        address=record;remaining=17
        while remaining:
            n=min(remaining,256-address%256);bursts.append((address,n));address+=n;remaining-=n
    for i in range(4):
        lines += [f'M441MAX_METRIC shard={i} active=1 mac_busy=1 mac_calls=2560 iterations=40960 AR=680 R=10880 return_gap=100 RSTALL=0 ARSTALL=10 AR_during_MAC=100 R_during_MAC=100 pending=0 bad_RLAST=0 bad_RRESP=0',
                  f'M441MAX_PROTOCOL shard={i} descriptors=10 FIFO_MAX=8192 queue_writes=10880 queue_reads=10880 queue_high=34 queue_full=100 queue_final=0 AR_STABLE=9']
        for _ in range(10):
            for a,n in bursts:lines.append(f'M441MAX_AR shard={i} address={a*16:x} len={n-1} size=4 burst=1')
    for c,v,term in [(10000,0,0),(800001,327680,1)]:
        lines.append(f'M441_PROGRESS cycle={c} output={v} tx=10 rx_stall=200 tx_stall=0 ctrl=30 stagnant=0 terminal={term}')
        for i in range(4):
            a=0 if term==0 else 680;r=0 if term==0 else 10880
            lines.append(f'M441_PORT_PROGRESS cycle={c} shard={i} AR={a} R={r} pending=0 gap=100 ARSTALL=10 RSTALL=0 MAC={0 if term==0 else 2560} iter={0 if term==0 else 40960} qwrite={r} qread={r} qcount=0 qhigh=34 qfull=100 live=0')
    channels=[f'axi_latency_w{i}_get_rdata_lat' for i in range(4)]+['svr_latency_rx_get_transfer_lat']
    for ch in channels:lines.append(f'M441_DELAY channel={ch} count=4096 sum=4096')
    log='\n'.join(lines)+'\n';receipt=dict(original_rc=0,gate_rc=0,software_wall_budget_exceeded=False)
    def accepted(text=log,r=receipt):
        try:return validate_boundary(p,r,text,fixture,golden,source/'verilog')['accepted']
        except (KeyError,ValueError,OSError,OverflowError):return False
    assert accepted()
    bad=[('tail_hold_missing',log.replace(lines[5]+'\n','')),('tail_hold_echo',log.replace(lines[5],'## puts "'+lines[5]+'"')),
         ('tail_hold127',log.replace('valid_cycles=128','valid_cycles=127')),('tail_hold_wrong_index',log.replace('accepted_before=327679','accepted_before=327678')),
         ('tail_hold_duplicate',log+lines[5]+'\n'),('random_missing_all', '\n'.join(x for x in lines if not x.startswith('M441_DELAY'))+'\n'),
         ('random_missing_port3',log.replace('M441_DELAY channel=axi_latency_w3_get_rdata_lat count=4096 sum=4096\n','')),
         ('random_zero',log.replace('sum=4096','sum=0')),('random_outside8',log.replace('sum=4096','sum=32769')),
         ('progress_missing', '\n'.join(x for x in lines if not x.startswith('M441_PROGRESS'))+'\n'),
         ('progress_partial_port',log.replace('qread=10880 ','',1)),('progress_terminal_bad',log.replace('terminal=1','terminal=2')),
         ('progress_stall',log.replace('stagnant=0','stagnant=1000000',1)),('fatal_zero_rc',log+'Fatal: injected\n'),
         ('output_fifo_not_full',log.replace('FIFO_MAX=8192','FIFO_MAX=8191')),
         ('queue_not_drained',log.replace('queue_final=0','queue_final=1',1)),('descriptor_missing',log.replace('descriptors=10','descriptors=9',1)),
         ('crossing_burst',log.replace('address=ff0 len=0','address=ff0 len=16',1)),('split_missing',log.replace('M441MAX_AR shard=0 address=1000 len=15 size=4 burst=1\n','',1)),
         ('wrong_count',log.replace('output=327680','output=327679'))]
    passed=[]
    for n,t in bad:assert not accepted(t),n;passed.append(n)
    for n,r in [('nonzero_tool',dict(receipt,original_rc=1)),('nonzero_gate',dict(receipt,gate_rc=1)),('wall_budget',dict(receipt,software_wall_budget_exceeded=True))]:
        assert not accepted(r=r),n;passed.append(n)
    timeout='M441_BOUNDARY_TIMEOUT_SNAPSHOT requested0=0 received0=0 output_stalls=0\nM441MAX_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200\nFatal: M441MAX bounded timeout expired before ap_done\n'
    tr=dict(original_rc=0,gate_rc=1,timeout_observed=True,software_wall_budget_exceeded=False)
    assert validate_boundary_timeout(tr,timeout,True)['accepted']
    for n,t,s in [('missing_timeout_snapshot',timeout.split('\n',1)[1],True),('timeout_wrong_snapshot',timeout,False),('timeout_no_fatal',timeout.split('Fatal:')[0],True)]:
        assert not validate_boundary_timeout(tr,t,s)['accepted'];passed.append(n)
    r=dict(status='PASS_M441_BOUNDED_BOUNDARY_COLLECTOR_COMPONENT_ONLY',fake_full_size_RTL_evidence=True,positive_boundary=True,positive_expected_timeout=True,
        rejected_cases=passed,actual_combined_predicates_executed=True,board=False,RTL_simulated=False,performance=False,
        files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in ['m441_boundary_checks06.py','m441_boundary_evidence06.py','m441_protocol_evidence.py','m441_progress03.py','m357_uvm_log_evidence.py','m356_collect_rtl.py']])
    atomic(ev,encoded(r),immutable=True);sync('latest_m441_boundary_collector_checks06',dict(status=r['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
        f'## M441 有界边界收集组件06（2026-10-09）\n\nSHA {sha(ev)}；完整2.5MiB明确fake保存证据经实际组合验收函数通过，{len(passed)}项尾停顿/随机范围/四端口/进度/FIFO/descriptor/跨4KiB/原rc/timeout破坏拒绝。仅收集组件，0实际DUT/板端；组件同SHA后才可运行独立压力。')
    print(r['status'],sha(ev),len(passed),flush=True)


if __name__=='__main__':main()
