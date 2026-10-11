"""Saved-only closure across original PASS evidence and one independent recovery."""
import json
from m351_workflow import ROOT,BASE,encoded,sha,sync
from m441_host_io08 import atomic
RUN=BASE/'runs/M441-W2-W4-simulation-recovery-23'
def main():
    wf=RUN/'RESULT.json';f=json.loads(wf.read_bytes());assert f['status']=='PASS_M441_SUPPLEMENTAL_GAPS_WITH_SEPARATE_RECOVERY23'
    p=json.loads((RUN/'PREPARATION.json').read_bytes());assert f['preparation_sha256']==sha(RUN/'PREPARATION.json')
    assert [r['case'] for r in f['results']]==['W2_max','timeout','q','gate_up','mlp_down']
    assert sha(ROOT/f['original_interruption']['path'])==f['original_interruption']['sha256']
    for item in f['original_recovery22_failure'].values():assert sha(ROOT/item['path'])==item['sha256']
    rows=['# M441 W2/W4源码与补仿真闭合（2026-10-10）','','Build 0x4D343431。W2九字、W4十七字记录均走记录内连续loader→FIFO34→原compute，跨记录仍为原布局。','','|补测|来源|完整输出字|周期|墙钟秒|裁决|','|---|---|---:|---:|---:|---|']
    for x in f['results']:
        path=ROOT/x['path'];assert sha(path)==x['sha256'];r=json.loads(path.read_bytes());assert r['status'].startswith('PASS_') and all(r['checks'].values())
        for e in r['evidence']:assert sha(ROOT/e['path'])==e['sha256']
        assert all(x['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
        if x['case']=='timeout':rows.append('|W2 timeout|原21|—|200|—|预期门禁拒绝通过，原rc保留|')
        else:
            d=r['details']['done'][0];rows.append(f'|{x["case"]}|'+('新23独立恢复' if x['case']=='mlp_down' else '原21')+f'|{d[1]}|{d[0]}|{r["elapsed_s"]:.3f}|PASS|')
            assert r['original_rc']==r['gate_rc']==0
            if x['case']!='W2_max':assert r['full_real_numerical'] and r['output_sha256']==r['reference_sha256']
    rows+=['','完整真实Q65536、gate_up311296、mlp_down40960共417792个输出逐位核对。固定seed441四R与RX有界0..8、四端口AR/R地址数量、FIFO34满背压排空、实际读/MAC重叠、尾TLAST128有效拍停顿稳定、KEEP/STRB、ap_done一次、Build及原返回值通过。','W2最大327680字零scale夹具只证明协议，覆盖FIFO8192容量、FIFO34、四端口4KiB拆分和超时负例，不当真实模型数值。','','原21最后mlp_down因Windows于06:49重启中断，原rc未知，原日志/部分输出及INTERRUPTION证据完整保存；原21未生成总PASS。新23复用同SHA编译快照/DUT/实际VIP/观察器/完整真实夹具，仅另开末项，一次新完整裁决，未拼接旧部分输出、未重跑已PASS项。','原22输出目录遗漏导致五个fopen WARNING、完整原字节未保存，原FAIL/STOP保持；新23仅补建并实际写权限前置核对输出目录，DUT/输入/观察器/快照逐SHA不改，原22输出不拼接、不覆盖。原18准备失败/19日志解码及沙箱编译失败、旧Random02 FAIL/03中断不覆盖。既有真实CSim、W4Zero和最大协议证据保持。','本结论覆盖预定完整代表链与边界，不是所有合法组合、权重、输入和种子的穷举或形式证明。无新板端、综合布线、时钟变化或生产晋级；原完整请求性能17为独立证据，RTL周期不当作请求收益。','','证据：']
    rows += ['- '+x['path']+' SHA '+x['sha256'] for x in f['results']]
    atomic(RUN/'REPORT.md',('\n'.join(rows)+'\n').encode('utf-8'),immutable=True)
    result=dict(status='PASS_M441_W2_W4_SOURCE_AND_SIMULATION_GAPS_CLOSED23',build_id=p['build_id'],workflow_sha256=sha(wf),preparation_sha256=sha(RUN/'PREPARATION.json'),results=f['results'],original_interruption=f['original_interruption'],original_recovery22_failure=f['original_recovery22_failure'],report_sha256=sha(RUN/'REPORT.md'),W2_new_load_FIFO_path_verified=True,W2_full_real_numerical_RTL=True,W2_maximum_bounded_pressure_and_timeout=True,W4_full_real_gate_up_down_bounded_pressure_RTL=True,board=False,new_performance=False,production_changed=False)
    ev=RUN/'CLOSURE.json';atomic(ev,encoded(result),immutable=True)
    sync('latest_m441_W2_W4_simulation_closure23',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),'## M441源码与补仿真最终闭合23（2026-10-10）\n\nSHA '+sha(ev)+'；原21已PASS四项加新23末项独立完整裁决，各级原SHA/三记录重核，真实417792输出逐位及结束/背压协议通过。21重启中断保留，0新板端/性能/生产变化，详见REPORT。')
    print(result['status'],sha(ev),flush=True)
if __name__=='__main__':main()
