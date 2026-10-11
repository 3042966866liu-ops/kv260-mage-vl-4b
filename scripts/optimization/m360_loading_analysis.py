"""Read existing immutable load evidence; no board operations or inference."""
import json
import m351_workflow as w

OUT=w.BASE/'runs/M360-existing-load-analysis-01'
MiB=1<<20

def main():
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=w.ROOT/name; text=p.read_text(encoding='utf-8-sig')
        recovery[name]=dict(sha256=w.sha(p),bytes=p.stat().st_size,lines=len(text.splitlines()))
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    bindings={}
    for name,digest in [('M358-candidate-capacity-board-01','b079a82a89fe01f7131fca275ba1482f381cca814a23683ad6b9358497ea514e'),('M352-load-ps-slot-board-01','325511dd0c5a2f1a57a039c46edbbb9ba867db0012089db824880cba616fd687')]:
        p=w.BASE/'runs'/name/'BOARD_RESULT.json'
        assert w.sha(p)==digest and digest in json.dumps(board)
        bindings[name]=dict(path=p.relative_to(w.ROOT).as_posix(),sha256=digest)
    raw=json.loads((w.ROOT/bindings['M358-candidate-capacity-board-01']['path']).read_text(encoding='utf-8'))
    stages=[]; previous=None
    for stage in raw['stages']:
        m=stage['memory'];values={k:m['system_bytes'][k] for k in ('CmaFree','Cached','MemAvailable')}
        values['RSS']=m['process_bytes']['VmRSS']
        stages.append(dict(name=stage['name'],elapsed_s=stage['elapsed_s'],bytes=values,delta_bytes={k:values[k]-previous[k] for k in values} if previous else {}))
        previous=values
    roles=['staged_weights_port_0','staged_weights_port_1','staged_weights_port_2','staged_weights_port_3','input_buffer','output_buffer','output_buffer_alt']
    sizes=[6963200]*4+[389152,2621440,2621440]
    assert [x['bytes'] for x in raw['allocated_buffers']]==sizes
    assert raw['released_buffers']==list(reversed(raw['allocated_buffers']))
    buffers=[dict(x,role=role,allocation_order=i,release_order=6-i,lifetime='M238/M236 construction through safe engine.close; zero submitted transactions') for i,(x,role) in enumerate(zip(raw['allocated_buffers'],roles))]
    source_root=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    closure=json.loads((w.BASE/'candidates/M358-m357-load-only-03/SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    selected=['board_runtime','m236_prefill_runtime','m243_video_server','video_language_runtime','m276_video_runtime','m259_video_runtime']
    sources=[]
    for name in selected:
        relative=closure['modules'][name];p=source_root/relative
        expected=next(x for x in closure['files'] if x['path']==relative)
        assert w.sha(p)==expected['sha256']
        text=p.read_text(encoding='utf-8')
        sources.append(dict(module=name,path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p),relevant_lines=[dict(line=i,text=s) for i,s in enumerate(text.splitlines(),1) if any(t in s for t in ('allocate(','self.staged_buffers =','def load(','Tokenizer.from_file','np.memmap','np.load(','self.norms =','def close(','verify_layout('))]))
    r=dict(status='COMPLETE_EXISTING_LOG_ANALYSIS_ONLY',recovery_read=recovery,bindings=bindings,stages=stages,buffers=buffers,total_requested_buffer_bytes=sum(sizes),source_bindings=sources,board_executed=False,capacity_proven=False,performance_pass=False,
        findings=['Largest observed CMA drop is release asset hash stage, before DMA allocations; simultaneous Cached rise and almost unchanged RSS. This is stage correlation, not page ownership/reclaimability/fragmentation proof.',
        'Seven requested buffer payloads total 33484832 bytes; four port windows, one input, two pipeline outputs. Two output buffers have a documented M236 ping-pong purpose; equal sizes do not prove duplication.',
        'M276/M259 inherit M243.load without extra post-language loader; Tokenizer.from_file occurs between after-language checkpoint and complete-engine checkpoint. The late RSS rise is consistent with that interval, not proven solely tokenizer ownership.',
        'Historical M352 stable and M358 candidate both rejected 64MiB reserve, but different initial/cache/time conditions prohibit a controlled A/B claim.'],
        next_step='New common load-only runner: per-file original SHA call checkpoints, per-allocation pre/post memory, tokenizer final construction bracket, retained object/mapping inventory. Same source/assets/buffers; only bit path varies. No clearing caches or numerical/chain retry.')
    lines=['# M360 已有完整加载日志分析','', '本文件仅解析原始记录和冻结源码；没有重新上板，也没有修改稳定版。','', '| 阶段 | CMA MiB | CMA变化 MiB | Cached变化 MiB | RSS变化 MiB |','|---|---:|---:|---:|---:|']
    for s in stages:
        d=s['delta_bytes'];lines.append(f"| {s['name']} | {s['bytes']['CmaFree']/MiB:.6f} | {d.get('CmaFree',0)/MiB:+.6f} | {d.get('Cached',0)/MiB:+.6f} | {d.get('RSS',0)/MiB:+.6f} |")
    lines+=['','七块实际缓冲：','', '| 用途 | 请求字节 | MiB | 释放顺序 |','|---|---:|---:|---:|']
    for b in buffers:lines.append(f"| {b['role']} | {b['bytes']} | {b['bytes']/MiB:.6f} | {b['release_order']+1} |")
    lines+=['',f"请求字节合计 **{sum(sizes)} B / {sum(sizes)/MiB:.6f} MiB**。这不是 allocator 页取整后的保留量；地址间距不能作为实际占用证据。",'']
    for x in r['findings']:lines+=['- '+x]
    lines+=['','完整runtime CMA **32.9375MiB**，64MiB门槛缺**31.0625MiB**；普通MemAvailable约**2.83GiB**。','','缺失粒度：逐文件原SHA读取前后、每块DMA分配前后、Overlay加载前后、最终tokenizer构造、保留对象与文件映射。补齐后做稳定/候选共同入口对照；记录自然缓存差异，不能宣称缓存条件完全一致。','','候选仅Q代表链收益成立；容量、其余W4/MLP、层、文本、159-token视频及完整请求性能仍须逐级验证。']
    w.atomic(OUT/'REPORT.md',('\n'.join(lines)+'\n').encode('utf-8'),immutable=True)
    w.atomic(OUT/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(OUT/'RESULT.json')
    w.sync('latest_m360_existing_load_analysis',dict(status=r['status'],sha256=digest,result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix()),f'## M360 已有加载日志解析（2026-10-02）\n\n最大CMA下降位于完整资产SHA阶段、早于DMA分配；七缓冲请求合计33484832B，四权重/一输入/双输出，未证明重复缓冲。最终tokenizer位于语言完成与构造结束之间，需独立检查点；历史稳定/候选非受控A/B。仅离线、无重跑。证据SHA `{digest}`。下一步共用只加载入口的逐SHA/逐分配及对象生命周期对照，不清缓存、不降低64MiB余量。')
    print(json.dumps(dict(status=r['status'],sha256=digest,total_buffer_bytes=sum(sizes),largest_drop=min(stages[1:],key=lambda x:x['delta_bytes']['CmaFree'])['name'])))

if __name__=='__main__':main()
