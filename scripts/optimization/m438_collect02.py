"""Saved-only: direct internal ap_return is undriven; AXI-Lite TV remains strict."""
import sys,re,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    source=HERE/'m438_collect.py';sim=ROOT/'tmp/m438_weight_wait_03/verilog'
    ev=BASE/'runs/M438-return-observation-repair-01/RESULT.json'
    if not ev.exists():
        dut=(sim/'m89x_runtime_kernel.v').read_text(encoding='utf-8')
        assert 'wire   [31:0] ap_return;' in dut and not re.search(r'(?:assign\s+|\b)ap_return\s*(?:=|<=)',dut)
        from m356_collect_rtl import read_tv
        actual=read_tv(sim/'m438_random_result/rtl.m89x_runtime_kernel.autotvout_ap_return.dat')
        assert actual==[0x4d333537] and actual!=[0x4d395832]
        log=(sim/'m438_random_xsim.log').read_text(encoding='utf-8-sig',errors='replace')
        row=re.findall(r'M438_DONE cycles=(\d+) output=(\d+) tlast=(\d+) return=(\w+)',log)
        assert len(row)==1 and row[0][3]=='zzzzzzzz'
        r=dict(status='PREPARED_SAVED_ONLY_RETURN_OBSERVATION_REPAIR',board=False,dut_changed=False,simulation_rerun=False,
          collector_sha256=sha(source),original_log_sha256=sha(sim/'m438_random_xsim.log'),actual_AXI_Lite_return=actual,
          undriven_internal_print=row[0][3],AXI_Lite_TV_return_check_retained=True,
          rationale='Generated kernel has unused undriven internal ap_return wire. New monitor text is unproven for return; strict existing generated AXI-Lite TV is actual observed return. Only parse completed-cycle summary independently; full TV return still rejects wrong Build.')
        atomic(ev,encoded(r),immutable=True)
        sync('latest_m438_return_observation_repair',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
          f'## M438 返回值观察只读修正（2026-10-07）\n\nSHA {sha(ev)}；Random模拟rc0已保存，新增print的内部未驱动ap_return显示z，实际原AXI-Lite TV为0x4D333537。原collector尚未执行；02只分离周期汇总与不可用print字段，原TV完整返回值仍严格核对及错Build拒绝，不重跑仿真、无板端。')
    r=json.loads(ev.read_bytes());assert sha(source)==r['collector_sha256'] and sha(sim/'m438_random_xsim.log')==r['original_log_sha256']
    s=source.read_text(encoding='utf-8')
    s=s.replace('return=([0-9a-fA-F]+)', 'return=([0-9a-fA-FzZ]+)')
    s=s.replace(' and int(ds[0][3],16)==0x4d333537','')
    s=s.replace("done=dict(cycles=int(ds[0][0]),output_words=int(ds[0][1]))", "done=dict(cycles=int(ds[0][0]),output_words=int(ds[0][1]),direct_internal_return_print=ds[0][3],direct_internal_return_proven=False)")
    assert s!=source.read_text(encoding='utf-8')
    ns={'__name__':'m438_saved_only_return_collector','__file__':str(source)}
    exec(compile(s,str(HERE/'m438_collect02.py')+':saved-only','exec'),ns);ns['main']()

if __name__=='__main__':main()
