"""Close source demand audit and two bounded read-only kernel observations."""
import json
import re
import m351_workflow as w
MiB=1<<20

def integers(text):
    out={}
    for line in text.splitlines():
        s=line.replace(':','').split()
        if len(s)>=2:
            try:out[s[0]]=int(s[1])*(1024 if len(s)>2 and s[2]=='kB' else 1)
            except ValueError:pass
    return out

def main():
    cases=[('audit','M364-reserve-and-cache-audit-01/RESULT.json','696a71aafd5842322151357d269a593d7b103a26da22499bd55caf6094286a21'),('metadata','M364-kernel-metadata-board-01/BOARD_RESULT.json','1fce88e03cb94a3394fd1d31b1765c1538ab574b7cc088ba70411a126e0b8c8a'),('sysfs','M364-cma-sysfs-board-01/BOARD_RESULT.json','8a0f5cc705783e46bc6d82ea78c93babc34fc5163ffd35c5a31bd23ef58dd461')]
    data={};bindings=[]
    for name,relative,digest in cases:
        path=w.BASE/'runs'/relative;assert w.sha(path)==digest
        for record in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert digest in (w.ROOT/record).read_text(encoding='utf-8-sig')
        data[name]=json.loads(path.read_text(encoding='utf-8'));bindings.append(dict(name=name,path=path.relative_to(w.ROOT).as_posix(),sha256=digest))
    raw=data['metadata'];a=data['audit'];s=data['sysfs']
    before=integers(raw['before']['/proc/meminfo']['text']);after=integers(raw['after']['/proc/meminfo']['text'])
    vm_before=integers(raw['before']['/proc/vmstat']['text']);vm_after=integers(raw['after']['/proc/vmstat']['text'])
    counters={k:dict(before=vm_before[k],after=vm_after[k],delta=vm_after[k]-vm_before[k]) for k in vm_before if k.startswith(('cma_','pgmigrate_','compact_','pgscan_','pgsteal_'))}
    match=re.findall(r'(?m)^Node\s+0, zone\s+DMA, type\s+CMA\s+(.+)$',raw['before']['/proc/pagetypeinfo']['text']);assert len(match)==1
    counts=list(map(int,match[0].split()));assert len(counts)==11
    pages=sum(n*(1<<order) for order,n in enumerate(counts));freebytes=pages*raw['platform']['page_size']
    areas=s['areas'];assert areas[0]['existing_names']==['alloc_pages_fail','alloc_pages_success']
    closure=dict(status='CLOSED_RESERVE_POLICY_IDENTIFIED_CACHE_MECHANISM_SUPPORTED_PAGE_OWNER_UNPROVEN',bindings=bindings,reserve_bytes=64<<20,reserve_unchanged=True,explicit_forward_cma_allocations=0,source_scope=a['allocation_scope'],native_peak_certified=False,metadata_snapshot_memory=dict(before=before,after=after),cma_free_block_counts_by_order=counts,cma_free_blocks_payload_bytes=freebytes,vmstat_counters=counters,sysfs_area_counters=areas,
        conclusions=['64 MiB is a conservative admission policy, not a source-derived list of later dedicated CMA requests. Keep unchanged.',
        'Known selected staged runtime has seven constructor buffers totalling 33484832 bytes; forward/retry reuse them. Ordinary PS payloads and native workspaces remain distinct.',
        'Existing M363 SHA-stage Cached growth with tiny RSS delta and upstream MOVABLE/CMA behavior supports page-cache explanation; actual file-to-CMA PFN association unproven.',
        'Existing debugfs is mounted, but cma metadata directory and page_owner file absent; sysfs provides only cumulative successful/failed allocated-page counts, no release/available/bitmap/PFN. Cannot derive live dedicated occupancy.',
        'CMA buddy free-block histogram is a current free-list distribution, not proof a larger CMA allocation cannot migrate/reclaim. All counters are global lifetime snapshots, not the M363 SHA interval.',
        'Current no-runtime CmaFree cannot unlock loaded-runtime capacity. No reserve reduction, candidate promotion, numerical/performance escalation.'],
        correction_to_initial_audit='Initial LM-head 74.1875 MiB accounting is a subset (three FP32 plus four Boolean payloads), not a proven conservative peak: Boolean indexing allocates another FP32 selection and parsing/native temporaries remain. Do not use as a capacity bound. Initial immutable audit retained; corrected final report supersedes this sentence.',
        rejected_attempts=['First local transfer collector lacked pathlib.Path import: NameError after valid upload/hash/syntax. Fixed host-only import, collected original transfer log, no repeated upload/probe.', 'Initial AST assertion incorrectly required unselected allocate_layout allocator spelling in allocate-name list; local assertion corrected before result creation; no board action.'],
        overlay_loads=0,model_forward_calls=0,fpga_transactions=0,real_asset_data_reads=0,cache_eviction=False,capacity_proven=False,file_page_ownership_proven=False,performance_pass=False,formal_promotion_allowed=False,
        next_step='Remain at memory diagnosis. To prove event-specific cache usage, separately plan bounded original SHA-stage sampling with cumulative CMA counters and valid file residency; current interfaces cannot prove exact PFN ownership. No full-runtime or model rerun authorized by this closure.')
    report=(w.BASE/'runs/M364-reserve-and-cache-audit-01/REPORT.md').read_text(encoding='utf-8')
    old=next(line for line in report.splitlines() if line.startswith('LM head虽'))
    report=report.replace(old,'LM head虽只取末token，原路径仍组装32行：单份最大 **18.546875 MiB**。merge同时保留旧target、update、新merged，三份FP32 payload最多55.640625 MiB，有限性布尔与Boolean索引的FP32选择副本另计；解析、线程和原生工作区仍未闭合。不能把这些部分payload当作完整峰值或CMA需求。初版74.1875 MiB“保守上限”措辞不成立，原记录保留，以本说明为准。')
    report+='\n\n## 3. 本次板端只读结果\n\n'
    report+=f'实际内核 `{raw["platform"]["uname"][2]}`，root、4096B页面。0Overlay/模型forward/FPGA事务/真实权重数据读取，无清缓存、分配测试或配置修改。两次探针耗时分别{raw["elapsed_s"]:.6f}s与{s["elapsed_s"]:.6f}s，不包含传输时间；原字节分别26与5个900B上限块回收。\n\n'
    report+=f'- 当前未加载runtime：CmaTotal **{before["CmaTotal"]/MiB:.6f} MiB**、CmaFree **{before["CmaFree"]/MiB:.6f} MiB**、MemAvailable **{before["MemAvailable"]/MiB:.6f} MiB**、Cached **{before["Cached"]/MiB:.6f} MiB**。这是空闲板快照，不能代替完整runtime的门槛。\n'
    report+='- debugfs已挂载；其中cma目录与page_owner文件不存在。sysfs只有reserved区域的alloc_pages_success=131469、alloc_pages_fail=0，没有释放页/当前可分配页/PFN/bitmap字段。成功页数为累计量，不能当当前占用或减CmaTotal求余量。\n'
    report+=f'- vmstat累计cma_alloc_success={vm_before["cma_alloc_success"]}、cma_alloc_fail={vm_before["cma_alloc_fail"]}；本次读取前后变化为0。这不能证明M363原校验期间的分配来源。已有失败仍是前置政策拒绝，不能改称实际CMA分配失败。\n'
    report+=f'- CMA free-list按order 0–10的块数为 `{counts}`，加权{freebytes/MiB:.6f} MiB，与非原子meminfo快照近似对应。order10单块4MiB，仍不能据此说6.64MiB缓冲无法分配：CMA分配会尝试页迁移/回收。\n'
    report+='- pgscan_file/pgsteal_file、pgmigrate/compact累计计数存在，说明系统统计能力可用；它们没有具体文件/阶段标签。当前数据不能确认哪些BF16文件页在CMA、哪些页仍被固定、能回收多少。\n\n'
    report+='**裁决：已澄清64MiB来源与完整SHA/实际加载的区别；页缓存机制有依据，具体文件物理页归属及运行时峰值仍未证明。门槛保持，完整模型/视频数值与性能不解锁。**\n\n'
    report+='下一步如继续，先独立设计最大的SHA阶段前后CMA累计计数与权限有效驻留观察，避免整模型重跑；这可进一步区别普通页缓存与CMA API分配事件，但当前系统接口仍不足以提供精确PFN归属。不得清缓存、临时开启debugfs/page_owner/改boot。\n\n'
    report+='## 原始证据及限制\n\n'
    for b in bindings:report+=f'- `{b["path"]}` SHA256 `{b["sha256"]}`\n'
    report+='\n主机回收器Path导入遗漏只修复回收，原板端已核验文件和日志复用；未重复上传或运行。初版head部分内存账目纠正在本报告中，原初版证据保持。所有新结果同步至BOARD/CURRENT/docs。\n'
    out=w.BASE/'runs/M364-memory-questions-closure-01'
    w.atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True);closure['report_sha256']=w.sha(out/'REPORT.md')
    w.atomic(out/'RESULT.json',w.encoded(closure),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m364_memory_questions_closure',dict(status=closure['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,reserve_unchanged=True,capacity_proven=False,file_page_ownership_proven=False),f'## M364 两项内存问题闭合\n\n稳定0x4D395832/候选0x4D333537，64MiB为保守政策非已证明后续专用需求，7缓冲forward复用，普通PS payload单列，native峰值未证。两次只读板端原SHA回收/同步：debugfs已挂载但无CMA/page_owner，sysfs仅成功131469页/失败0累计，无release/available/PFN/bitmap；不能算当前专用占用或具体文件归属。空闲CmaFree98.585938MiB不解锁runtime容量，0模型/PL/真实资产数据读，无清缓存/配置修改。初版head74.1875MiB只是部分账目，非保守总峰值，最终报告纠正；主机Path遗漏仅原日志回收修复不重跑。证据SHA `{digest}`。仍停容量级，下一步仅独立规划SHA阶段事件计数与有效驻留，不自动重跑模型或晋级。')
    print(json.dumps(dict(status=closure['status'],sha256=digest,report=str(out/'REPORT.md'),current_cma_mib=before['CmaFree']/MiB,free_histogram_mib=freebytes/MiB)))

if __name__=='__main__':main()
