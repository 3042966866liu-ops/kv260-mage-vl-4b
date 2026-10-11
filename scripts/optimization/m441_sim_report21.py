"""Read-only saved simulation closure/report; no tool or board launch."""
import json
from m351_workflow import ROOT,BASE,encoded,sha,sync
from m441_host_io08 import atomic
RUN=BASE/'runs/M441-W2-W4-simulation-coverage-21'


def main():
    workflow=RUN/'RESULT.json'
    assert workflow.is_file(),'Finite simulator still running or stopped; do not claim closure'
    final=json.loads(workflow.read_bytes())
    assert final['status']=='PASS_M441_W2_W4_SUPPLEMENTAL_SIMULATION_CLOSED19'
    prep=RUN/'PREPARATION.json';p=json.loads(prep.read_bytes())
    assert final['preparation_sha256']==sha(prep)
    refs=[];report=['# M441 W2/W4 补充仿真裁决（2026-10-10）','',
        '冻结M441源码 Build0x4D343431；W2每record9字、W4每record17字，同每shard FIFO34 DATAFLOW读算通路。',
        '连续读取仅指记录内部，跨记录按原布局。原候选源码、实际综合RTL、时钟/约束未改。本轮不访问板端或修改稳定部署。','',
        '|补测|位宽|完整输出字|RTL周期|墙钟秒|裁决|', '|---|---:|---:|---:|---:|---|']
    for row in final['results']:
        path=RUN/(row['case']+'_RESULT.json');r=json.loads(path.read_bytes())
        assert sha(path)==row['sha256'] and r['status'].startswith('PASS_') and all(r['checks'].values())
        for e in r['evidence']:assert sha(ROOT/e['path'])==e['sha256']
        assert all(sha(path) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
        refs.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),status=r['status']))
        if row['case']=='timeout':report.append('|W2同快照200周期timeout|2|—|200（预期失败）|—|原工具返回值保留，门禁拒绝PASS|')
        else:
            done=r['details']['done'][0]
            report.append(f'|{row["case"]}|{r["bits"]}|{done[1]}|{done[0]}|{r["elapsed_s"]:.3f}|PASS|')
    report.extend(['','完整真实Q、gate_up、down参考逐位核对全部输出，KEEP/STRB全255、仅最终一拍TLAST、ap_done一次及返回Build一致。',
        '四端口AR/R完整地址覆盖、RLAST/RRESP、MAC工作量、FIFO34满背压排空、真实accepted-MAC与读重叠、停顿payload稳定、固定seed441延迟0..8及尾TLAST128有效拍停顿均完整核对。',
        'W2最大协议另外覆盖G1/D10/512 rows、FIFO8192容量满、W2九字记录在四端口4KiB边界拆分以及同新编译快照200周期timeout负例。最大夹具零scale，只证明协议，不代表真实模型数值或性能。',
        '', '已有证据完整复用：M441七组缩减真实记录CSim、完整W2/Q与两W4 CSim、两W4完整Zero数值RTL、W4最大协议/timeout07。无重复已通过测试。',
        '原Random02 FAIL及03中断不覆盖，不称旧六组Random全部通过。原18准备失败、19日志解码前置失败及沙箱编译失败保留；21恢复仅隔离路径/正常工具权限，同DUT/VIP/夹具/观察器SHA，内部沿用schema19标签。',
        '', '这是一组预定代表完整链和最大协议边界的L1/L2证据；没有穷举所有合法G/D组合、所有权重/输入/随机种子，不声称形式证明。RTL周期不当作板端或完整请求性能；原板端性能17独立证据保持。',
        '', '完整证据：'])
    for e in refs:report.append(f'- `{e["path"]}` SHA `{e["sha256"]}`')
    atomic(RUN/'REPORT.md',('\n'.join(report)+'\n').encode('utf-8'),immutable=True)
    r=dict(status='PASS_M441_W2_W4_SOURCE_AND_SIMULATION_GAPS_CLOSED21',build_id=p['build_id'],
           workflow_sha256=sha(workflow),preparation_sha256=sha(prep),results=refs,report_sha256=sha(RUN/'REPORT.md'),
           W2_new_load_FIFO_path_verified=True,W2_full_real_numerical_RTL=True,W2_maximum_bounded_pressure_and_timeout=True,
           W4_full_real_gate_up_down_bounded_pressure_RTL=True,board=False,new_performance=False,production_changed=False)
    ev=RUN/'CLOSURE.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_W2_W4_simulation_closure21',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         '## M441 W2/W4源码与缺口仿真最终报告21（2026-10-10）\n\nSHA '+sha(ev)+'；全部原字节/返回值/原参考/资源协议及三记录重核，W2完整Q数值RTL和最大压力/timeout、两W4真实完整链有界背压RTL闭合。原PASS/FAIL保持，0新板端/请求性能/生产修改；范围与限制见REPORT.md。')
    print(r['status'],sha(ev))


if __name__=='__main__':main()
