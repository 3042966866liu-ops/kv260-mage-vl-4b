"""Bind frozen code, existing load records, and explicit memory payloads."""
import ast
import json
import m351_workflow as w

OUT=w.BASE/'runs/M364-reserve-and-cache-audit-01'
SRC=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
MiB=1<<20

def main():
    recovery={}
    for name in ('AGENTS.md','CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=w.ROOT/name;t=p.read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=w.sha(p),bytes=p.stat().st_size,lines=len(t.splitlines()))
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    closure_path=w.BASE/'candidates/M363-common-load-observer-01/SOURCE_CLOSURE.json'
    closure=json.loads(closure_path.read_text(encoding='utf-8'))
    sources=[];allocator_calls=[];references={}
    for row in closure['files']:
        p=SRC/row['path'];assert w.sha(p)==row['sha256'];sources.append(dict(row,local_path=p.relative_to(w.ROOT).as_posix()))
        if p.suffix!='.py':continue
        text=p.read_text(encoding='utf-8');tree=ast.parse(text)
        def scan(node,context='module'):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):context=node.name
            if isinstance(node,ast.Call) and ((isinstance(node.func,ast.Name) and node.func.id=='allocate') or (isinstance(node.func,ast.Attribute) and node.func.attr=='allocate')):
                allocator_calls.append(dict(path=row['path'],function=context,line=node.lineno,expression=ast.get_source_segment(text,node)))
            for child in ast.iter_child_nodes(node):scan(child,context)
        scan(tree)
        references[row['path']]=[dict(line=i,text=s) for i,s in enumerate(text.splitlines(),1) if any(k in s for k in ('np.full(', 'np.zeros(', 'np.empty(', 'np.concatenate(', 'np.memmap(', 'allocate(', '_components', 'merge_outputs(', 'keys.append(', 'values.append(', '64 << 20', 'budget_mib', 'GFP'))]
    assert {x['function'] for x in allocator_calls}<={'__init__','allocate_layout'}, allocator_calls
    policies=[]
    for name in ('weight_prefetch.py','ps_read_ahead.py','ps_slot_capacity.py','m350_audit_ps_read_ahead.py','m358_prepare_capacity.py'):
        p=w.HERE/name;t=p.read_text(encoding='utf-8')
        policies.append(dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p),reserve_lines=[dict(line=i,text=s) for i,s in enumerate(t.splitlines(),1) if '64' in s and any(k in s for k in ('reserve','RESERVE','20','MiB'))]))
    bindings=[];deltas=[];buffer_rows=None
    for case,expected in [('A1','a04d03b6a42d957505023a9d31a340c3adc1c79f499b3a9892c6c811af68ac8b'),('B1','e8697ca113caa68373a2a1ed762e4f17447c1c903dc29af392b950a0b2464c08')]:
        p=w.BASE/f'runs/M363-load-{case}-board-01/BOARD_RESULT.json';assert w.sha(p)==expected and expected in json.dumps(board)
        r=json.loads(p.read_text(encoding='utf-8'));bindings.append(dict(case=case,path=p.relative_to(w.ROOT).as_posix(),sha256=expected))
        assert len(r['allocated_buffers'])==7 and [b['bytes'] for b in r['allocated_buffers']]==[6963200]*4+[389152,2621440,2621440]
        buffer_rows=r['allocated_buffers']
        for e in r['io_events']:
            delta={k:e['after']['system_bytes'][k]-e['before']['system_bytes'][k] for k in ('CmaFree','Cached','MemAvailable')}
            delta['RSS']=e['after']['process_bytes']['VmRSS']-e['before']['process_bytes']['VmRSS']
            deltas.append(dict(case=case,name=e['name'],path=e['first_path'],delta_bytes=delta,integrity_digest='returned_sha256' in e,returned_sha256=e.get('returned_sha256')))
    vision=SRC/'deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
    vm=json.loads(vision.read_text(encoding='utf-8'));vmax=max(vm['modules'],key=lambda x:x['shape'][0]*x['input_groups']*64)
    cache=SRC/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/M261_CACHE_POLICY.json'
    cp=json.loads(cache.read_text(encoding='utf-8'))
    cache_bytes=cp.get('expected_used_bytes');assert cache_bytes==66699264
    payloads=[]
    for n in (159,1024):
        payloads.append(dict(tokens=n,kv_retained_bytes=2*36*n*8*128*4,hidden_bytes=n*2560*4,q_bytes=n*4096*4,gate_or_up_bytes=n*9728*4,gate_and_up_bytes=2*n*9728*4,attention_one_group_scores_bytes=4*n*n*4,attention_mask_bytes=n*n))
    head=32*151936*4
    r=dict(status='COMPLETE_SOURCE_RESERVE_AND_EXISTING_IO_AUDIT',build_ids=['0x4D395832','0x4D333537'],recovery_read=recovery,closure_sha256=w.sha(closure_path),source_bindings=sources,allocator_calls=allocator_calls,source_memory_references=references,policy_bindings=policies,bindings=bindings,existing_io_deltas=deltas,
        reserve_bytes=64<<20,reserve_unchanged=True,reserve_basis='Conservative admission policy; no proven post-construction dedicated CMA allocation list summing to 64 MiB',explicit_selected_forward_pynq_allocate_calls=0,allocation_scope='Frozen selected staged-low-cma Python closure; excludes resident-high-ddr allocate_layout and opaque native libraries',constructor_buffer_requests=buffer_rows,total_requested_cma_payload_bytes=33484832,
        ordinary_ps_payloads=payloads,visual_packed_cache_bytes=cache_bytes,visual_max_decoded_weight=dict(module=vmax['module'],shape=vmax['shape'],input_groups=vmax['input_groups'],fp32_bytes=vmax['shape'][0]*vmax['input_groups']*64*4),head_t32_array_bytes=head,head_merge_upper_explicit_array_bytes=3*head+4*(head//4),
        native_total_peak_proven=False,cma_physical_page_ownership_proven=False,cma_irrecoverable_fragmentation_proven=False,board_executed=False,capacity_proven=False,performance_pass=False,formal_promotion_allowed=False,
        kernel_sources=['https://raw.githubusercontent.com/torvalds/linux/v5.15/fs/proc/meminfo.c','https://raw.githubusercontent.com/torvalds/linux/v5.15/mm/page_alloc.c','https://raw.githubusercontent.com/torvalds/linux/v5.15/mm/cma.c','https://docs.kernel.org/admin-guide/mm/cma_debugfs.html','https://docs.kernel.org/admin-guide/mm/pagemap.html'],
        next_step='Read existing kernel CMA bitmap/range and kpageflags capabilities only; no asset hash rerun, no forward, no reserve change')
    lines=['# KV260：64 MiB余量与校验阶段CMA下降核查','', '稳定Build `0x4D395832`；候选 `0x4D333537`。本记录复用已有结果和冻结源码，不重跑模型、Q链或完整资产校验。','', '## 1. 64 MiB究竟保留给什么','', '**目前它是保守准入政策，并非已证明的后续64 MiB专用CMA分配需求。** 它来自weight_prefetch及PS预读/容量诊断的reserve常量，后来沿用到M358–M363加载门禁。没有找到推理阶段必需新增64 MiB CMA的对应清单；按用户要求保持门槛不变。','', '| 专用缓冲 | 数量 | 单块请求字节 | 分配/释放 |','|---|---:|---:|---|','| 权重端口 | 4 | 6,963,200 | 构造时分配；关闭时释放 |','| 输入 | 1 | 389,152 | 构造时分配；关闭时释放 |','| 输出和备用输出 | 2 | 2,621,440 | 构造时分配；关闭时释放 |','', '**请求合计31.933624 MiB。** 实际selected staged路径的分配调用只在构造函数；allocate_layout属于未启用resident-high-ddr分支。family、T32流水、缩放重试、LM head复用已有缓冲。双输出是原流水线必需组织，不能因大小相同删除。请求字节不等于驱动页取整后物理占用。此结论限冻结Python调用闭包，未把不透明驱动/原生库作为已证明零分配。','', 'forward仍会新增普通PS内存。普通可迁移页和页缓存可能使用空闲CMA页，故零新增显式PYNQ调用不等于CmaFree不会下降。下表是数组payload，不是经过运行证明的总峰值。','', '| 对象 | 固定159 tokens MiB | 1024 tokens MiB | 生命周期 |','|---|---:|---:|---|']
    for key,label,life in [('kv_retained_bytes','36层K/V','prefill累计保留；decode拼接还会出现旧/新副本'),('hidden_bytes','一份hidden','每层及残差/归一化临时副本'),('q_bytes','一份Q','当前层'),('gate_and_up_bytes','gate+up两份','MLP激活/乘法还可能生成同尺寸临时数组'),('attention_one_group_scores_bytes','一组attention分数','8组依次执行；scores/prob/where可能同时存活')]:
        lines.append(f"| {label} | {payloads[0][key]/MiB:.6f} | {payloads[1][key]/MiB:.6f} | {life} |")
    lines+=['',f'视觉懒加载packed-code缓存预算64 MiB，选定26项payload **{cache_bytes/MiB:.6f} MiB**；这是普通PS缓存预算，不能混为CMA reserve。缓存构造时为空，forward逐步填充，关闭清除。',f'最大单视觉W4恢复权重 `{vmax["module"]}`，shape `{vmax["shape"]}`，FP32 padded payload **{r["visual_max_decoded_weight"]["fp32_bytes"]/MiB:.6f} MiB**；解包整数、scale及Torch转换/算子工作区另外占用。',f'LM head虽只取末token，原路径仍组装32行：单份最大 **{head/MiB:.6f} MiB**。merge同时有旧target/update/new merged及有限性布尔和索引副本；三份FP32加四份同形bool保守数组上限 **{r["head_merge_upper_explicit_array_bytes"]/MiB:.6f} MiB**，还未包括解析临时、pack线程或原生分配。该数不是实测峰值，也不是CMA需求。','', '这些阶段峰值不能直接相加：视觉解码临时通常先释放，packed cache继续保留；语言KV随层累计；head合并发生末尾。还缺Torch/BLAS/allocator保留页、驱动和线程栈等实际峰值证据，因此无法用这次静态核查认证64 MiB足够或降低它。','', '## 2. 校验与实际权重加载的区别','', '| 资产 | 完整性校验 | 所选推理路径消费者 |','|---|---|---|','| 完整vision_bf16.safetensors | release preflight完整SHA | 所选冻结路径未用此完整文件构造视觉模型；使用meta空模型、W4 mmap及小raw参数 |','| runtime wheel归档 | release preflight完整SHA | 已安装模块用于运行；所选路径未从该归档加载模型 |','| 视觉W4四分片 | preflight/store完整SHA | readonly mmap；forward按需解包 |','| 语言/LM head W4分片 | preflight/layout完整SHA | 暂存读窗口到已有四权重缓冲 |','| embedding | preflight完整SHA | np.memmap与token行采样 |','', '这只是M348/M363选定加载路径审计，不是全系统没有其他消费者的证明。完整SHA是读取所有字节，不等于把完整权重作为进程中的模型tensor保留。','', '| 原始例 | 最大下降文件 | CMA变化 MiB | Cached变化 MiB | RSS变化 MiB |','|---|---|---:|---:|---:|']
    for case in ('A1','B1'):
        d=min((x for x in deltas if x['case']==case and x['integrity_digest']),key=lambda x:x['delta_bytes']['CmaFree']);b=d['delta_bytes']
        lines.append(f"| M363 {case} | {d['path'].split('/')[-1]} | {b['CmaFree']/MiB:+.6f} | {b['Cached']/MiB:+.6f} | {b['RSS']/MiB:+.6f} |")
    lines+=['', '已有记录支持：下降发生在具体完整SHA读取期间，同时Cached增长、进程RSS几乎不变。不同自然缓存运行中最大下降文件还会改变；期间也存在CMA自然回升。它尚不能证明文件页的物理位置、专用CMA bitmap占用、是否可回收或连续性失败。','', '## 内核机制与证据缺口','', 'Linux v5.15中CmaFree取NR_FREE_CMA_PAGES；它不是CMA专用分配bitmap的空闲总量。[meminfo实现](https://raw.githubusercontent.com/torvalds/linux/v5.15/fs/proc/meminfo.c)', 'MIGRATE_MOVABLE请求允许ALLOC_CMA，页分配器可从MIGRATE_CMA空闲链表取页。这解释了文件读取填充页缓存时，CmaFree可能下降而进程RSS不明显增长。[页分配器](https://raw.githubusercontent.com/torvalds/linux/v5.15/mm/page_alloc.c)', '专用cma_alloc先在bitmap选区，再尝试alloc_contig_range迁移/回收；这与“当前free页统计较低”是不同问题。低统计不能直接证明专用空间耗尽，也不保证分配一定成功。[CMA实现](https://raw.githubusercontent.com/torvalds/linux/v5.15/mm/cma.c)', '', '以上是上游v5.15机制解释，板端vendor配置/补丁及当前页归属需单独读取证据。只读debugfs的base_pfn/count/bitmap可区分区域与专用占用；不能写alloc/free或临时挂载debugfs。kpageflags没有CMA位，只能用实际区域PFN范围关联；LRU非ANON非SWAPBACKED只是文件页候选类别，不能识别具体文件。[CMA debugfs](https://docs.kernel.org/admin-guide/mm/cma_debugfs.html)、[pagemap说明](https://docs.kernel.org/admin-guide/mm/pagemap.html)', '', '下一步仅读取已有内核统计及接口能力；不重新读取资产数据，不制造缺页，不清缓存，不做分配试验。若PFN/bitmap接口不可用，明确记录证据不足，不把普通空闲快照当作runtime容量证明。']
    w.atomic(OUT/'REPORT.md',('\n'.join(lines)+'\n').encode('utf-8'),immutable=True)
    r['report_sha256']=w.sha(OUT/'REPORT.md');w.atomic(OUT/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(OUT/'RESULT.json')
    w.sync('latest_m364_reserve_cache_audit',dict(status=r['status'],result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,reserve_unchanged=True,capacity_proven=False),f'## M364 64MiB依据与校验内存核查\n\n稳定0x4D395832/候选0x4D333537；冻结闭包显式PYNQ分配仅构造7缓冲33484832B，forward复用；64MiB是保守准入政策，非已证明后续专用分配需求。普通PS的KV/视觉懒缓存/恢复权重/head合并单列payload，原生总峰值未证明，门槛保持。复用M363逐SHA下降，区分校验与实际加载；上游内核机制不能替代板端PFN/bitmap归属证据。0上板/forward/FPGA/重跑，证据SHA `{digest}`。下一步仅只读内核页统计能力调查。')
    print(json.dumps(dict(status=r['status'],sha256=digest,allocator_calls=allocator_calls,max_vision=r['visual_max_decoded_weight'])))

if __name__=='__main__':main()
