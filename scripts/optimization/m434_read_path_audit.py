"""Saved-byte and frozen-source audit; never opens a board or model asset."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,sha,atomic,encoded,sync

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior={k:board[k] for k in ('latest_m433_warm_board','latest_m433_warm_closure','latest_m433_warm_failure_interpretation','latest_m430_complete_visual_board','latest_m432_integrated_board')}
    for e in prior.values():
        assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    pkg=BASE/'candidates/M433-late11-complete-request-warm-01'
    manifest=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes())
    for row in manifest['files']:assert sha(pkg/row['path'])==row['sha256'] and (pkg/row['path']).stat().st_size==row['bytes']
    closure=json.loads((pkg/'SOURCE_CLOSURE.json').read_bytes());sources=[]
    for row in closure['files']:
        matches=[p for p in (ROOT/row['path'],ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'/row['path']) if p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']]
        assert matches,'Frozen resolved source unavailable: '+row['path']
        sources.append(dict(row,local_source=matches[0].relative_to(ROOT).as_posix()))
    names=('m238_prefill_runtime','board_runtime','m230_prefill_runtime','ps_vision_runtime','m207_ps_vision_runtime','m261_budgeted_w4_runtime','m260_cached_w4_runtime','m222_vectorized_w4_runtime')
    io_calls=[]
    for name in names:
        path=next(ROOT/r['local_source'] for r in sources if r['path']==closure['modules'][name])
        tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                call=ast.unparse(node.func)
                if any(x in call for x in ('.open','.read','.seek','mmap','_stage','decode','copy_window','fadvise')):
                    io_calls.append(dict(module=name,path=path.relative_to(ROOT).as_posix(),line=node.lineno,call=call))
    dependencies=json.loads((pkg/'DEPENDENCY_CLOSURE.json').read_bytes())['files']
    helper=HERE/'m411_mlp_binding.py';assert sha(helper)==dependencies['m411_mlp_binding']
    for name in ('m433_timed_visual.py','m431_borrowed_visual.py','m430_timed_scope.py','m432_request_visual.py','m433_trials.py'):
        path=pkg/name;sources.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size))
    sources.append(dict(path=helper.relative_to(ROOT).as_posix(),sha256=sha(helper),bytes=helper.stat().st_size))
    plan=json.loads((pkg/'PLAN.json').read_bytes());visual_manifest=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
    assert sha(visual_manifest)==plan['layout_sha256'];visual_layout=json.loads(visual_manifest.read_bytes())
    rows=[]
    for layer in range(13,24):
        for part in ('fc1','fc2'):
            for port,row in enumerate(plan['windows'][str(layer)][part]):
                assert row['path']==f'weights{port}.bin' and row['bytes']==557056 and row['offset']+row['bytes']<=row['file_bytes']
                rows.append(dict(layer=layer,part=part,port=port,path='deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout/'+row['path'],offset=row['offset'],bytes=row['bytes'],file_bytes=row['file_bytes'],window_sha256=row['sha256']))
    assert len(rows)==88 and sum(r['bytes'] for r in rows)==49020928
    layouts={};stage_total=0
    for name,label in (('language','LANGUAGE'),('lmhead','LMHEAD')):
        path=ROOT/f'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/external_assets/weights/{name}_fourport/SIXPORT_LAYOUT_MANIFEST.json'
        contract=ROOT/f'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_{label}_RUNTIME_CONTRACT_RESULT.json'
        c=json.loads(contract.read_bytes());assert sha(path)==c['source_manifest_sha256']
        d=json.loads(path.read_bytes());logical=sum(x['staged_bytes_all_shards'] for x in c['chains']);stage_total+=logical
        layouts[name]=dict(remote='external_assets/weights/'+name+'_fourport',manifest_sha256=sha(path),manifest_local_path=path.relative_to(ROOT).as_posix(),contract_path=contract.relative_to(ROOT).as_posix(),contract_sha256=sha(contract),files=d['files'],total_file_bytes=sum(x['bytes'] for x in d['files']),stages=len(c['chains']),logical_stage_bytes=logical)
    assert stage_total==2034890752
    raw=json.loads((ROOT/prior['latest_m433_warm_board']['result']).read_bytes())
    visual=json.loads((ROOT/prior['latest_m430_complete_visual_board']['result']).read_bytes())
    samples=[dict(index=s['index'],variant=s['variant'],read_bytes=s['io_delta']['read_bytes'],major_fault_delta=s['major_fault_delta'],stages_ms=s['timing']['stages_ms']) for s in raw['samples']]
    vrows=[dict(phase=phase,index=s['index'],variant=s['variant'],read_bytes=s['io_delta']['read_bytes'],major_fault_delta=s['major_fault_delta']) for phase in ('warmup_samples','formal_samples') for s in visual[phase]]
    policy=json.loads((ROOT/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/M261_CACHE_POLICY.json').read_bytes())
    selected_cached=[n for n in policy['selected_names'] if any(n==f'encoder.layers.{i}.mlp.{p}' for i in range(13,24) for p in ('fc1','fc2'))]
    assert selected_cached==['encoder.layers.19.mlp.fc1']
    report='# M434 视觉暂存与语言权重读取路径审计\n\n'
    report+='只读取保存结果、JSON清单和冻结源码；0板端调用、0权重数据读取、0Overlay/模型/新性能样本。M433原FAIL和暖态裁决不改。\n\n'
    report+='候选每条B：TimedVisualProvider → TimedPLRangeScope → PLMLPBinding.forward → BorrowedVisual.stage → m411.stage_windows。第13–23层每层fc1/fc2各暂存一次，每次四个端口，总22 stage/88 open-seek-read。每窗口557,056B，每stage2,228,224B，总49,020,928B（46.75MiB）。没有常驻PS预读slot、缓存命中分支或O_DIRECT；原buffer复制与sync_to_device仍每次执行。全88窗口和SHA见RESULT。\n\n'
    report+='文件为原vision_layout/weights0..3.bin，各43,728,896B。CPU视觉FourPortW4Store持有这些相同文件的只读mmap，构造时全文件SHA；运行M207.forward → M261.decode。26项66,699,264B进程组件缓存只覆盖本范围的layer19.fc1，其余21个MLP投影每次从mmap解码。B绕开这22个CPU Linear，改为普通文件窗口读到原CMA；两个消费者仍共享同一文件的内核页缓存。固定代码没有逐请求全文件哈希、缓存驱逐或清缓存操作。board_runtime.copy_to_buffer虽含旧fadvise分支，但staged-low-cma实际只调用copy_window_to_buffer，不会走该分支。\n\n'
    report+='语言每次完整159-token Prefill：M238.language_family_many在进入T32循环前_stage一次，共154family；保护重试复用已暂存权重。LM head另8chain各_stage一次。共162stage/648文件窗口读；_stage → copy_window_to_buffer以buffering=0的普通读取、seek到chain_window偏移，循环读最多16MiB块并复制同步原四DMA。没有跨请求常驻权重缓存。语言四文件1,828,839,424B，head四文件206,632,960B；精确当前发布manifest分别12ea4b8…、a1a55570…，不是较早artifacts目录的其他SHA版本。两者总2,035,472,384B，逻辑暂存2,034,890,752B；与visual文件不同。\n\n'
    report+='|保存请求|版|read_bytes MiB|major faults|视觉s|语言Prefill s（含head）|\n|---|---|---:|---:|---:|---:|\n'
    for s in samples:report+=f'|M433预热{s["index"]}|{s["variant"]}|{s["read_bytes"]/(1<<20):.6f}|{s["major_fault_delta"]}|{s["stages_ms"]["vision"]/1000:.6f}|{s["stages_ms"]["prefill"]/1000:.6f}|\n'
    report+='\nM430仅视觉：第2条B预热起到全部8条正式A/B，read_bytes和major faults均0。这直接说明同一视觉暂存读取曾命中缓存；不能说46.75MiB暂存必然每请求读盘。M433加入语言后第3条B仍49.855469MiB存储读取、major faults0，显示二者不是同一指标。原59个io_events只是加载期SHA/内存记录，没有请求内按文件read_bytes，22个staging只记逻辑bytes和elapsed_ns。因此现有证据不能归因这49.855469MiB，也不能证明语言页被视觉挤出。\n\n'
    report+='首次加载与每次请求的边界：全文件完整性校验、PS store mmap与provider窗口/矩阵校验仅构造时执行；CPU mmap解码（除选择的组件缓存）/候选22暂存/语言162暂存每次请求发生。后者是否访问存储，取决于当时内核缓存驻留，不由read调用次数决定。普通read可以发生存储I/O且major faults=0。\n\n'
    report+='下一项只做有固定终点的窄观察：同一原完整runtime、原七DMA驻留，固定两个B诊断请求；不做A/B性能裁决、不要求全缓存、不自动加预热。记录22暂存中88次实际read窗口、语言/head648次窗口的进程read_bytes增量，CPU视觉decode的独立区间；在请求前/视觉后/语言后记录12个权重文件的权限有效mincore驻留位图差分，以区分语言页在视觉期间的增减。数值/事务/重试/释放继续核对，记录时序仅诊断，不能作性能。观察器正例/身份/错误/恢复和Linux权限先通过；失败停止扩大。若两次观察不足，则保留未证实，不能再循环直到某结论成立。\n\n'
    report+='若观测为首次读后缓存命中，后续协议应明确有限预热终点；若相同窗口在连续请求持续读盘，应将这些I/O保留在真实请求计时中，并预先固定样本/顺序/统计，不删除读盘样本或沿用不可维持的零I/O门槛。当前不冻结任何新性能阈值，也不重跑M433。\n\n'
    report+='依据：[Linux进程I/O统计](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html)、[mincore快照语义](https://man7.org/linux/man-pages/man2/mincore.2.html)、[Linux5.15权限保护分支](https://github.com/torvalds/linux/blob/v5.15/mm/mincore.c)。rchar是read系统调用返回量；read_bytes是进程计账的存储层读取量，需记录块设备/文件系统并考虑预读和并发归因。mincore仅时刻驻留快照；必须核euid与owner/有效权限，不能将受保护的全1结果当真实驻留。\n'
    result=dict(status='PASS_M434_OFFLINE_READ_PATH_AUDIT_ONLY',prerequisites=prior,manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),source_sha256=sha(HERE/'m434_read_path_audit.py'),verified_sources=sources,read_calls=io_calls,visual_windows=rows,visual_per_request_stages=22,visual_per_request_reads=88,visual_per_request_logical_bytes=49020928,visual_total_file_bytes=sum(x['bytes'] for x in visual_layout['files']),visual_manifest_sha256=sha(visual_manifest),selected_MLP_PS_component_cache=selected_cached,language_layouts=layouts,language_per_request_stages=162,language_per_request_reads=648,language_per_request_logical_bytes=stage_total,M433_saved_samples=samples,M430_saved_IO=vrows,actual_disk_attribution_proven=False,language_cache_eviction_proven=False,initial_only_or_recurring_storage_read_proven=False,board_calls=0,weight_data_read=0,performance_pass=False,production_promoted=False,temperature_measurement_enabled=False)
    folder=BASE/'runs/M434-read-path-audit-01';out=folder/'RESULT.json';atomic(out,encoded(result),immutable=True);atomic(folder/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m434_read_path_audit',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),actual_disk_attribution_proven=False,board_run=False),f'## M434 22视觉暂存及语言读取路径审计（2026-10-07）\n\nSHA {sha(out)}；冻结当前源码/当前发布manifest同SHA，0板端/权重数据读取。B每请求22stage/88普通窗口read共46.75MiB，与CPU mmap同4视觉文件；仅layer19.fc1属26项PS组件缓存。语言/head154+8stage/648read逻辑2,034,890,752B，当前文件总2,035,472,384B。M430纯视觉后续零读盘，M433第3预热49.855469MiB未按文件归因；不能证明视觉来源、语言驱逐或持续I/O。原M433关闭不改；下一步仅固定两个B的窄文件I/O+权限有效驻留观察，数值/原七DMA/释放保持，不做新性能或测温。详见REPORT。')
    print('M434_AUDIT_SYNC',sha(out))

if __name__=='__main__':main()
