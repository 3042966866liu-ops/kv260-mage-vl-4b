"""Repair only TB sink hold via handshake interposer; keep full fixture and DUT."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_vip_tail_component13 import TAIL

def main():
    prior=BASE/'runs/M441-boundary-rtl-06/RESULT.json';assert sha(prior)=='4f747b70e4ddb61b79d14dc782297b746d3396f2a9a1c51bca11060707a0eeb9'
    from m441_boundary_control06 import synchronized
    synchronized(prior,'FAIL_M441_PROTOCOL_MAX','latest_m441_boundary06_max')
    cp=BASE/'runs/M441-vip-tail-component-13/RESULT.json'
    synchronized(cp,'PASS_M441_ACTUAL_VIP_RELEASE_DIAGNOSIS_COMPONENT','latest_m441_vip_tail_component13')
    assert sha(cp)=='cc64a9e27602d4f581bf953545423a0417f3575aacb69e609c214c52348bfe1e'
    prep=BASE/'runs/M441-bounded-boundary-preparation-06/RESULT.json';p=json.loads(prep.read_bytes())
    old=ROOT/'tmp/m441_boundary_protocol_06';out=ROOT/'tmp/m441_boundary_protocol_07';assert not out.exists()
    tail=TAIL.replace('rx_clk','`D.ap_clk').replace('rx_ready','`D.rx_TREADY').replace('rx_valid','`D.rx_TVALID').replace('rx_last','`D.rx_TLAST')
    changed=[]
    for row in p['files']:
        source=ROOT/row['path'];assert sha(source)==row['sha256'];rel=source.relative_to(old);raw=source.read_bytes()
        if source.name=='m441_max_monitor.sv':
            s=raw.decode('utf-8-sig');start=s.index('// Shared VIP ready');end=s.rindex('endmodule')
            s=s[:start]+tail+'\n'+s[end:];s=s.replace('module m441_max_monitor;','module m441_max_monitor;\nbit tail_block=0;')
            assert 'force ' not in s and 'release ' not in s
            raw=s.encode()
        elif source.name=='sv_module_top.sv':
            s=raw.decode('utf-8-sig')
            a='assign apatb_m89x_runtime_kernel_top.rx_TREADY = svr_rx_if.ready;'
            b='assign svr_rx_if.valid = apatb_m89x_runtime_kernel_top.rx_TVALID;'
            assert s.count(a)==s.count(b)==1
            s=s.replace(a,a[:-1]+' && !m441_max_monitor.tail_block;').replace(b,b[:-1]+' && !m441_max_monitor.tail_block;')
            raw=s.encode()
        atomic(out/rel,raw,immutable=True)
        if sha(out/rel)!=row['sha256']:changed.append(rel.as_posix())
    assert set(changed)=={'verilog/m441_max_monitor.sv','verilog/svtb/sv_module_top.sv'}
    (out/'tv/rtldatafile').mkdir(parents=True)
    r=dict(p,status='PREPARED_M441_BOUNDED_BOUNDARY07',previous_preparation_sha256=sha(prep),old_FAIL_sha256=sha(prior),
        actual_VIP_component_sha256=sha(cp),changed_from06=changed,repair='TB handshake interposer gates DUT READY and VIP VALID together; never force/release receiver variable. Arithmetic/DUT/fixture/delay/budgets unchanged.',
        readiness='Frozen07 controller policy and prerequisites required',files=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q)) for q in sorted(out.rglob('*')) if q.is_file()])
    ev=BASE/'runs/M441-bounded-boundary-preparation-07/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_bounded_boundary_preparation07',dict(status=r['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
         f'## M441 有界压力测试入口修复07（2026-10-09）\n\nSHA {sha(ev)}；旧06 FAIL {sha(prior)}不改。实际原VIP复现release READY保留0并通过interposer对照 {sha(cp)}；只改测试台两根握手和尾停顿状态，不改DUT/最大输入/4M4h/随机范围。0工具/板端，下一步同级独立一次。')
    # Derive controller/collector, keeping strict combined predicates intact.
    c=(HERE/'m441_boundary_control06.py').read_text(encoding='utf-8-sig')
    for a,b in [('M441-bounded-boundary-preparation-06','M441-bounded-boundary-preparation-07'),('PREPARED_M441_BOUNDED_BOUNDARY06','PREPARED_M441_BOUNDED_BOUNDARY07'),('tmp/m441_boundary_protocol_06','tmp/m441_boundary_protocol_07'),('tmp/m441_boundary_timeout_06','tmp/m441_boundary_timeout_07'),('M441-boundary-compile-06','M441-boundary-compile-07'),('M441-boundary-rtl-06','M441-boundary-rtl-07'),('latest_m441_boundary06_','latest_m441_boundary07_'),('M441-boundary-control-preparation-06','M441-boundary-control-preparation-07'),('PREPARED_M441_BOUNDARY_CONTROL06','PREPARED_M441_BOUNDARY_CONTROL07'),('latest_m441_boundary_control06','latest_m441_boundary_control07'),('latest_m441_boundary_component10','latest_m441_vip_tail_component13'),('PASS_M441_BOUNDARY_ACTUAL_SV_COMPONENT_ONLY','PASS_M441_ACTUAL_VIP_RELEASE_DIAGNOSIS_COMPONENT'),('63063b52e228035a4fa908771e18e0e7d32b1ed6836005be3c79bb690efd541c',sha(cp))]:
        assert a in c,a;c=c.replace(a,b)
    atomic(HERE/'m441_boundary_control07.py',c.encode(),immutable=True)
    s=(HERE/'m441_collect_boundary06.py').read_text(encoding='utf-8-sig')
    for a,b in [('m441_boundary_control06','m441_boundary_control07'),('M441-boundary-control-preparation-06','M441-boundary-control-preparation-07'),('M441-boundary-compile-06','M441-boundary-compile-07'),('M441-boundary-rtl-06','M441-boundary-rtl-07'),('M441-boundary-timeout-06','M441-boundary-timeout-07'),('latest_m441_boundary06_','latest_m441_boundary07_')]:assert a in s,a;s=s.replace(a,b)
    # Make the original external stop explicit, rather than trusting launcher rc0.
    s=s.replace('2026-10-07','2026-10-09')
    atomic(HERE/'m441_collect_boundary07.py',s.encode(),immutable=True)
    compile(c,'control07','exec');compile(s,'collector07','exec')
    import m441_boundary_control07 as control
    control.verified_prep();refs=control.prerequisites()
    names=['m441_boundary_control07.py','m441_collect_boundary07.py','m441_boundary_evidence06.py','m441_protocol_evidence.py','m441_progress03.py','m357_uvm_log_evidence.py','m356_collect_rtl.py','m351_workflow.py','m441_supervisor04.py','m441_continue_offline.py','m441_vip_tail_component13.py','m441_prepare_boundary07.py']
    r=dict(status='PREPARED_M441_BOUNDARY_CONTROL07',prerequisites=refs,old_failed_level_sha256=sha(prior),preparation_sha256=sha(ev),
        files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in names],board=False,default_disabled=True,no_restart_old06=True)
    policy=BASE/'runs/M441-boundary-control-preparation-07/RESULT.json';atomic(policy,encoded(r),immutable=True)
    sync('latest_m441_boundary_control07',dict(status=r['status'],sha256=sha(policy),result=policy.relative_to(ROOT).as_posix(),board=False),
         f'## M441 修复后压力控制07（2026-10-09）\n\nSHA {sha(policy)}；绑定实际VIP组件13、原26收集破坏检查及同级旧FAIL。默认关闭，同4M/4h一次及完整327680输出/FIFO要求不降低；旧06不重启。编译结果三记录后才跑压力，非板端。')
    print(r['status'],sha(policy),flush=True)

if __name__=='__main__':main()
