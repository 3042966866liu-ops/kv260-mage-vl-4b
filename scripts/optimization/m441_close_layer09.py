"""Adjudicate the immutable collected single-layer result only."""
import json
import m351_workflow as w
from m441_host_io08 import atomic

def main():
    p=w.BASE/'runs/M441-single-layer-board-09/BOARD_RESULT.json';r=json.loads(p.read_bytes());raw=w.sha(p)
    assert r['status']=='PASS_M441L_SINGLE_LAYER_DIAGNOSTIC' and all(r['exact_comparison'].values())
    assert r['safe_buffers_released'] and not r['unsafe_buffers_retained'] and len(r['released_buffers'])==7 and not r['sampled_memory']['stop_reason']
    assert all(raw in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    out=w.BASE/'runs/M441-single-layer-closure-09'
    m=r['sampled_memory']['extrema'];loaded=r['loaded_capacity'];layer=r['layer_result']
    report=f'''# M441 单层数值与生命周期闭合（2026-10-09）

Build0x4D343431，原raw SHA {raw}，gate/export/controller均0，369个900B分块完整回收。

原完整M276/M273/M238/M241对象保留，仅一层159行重复固定文本embedding；不是视频。五family全部输入/输出、hidden、K/V和全部量化/缩放/重试/权重暂存记录与原M343参考相同。语言逻辑{layer['logical_calls']}、物理{layer['host_calls']}，另一个同Overlay最小事务，合计{r['fpga_transactions']}。

七原缓冲合计33484832B，封锁第八次PYNQ分配，无新CMA bank或PS槽；原owner逆序各释放一次。候选末态AP_CTRL4、两DMASR4098，Build匹配、无错；稳定Overlay重载后没有提交事务，DMASR0仅为未提交生命周期，不称已完成idle。

完整runtime准入时CmaFree {loaded['cma_free_bytes']/(1<<20):.6f}MiB，MemAvailable {loaded['mem_available_bytes']/(1<<20):.6f}MiB。固定64MiB CMA门槛只记录反事实，没有拒绝；真正检查普通PS增长256MiB和其剩余预算之外64MiB普通可用余量。

20ms采样：最低CmaFree {m['min_cma']/(1<<20):.6f}MiB，最低MemAvailable {m['min_available']/(1<<20):.6f}MiB，最大RSS {m['max_rss']/(1<<20):.6f}MiB；整个进程VmHWM {m['max_hwm']/(1<<20):.6f}MiB含加载且采样可能漏短峰，不作为精确原生总峰值。源码兼容在Overlay/分配之前已核对；生产入口及服务不改变。

单层PASS只解锁独立原30token/36层/完整head数值包；不证明真实视频容量、完整请求时间或生产准入。固定文本已经复用M36603修正后的head物理观察与参考，不重复旧失败或Q链。
'''
    atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True)
    v=dict(status='PASS_M441_SINGLE_LAYER_CLOSED',build_id=r['build_id'],raw_sha256=raw,logical=layer['logical_calls'],physical=layer['host_calls'],total_transactions=r['fpga_transactions'],all_reference_fields_exact=True,original_buffers_released=7,source_checked_before_overlay=True,sampled_memory=r['sampled_memory'],fixed_cma_reserve_enforced=False,actual_video=False,full_model_capacity_proven=False,request_performance_proven=False,promotion=False,report_sha256=w.sha(out/'REPORT.md'))
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);sha=w.sha(out/'RESULT.json')
    w.sync('latest_m441_single_layer_closure',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=sha,raw_sha256=raw),f'## M441 单层解读09（2026-10-09）\n\n五family/hidden/KV/重试逐位一致，25语言逻辑/物理+1合法事务，七owner安全释放及稳定重载。无固定64MiB CMA拒绝，真实runtime驻留CMA{loaded["cma_free_bytes"]/(1<<20):.6f}MiB；非实际视频/总峰值/请求收益。raw {raw}；闭合SHA {sha}；下一步固定文本。')
    npath=w.BASE/'runs/M441-completion-notification-08/NOTIFIED.json';n=json.loads(npath.read_bytes());n['stages']['single_layer_pass09']=dict(evidence=p.relative_to(w.ROOT).as_posix(),sha256=raw,closure_sha256=sha);atomic(npath,w.encoded(n))
    print(v['status'],sha)

if __name__=='__main__':main()
