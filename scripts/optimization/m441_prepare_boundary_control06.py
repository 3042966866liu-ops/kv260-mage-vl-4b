"""Derive independent pressure controller/collector from reviewed local tools."""
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import json

REFS={
 'latest_m441_full_numeric_csim':('PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM','a2b19009642bc956a3a18cd01a09fb3d65bb187ea1672ce2a4bd853bb1256c46'),
 'latest_m441_long_A_gate_up_zero02':('PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL','3116961c34d729e37f32a79b4e914c1e16d4a978c988e41ddc51814298fd16f4'),
 'latest_m441_long_B_gate_up_zero02':('PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL','74bafec070d975c0ef967205f7b3232e49efd75a5436f6db2223a2142220647c'),
 'latest_m441_W4_zero05_result':('PASS_M441_W4_MLPDOWN_FULL_ZERO04','3db32e9edcd326c35247fc0b487f1ba33488b73275361aa7fa2126c0f90b0e54'),
 'latest_m441_boundary_component10':('PASS_M441_BOUNDARY_ACTUAL_SV_COMPONENT_ONLY','63063b52e228035a4fa908771e18e0e7d32b1ed6836005be3c79bb690efd541c'),
 'latest_m441_boundary_collector_checks06':('PASS_M441_BOUNDED_BOUNDARY_COLLECTOR_COMPONENT_ONLY','a35ae4d4187f747a10317c944102ac67b3320fc024c0009ba6fa424e5405ae0b'),
}

def replace(s,a,b):
    assert a in s,a
    return s.replace(a,b)

def main():
    c=(HERE/'m441_protocol_control.py').read_text(encoding='utf-8-sig')
    c=replace(c,'from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha','from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha\nfrom m441_supervisor04 import boot,process,classify,log_snapshot')
    c=replace(c,"M441-max-protocol-preparation-01","M441-bounded-boundary-preparation-06")
    c=replace(c,'tmp/m441_max_protocol_01','tmp/m441_boundary_protocol_06')
    c=replace(c,'tmp/m441_timeout_negative_01','tmp/m441_boundary_timeout_06')
    start=c.index('def prerequisites():');end=c.index('\n\ndef verified_prep',start)
    body='def prerequisites():\n    refs='+repr(REFS)+'\n    result={}\n    b=json.loads((ROOT/"deployment/mage_vl4b/BOARD_GATE_RESULT.json").read_bytes())\n    for key,(status,digest) in refs.items():\n        path=ROOT/b[key]["result"];r=synchronized(path,status,key)\n        assert sha(path)==digest\n        result[key]=digest\n    assert len(json.loads((ROOT/b["latest_m441_boundary_collector_checks06"]["result"]).read_bytes())["rejected_cases"])==26\n    return result\n'
    c=c[:start]+body+c[end:]
    for a,b in [('PREPARED_M441_MAXIMUM_PROTOCOL_NO_EXECUTION','PREPARED_M441_BOUNDED_BOUNDARY06'),('M441-max-protocol-compile-01','M441-boundary-compile-06'),('M441-max-protocol-rtl-01','M441-boundary-rtl-06'),('PASS_M441_MAXIMUM_PROTOCOL_COMPILED','PASS_M441_BOUNDARY_COMPILED'),('PASS_M441_MAXIMUM_PROTOCOL_RTL','PASS_M441_BOUNDARY_RTL'),('latest_m441_max_protocol_','latest_m441_boundary06_'),('M441-protocol-control-preparation-01','M441-boundary-control-preparation-06'),('PREPARED_M441_PROTOCOL_CONTROL_COLLECTOR_GUARDS','PREPARED_M441_BOUNDARY_CONTROL06'),('latest_m441_protocol_control_preparation','latest_m441_boundary_control06'),("'-debug','typical'","'-debug','typical','-v','2'"),('-testplusarg M438_ZERO_EXTRA_LATENCY\\n',''),('budget=8*3600','budget=4*3600')]:c=replace(c,a,b)
    anchor='wall=False;started=time.monotonic();rc=None'
    c=replace(c,anchor,anchor+';start_boot=boot();next_live=0')
    anchor="print('M441_PROTOCOL_LOCAL_STARTED '+stem+' pid='+str(proc.pid),flush=True)"
    c=replace(c,anchor,anchor+'\n        identity=process(proc.pid);born=identity.get("creation_FILETIME")')
    c=replace(c,'while proc.poll() is None:\n            if time.monotonic()-started>budget:wall=True;break',
        'while proc.poll() is None:\n            if time.monotonic()>=next_live:\n                state=process(proc.pid,born);current=boot()\n                atomic(sim/(stem+"_LIVE.json"),encoded(dict(status=classify(start_boot,current,state),process=state,boot=current,start_boot=start_boot,elapsed_s=time.monotonic()-started,log=log_snapshot(sim/(stem+".log")))))\n                next_live=time.monotonic()+30\n            if time.monotonic()-started>budget:wall=True;break')
    c=replace(c,'process_killed=False,','process_killed=False,start_boot=start_boot,process_creation_FILETIME=born,')
    atomic(HERE/'m441_boundary_control06.py',c.encode('utf-8'),immutable=True)
    s=(HERE/'m441_collect_max_protocol.py').read_text(encoding='utf-8-sig')
    for a,b in [('from m441_protocol_evidence import validate_max,validate_timeout,clean_engine','from m441_protocol_evidence import clean_engine\nfrom m441_boundary_evidence06 import validate_boundary as validate_max,validate_boundary_timeout as validate_timeout'),('from m441_protocol_control import','from m441_boundary_control06 import'),('M441-protocol-control-preparation-01','M441-boundary-control-preparation-06'),('PASS_M441_MAXIMUM_PROTOCOL_COMPILED','PASS_M441_BOUNDARY_COMPILED'),('PASS_M441_MAXIMUM_PROTOCOL_RTL','PASS_M441_BOUNDARY_RTL'),('PASS_M441_EXPECTED_TIMEOUT_NEGATIVE','PASS_M441_BOUNDARY_EXPECTED_TIMEOUT'),('M441-max-protocol-compile-01','M441-boundary-compile-06'),('M441-max-protocol-rtl-01','M441-boundary-rtl-06'),('M441-timeout-negative-01','M441-boundary-timeout-06'),('latest_m441_max_protocol_','latest_m441_boundary06_')]:s=replace(s,a,b)
    atomic(HERE/'m441_collect_boundary06.py',s.encode('utf-8'),immutable=True)
    # Actual source bindings/default-off contract checked before freezing policy.
    import m441_boundary_control06 as control
    control.verified_prep();refs=control.prerequisites()
    assert 'M438_ZERO_EXTRA_LATENCY' not in c and 'len(r[\'comparisons\'])==6' not in c
    assert "assert a.run" in c and "budget=4*3600" in c and 'proc.kill' not in c and 'proc.terminate' not in c
    compile(c,'boundary_control06','exec');compile(s,'collect_boundary06','exec')
    names=['m441_boundary_control06.py','m441_collect_boundary06.py','m441_boundary_evidence06.py','m441_protocol_evidence.py','m441_progress03.py','m357_uvm_log_evidence.py','m356_collect_rtl.py','m351_workflow.py','m441_protocol_control.py','m441_supervisor04.py','m441_continue_offline.py','m441_boundary_checks06.py','m441_prepare_boundary_control06.py']
    r=dict(status='PREPARED_M441_BOUNDARY_CONTROL06',prerequisites=refs,source_guards=dict(default_disabled=True,no_zero_latency_override=True,fixed_4h_once=True,old_six_random_not_claimed=True,live_30s_boot_PID_identity=True,no_kill=True),
        files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in names],board=False,compiled=False,simulated=False)
    ev=BASE/'runs/M441-boundary-control-preparation-06/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_boundary_control06',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441 独立有界压力控制06（2026-10-09）\n\nSHA {sha(ev)}；前级同SHA三记录、26负例与实际SV组件绑定；默认关闭，无Zero override，固定4M/4h一次，30秒保存主机/PID身份及进度，不kill；原六Random不声称完成。下一步编译后严格收集再启动压力。')
    print(r['status'],sha(ev),flush=True)

if __name__=='__main__':main()
