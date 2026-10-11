"""Exercise actual collector predicates with explicit fake RTL evidence only."""
import copy
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m438_prepare import tv
from m441_protocol_evidence import validate_max, validate_timeout, native


def main():
    source=ROOT/'tmp/m441_max_protocol_01';prep=BASE/'runs/M441-max-protocol-preparation-01/RESULT.json'
    p=json.loads(prep.read_bytes());assert p['status']=='PREPARED_M441_MAXIMUM_PROTOCOL_NO_EXECUTION'
    fixture=ROOT/'tmp/m441_protocol_evidence_checks_01';assert not fixture.exists()
    prefix='rtl.m89x_runtime_kernel.autotvout_';n=p['expected']['output_words']
    golden=(source/'golden.bin').read_bytes();assert golden==bytes(2621440)
    for name,vals in [('rx_V_data_V',['0x0']*n),('rx_V_keep_V',['0xff']*n),('rx_V_strb_V',['0xff']*n),
                      ('rx_V_last_V',['0x0']*(n-1)+['0x1']),('ap_return',['0x4d343431'])]:tv(fixture/(prefix+name+'.dat'),vals)
    lines=['M441MAX_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000',
           'M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000',
           'M441MAX_HELD_VALID=100 STABLE_OUTPUT_CYCLES=99',
           'M441MAX_DONE cycles=800000 output=327680 tlast=1','RTL Simulation : 1 / 1']
    for i in range(4):
        lines.append(f'M441MAX_METRIC shard={i} active=1 mac_busy=1 mac_calls=2560 iterations=40960 AR=640 R=10880 return_gap=0 RSTALL=0 ARSTALL=10 AR_during_MAC=0 R_during_MAC=0 pending=0 bad_RLAST=0 bad_RRESP=0')
        lines.append(f'M441MAX_PROTOCOL shard={i} descriptors=10 FIFO_MAX=8192 queue_writes=10880 queue_reads=10880 queue_high=34 queue_full=100 queue_final=0 AR_STABLE=9')
        for _ in range(10):
            for address in range(0,1088,17):lines.append(f'M441MAX_AR shard={i} address={address*16:x} len=16 size=4 burst=1')
    log='\n'.join(lines)+'\n';receipt=dict(original_rc=0,gate_rc=0,software_wall_budget_exceeded=False)
    def accept(r,text,expected=golden):
        try:return validate_max(p,r,text,fixture,expected,source/'verilog')['accepted']
        except (KeyError,ValueError,OSError,OverflowError):return False
    assert accept(receipt,log)
    mutations=[('simulator_nonzero',dict(receipt,original_rc=1),log),
               ('gate_nonzero',dict(receipt,gate_rc=1),log),('wall_timeout',dict(receipt,software_wall_budget_exceeded=True),log),
               ('fatal_rc0',receipt,log+'Fatal: injected simulator fatal\n'),
               ('UVM_error',receipt,log+'UVM_ERROR fake [wrong] injected error\n'),
               ('echo_only_AR_hold',receipt,log.replace(lines[0],'## puts "'+lines[0]+'"')),
               ('echo_only_output_hold',receipt,log.replace(lines[1],'## puts "'+lines[1]+'"')),
               ('missing_done',receipt,log.replace(lines[3]+'\n','')),
               ('duplicate_done',receipt,log+lines[3]+'\n'),('incomplete_engine',receipt,log.replace('RTL Simulation : 1 / 1','RTL Simulation : 0 / 1')),
               ('wrong_MAC',receipt,log.replace('iterations=40960','iterations=40959',1)),
               ('pending_AR',receipt,log.replace('pending=0','pending=1',1)),
               ('bad_RLAST',receipt,log.replace('bad_RLAST=0','bad_RLAST=1',1)),
               ('lost_descriptor',receipt,log.replace('descriptors=10','descriptors=9',1)),
               ('no_actual_output_full',receipt,log.replace('FIFO_MAX=8192','FIFO_MAX=8191')),
               ('record_queue_overflow',receipt,log.replace('queue_high=34','queue_high=35',1)),
               ('record_queue_not_full',receipt,log.replace('queue_high=34','queue_high=33',1)),
               ('record_queue_not_drained',receipt,log.replace('queue_final=0','queue_final=1',1)),
               ('unstable_output_marker',receipt,log.replace('STABLE_OUTPUT_CYCLES=99','STABLE_OUTPUT_CYCLES=0')),
               ('no_AR_stability',receipt,log.replace('AR_STABLE=9','AR_STABLE=0')),
               ('missing_address',receipt,log.replace('M441MAX_AR shard=0 address=0 len=16 size=4 burst=1\n','',1)),
               ('duplicate_address',receipt,log+'M441MAX_AR shard=0 address=0 len=16 size=4 burst=1\n'),
               ('wrong_AR_shard',receipt,log.replace('M441MAX_AR shard=0','M441MAX_AR shard=4',1)),
               ('wrong_AR_size',receipt,log.replace('len=16 size=4','len=16 size=3',1)),
               ('partial_protocol_row',receipt,log.replace('queue_writes=10880 ','',1))]
    passed=[]
    for name,r,text in mutations:assert not accept(r,text),name;passed.append(name)
    assert not accept(receipt,log,bytes([1])+golden[1:]);passed.append('wrong_wire')
    timeout_log='M441MAX_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200\nFatal: M441MAX bounded timeout expired before ap_done\n'
    tr=dict(original_rc=0,gate_rc=1,timeout_observed=True,software_wall_budget_exceeded=False)
    assert validate_timeout(tr,timeout_log,True)['accepted']
    for name,r,text,snapshot in [('timeout_rc0_marked_PASS',dict(tr,gate_rc=0),timeout_log,True),
                                 ('timeout_without_fatal',tr,timeout_log.split('Fatal:')[0],True),
                                 ('timeout_echo_only',tr,'## puts "'+timeout_log.splitlines()[0]+'"\n'+timeout_log.splitlines()[1]+'\n',True),
                                 ('timeout_wrong_snapshot',tr,timeout_log,False),
                                 ('timeout_unexpected_done',tr,timeout_log+'M441MAX_DONE cycles=200 output=1 tlast=1\n',True)]:
        assert not validate_timeout(r,text,snapshot)['accepted'],name;passed.append(name)
    assert native(log,lines[0]) and not native('## puts "'+lines[0]+'"\n',lines[0])
    result=dict(status='PASS_M441_PROTOCOL_COLLECTOR_FAULT_CHECKS_ONLY',positive_max_fixture=True,positive_expected_timeout_fixture=True,
                rejected_cases=passed,fake_RTL_log_and_output=True,actual_predicates_executed=True,
                source_sha256=sha(HERE/'m441_protocol_evidence.py'),test_sha256=sha(HERE/'m441_protocol_support_checks.py'),
                preparation_sha256=sha(prep),RTL_simulated=False,board=False,performance=False,promoted=False)
    dest=BASE/'runs/M441-protocol-evidence-support-checks-01/RESULT.json';atomic(dest,encoded(result),immutable=True)
    sync('latest_m441_protocol_collector_checks',dict(status=result['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),
         f'## M441 协议收集故障检查（2026-10-07）\n\nSHA {sha(dest)}；实际新验收函数完整2.5MiB明确fake输出/日志及200周期预期失败夹具，{len(passed)}项损坏/echo/fatal0/地址缺重/两级FIFO/未排空/错snapshot拒绝。仅收集组件，不证明新DUT协议或性能；当前A/B长链保持，原M439 FAIL不改。')
    print(result['status'],sha(dest),len(passed))


if __name__=='__main__':main()
