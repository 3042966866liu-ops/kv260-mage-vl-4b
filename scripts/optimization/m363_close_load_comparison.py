"""Close one duplicate-tokenizer correction; no inference promotion."""
import json
import m351_workflow as w
import m363_collect_load_comparison as c

def main():
    oldpath=w.BASE/'runs/M362-load-comparison-closure-01/RESULT.json'
    old=json.loads(oldpath.read_text(encoding='utf-8'))
    rows=[];bindings=[dict(path=oldpath.relative_to(w.ROOT).as_posix(),sha256=w.sha(oldpath))]
    for case in ('A1','B1'):
        p=w.BASE/f'runs/M363-load-{case}-board-01/BOARD_RESULT.json'
        r=json.loads(p.read_text(encoding='utf-8'));assert c.validate(r) and c.completed(r)
        digest=w.sha(p)
        for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert digest in (w.ROOT/name).read_text(encoding='utf-8-sig')
        reference=[(x['name'],x['first_path'],x.get('returned_sha256')) for x in json.loads((w.ROOT/old['bindings'][0]['path']).read_text(encoding='utf-8'))['io_events'] if 'returned_sha256' in x]
        assert [(x['name'],x['first_path'],x.get('returned_sha256')) for x in r['io_events'] if 'returned_sha256' in x]==reference
        rows.append(r);bindings.append(dict(case=case,path=p.relative_to(w.ROOT).as_posix(),sha256=digest))
    fits=all(r['memory_capacity_proven'] for r in rows)
    decision='PASS_LOAD_CAPACITY_ONLY_AFTER_DIAGNOSTIC_CORRECTION' if fits else ('BOTH_STILL_REJECT_RESERVE_COMMON_LOAD_REMAINS' if not any(r['memory_capacity_proven'] for r in rows) else 'MIXED_LOAD_CAPACITY_NO_RELIABLE_UNLOCK')
    lines=['# KV260 完整加载 CMA 定位与一处诊断修正（2026-10-02）','','稳定 Build `0x4D395832`；并行候选 `0x4D333537`。本轮仅加载：没有模型 forward、FPGA事务、额外CMA bank或PS slot；没有重跑已通过的Q链。','','## 同入口 A-B-B-A 对照','','| 次序 | 版本 | 加载完成 CMA MiB | 保留2秒 CMA MiB | 64MiB余量 |','|---|---|---:|---:|---|']
    for r in old['summary']:lines.append(f"| {r['case']} | {r['build_id']} | {r['loaded_capacity']['cma_free_bytes']/(1<<20):.6f} | {r['settled_capacity']['cma_free_bytes']/(1<<20):.6f} | 未满足 |")
    lines+=['','两版均不足；原完整SHA调用序列和七块缓冲几何完全一致。自然初始缓存/CMA不同，不能把差值归因于bitstream或宣称缓存条件完全相同。','','## 唯一修正及验证','','旧诊断先解析tokenizer、丢弃对象，原M243加载时再解析。正式生产M243源码本来只解析一次：本次修正只针对诊断重复构造，不称为生产内存优化。保留上Overlay前真实解析，原加载复用同一个原生Tokenizer对象；路径/打开文件七字段身份前后核对，变化或第三次调用拒绝。所有35次完整SHA、七块DMA缓冲与64MiB门槛保持。','','| 新例 | 版本 | 加载完成 CMA MiB | 保留2秒 CMA MiB | 加载RSS MiB | MemAvailable MiB |','|---|---|---:|---:|---:|---:|']
    summary=[]
    for r in rows:
        stage=next(s for s in r['stages'] if s['name']=='complete-runtime-loaded-retained')['memory']
        lines.append(f"| {r['case']} | {r['build_id']} | {r['loaded_capacity']['cma_free_bytes']/(1<<20):.6f} | {r['settled_capacity']['cma_free_bytes']/(1<<20):.6f} | {stage['process_bytes']['VmRSS']/(1<<20):.6f} | {r['loaded_capacity']['mem_available_bytes']/(1<<20):.6f} |")
        deltas=[]
        for x in r['io_events']:
            before=x['before'];after=x['after']
            deltas.append(dict(name=x['name'],path=x['first_path'],cma_delta_bytes=after['system_bytes']['CmaFree']-before['system_bytes']['CmaFree'],cached_delta_bytes=after['system_bytes']['Cached']-before['system_bytes']['Cached'],rss_delta_bytes=after['process_bytes']['VmRSS']-before['process_bytes']['VmRSS']))
        largest=sorted(deltas,key=lambda x:x['cma_delta_bytes'])[:5]
        summary.append(dict(case=r['case'],build_id=r['build_id'],loaded_capacity=r['loaded_capacity'],settled_capacity=r['settled_capacity'],loaded_memory=stage,largest_io_cma_drops=largest,allocated_buffers=r['allocated_buffers'],retained_inventory=r['retained_inventory'],single_parse_same_object=r['tokenizer_single_parse_reused']))
    lines+=['',decision,'','## 七块实际缓冲的大小和生命周期','','| 缓冲 | 数量 | 单块请求大小 | 生命周期 |','|---|---:|---:|---|','| 四个权重端口 | 4 | 6,963,200 B（6.640625 MiB） | M238构造分配，保留至runtime关闭 |','| 输入 | 1 | 389,152 B | M238构造分配，保留至runtime关闭 |','| 输出与备用输出 | 2 | 2,621,440 B（2.5 MiB） | 原流水线双输出策略，保留至runtime关闭 |','','合计33,484,832 B（31.933624 MiB），没有发现候选额外分配或已证明可删除的重复DMA缓冲。请求字节不等于底层页取整后实际占用；两个输出大小相同也不证明重复。关闭时每块按拥有关系安全释放一次，幂等析构无额外后端释放。','','## 逐文件下降位置','']
    for r in summary:
        lines+=['### '+r['case'],'','| 调用/文件 | CMA变化 MiB | Cached变化 MiB | RSS变化 MiB |','|---|---:|---:|---:|']
        for x in r['largest_io_cma_drops']:lines.append(f"| {x['name']} / {x['path']} | {x['cma_delta_bytes']/(1<<20):+.6f} | {x['cached_delta_bytes']/(1<<20):+.6f} | {x['rss_delta_bytes']/(1<<20):+.6f} |")
    lines+=['','下降可定位到具体哈希调用和加载检查点；仍未证明这些文件占用了哪些CMA物理页、是否可迁移回收、是否连续性受限。Cached/RSS/CmaFree相关变化不足以证明根因。embedding的mmap逻辑大小也不等于驻留或CMA占用。','','## 当前边界与下一步','','仅实际容量条件成立后才进入其他W4/MLP代表链、单层、固定文本及固定159-token视频。原Q链3.5279倍时间比值保持其单链范围，不是完整请求收益。若本轮仍不足，停在容量级；下一项应是针对已定位文件/阶段的物理页与分配来源证据，不再泛泛清缓存或重跑完整模型。','','稳定Overlay已重新加载但没有提交事务，初始DMASR=0只表示从未提交，不能称为已完成DMA空闲。boot/DTB/CMA配置、服务及回滚保持。','','## 原始证据','']
    for b in bindings:lines.append(f"- `{b['path']}`，SHA256 `{b['sha256']}`")
    result=dict(status=decision,bindings=bindings,summary=summary,original_full_hash_sequence_equal=True,original_buffer_geometry_equal=True,production_source_changed=False,one_diagnostic_tokenizer_correction=True,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,capacity_unlocked=fits,physical_page_ownership_proven=False,next_step='Capacity-only adjudication before any larger numerical gate; do not clear caches or replay Q')
    out=w.BASE/'runs/M363-single-tokenizer-closure-01'
    w.atomic(out/'REPORT.md',('\n'.join(lines)+'\n').encode('utf-8'),immutable=True)
    result['report_sha256']=w.sha(out/'REPORT.md')
    result['manifest_sha256']=w.sha(c.PKG/'PACKAGE_MANIFEST.json')
    correction=w.BASE/'runs/M363-correction-support-01/RESULT.json'
    result['offline_correction_support_sha256']=w.sha(correction)
    w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m363_single_tokenizer_closure',dict(status=decision,sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),capacity_unlocked=fits),f'## M363 单次tokenizer诊断修正闭合\n\nBuild0x4D395832/0x4D333537；仅复用前置原生Tokenizer，原M243生产源码不改、35完整SHA/7缓冲不变，0forward/FPGA。裁决{decision}；保留64MiB门槛，自然缓存不等同，不证明物理页归属。证据SHA `{digest}`。Q不重跑；完整模型/视频数值与性能尚未执行。')
    print(decision,digest)

if __name__=='__main__':main()
