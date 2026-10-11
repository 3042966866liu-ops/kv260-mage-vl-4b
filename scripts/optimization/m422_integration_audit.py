"""Offline shared-buffer geometry and ownership audit, after M421 closure only."""
import ast,json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync

def method(source,cls,name):
    c=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name==cls)
    n=next(n for n in c.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return ast.get_source_segment(source,n)

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior={}
    for key in ('latest_m420_combination_board','latest_m420_combination_closure','latest_m421_saved_language_board','latest_m421_saved_language_closure'):
        e=b[key];assert sha(ROOT/e['result'])==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'));prior[key]=e
    language=json.loads((ROOT/prior['latest_m421_saved_language_board']['result']).read_bytes());assert language['status']=='PASS_M421_SAVED_FEATURE_DECISION_CONSISTENCY' and not language['gate_return_code']
    pkt=BASE/'candidates/M421-combination-saved-language-01';closure=json.loads((pkt/'SOURCE_CLOSURE.json').read_bytes());release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7';files={x['path']:x for x in closure['files']};sources={};identities={}
    for name in ('board_runtime','m238_prefill_runtime','m230_prefill_runtime'):
        p=release/closure['modules'][name];assert sha(p)==files[closure['modules'][name]]['sha256'];sources[name]=p.read_text(encoding='utf-8-sig');identities[name]=dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))
    stage=method(sources['board_runtime'],'M120BoardRuntime','_stage');program=method(sources['m230_prefill_runtime'],'M230PrefillRuntime','_program_static_registers');family=method(sources['m238_prefill_runtime'],'M238PrefillRuntime','language_family_many')
    assert 'copy_window_to_buffer' in stage and 'cached' not in stage
    assert '_programmed_weight_addresses' in program and '_programmed_config' in program
    assert 'ThreadPoolExecutor(max_workers=1' in family and 'for buffer_index in sorted(pending_by_buffer)' in family and family.index('for buffer_index in sorted(pending_by_buffer)')<family.index('return targets')
    rows=[];total_stage=0;visual_calls=0
    sizes=[x['bytes'] for x in language['allocated_buffers']];assert sizes==[6963200]*4+[389152,2621440,2621440]
    for index,pkg in ((12,'M410-visual-linear-01'),(13,'M418-visual-linear-01')):
        p=BASE/'candidates'/pkg/'BOARD_CASES.json';m=json.loads((p.parent/'PACKAGE_MANIFEST.json').read_bytes());assert sha(p)==next(x['sha256'] for x in m['files'] if x['path']==p.name)
        cases=json.loads(p.read_bytes())['cases']
        for kind in ('Chain','Descriptor'):
            r=cases[kind];c=r['chain'];part=r['part'];stage_bytes=sum(x['bytes'] for x in r['windows']);assert max(x['bytes'] for x in r['windows'])<=min(sizes[:4]) and c['input_bytes']<=sizes[4] and c['output_bytes']<=min(sizes[5:])
            rows.append(dict(layer=index,part=part,weight_bytes_each=max(x['bytes'] for x in r['windows']),input_bytes=c['input_bytes'],output_bytes=c['output_bytes'],T32_batches=13,descriptors=c['descriptor_count'],stage_bytes=stage_bytes,case_sha256=sha(p)))
            total_stage+=stage_bytes;visual_calls+=13
    assert total_stage==8912896 and visual_calls==52
    v=dict(status='PASS_M422_OFFLINE_SHARED_DMA_GEOMETRY_AUDIT_ONLY',prerequisites=prior,sources=identities,existing_DMA_sizes=sizes,existing_DMA_payload_bytes=sum(sizes),extra_DMA_planned=0,visual_contracts=rows,additional_visual_logical_calls=52,additional_visual_weight_staging_bytes=total_stage,
        cache_switch_requirements=['Invalidate _programmed_weight_addresses and _programmed_config on every visual-to-language handoff, including failure.','Original _stage unconditionally rewrites each language weight window; preserve that behavior and accounting.','Before visual submission require original family parse/pack context fully returned, both output buffers no pending readers, and same-overlay completion proof.'],
        ownership_requirements=['Borrow all seven existing buffers without allocate/free/Overlay operations.','Visual adapter records transactions separately; original language counters remain exact.','Use same StagePolicy active/ever/completed state; on unproven completion retain original engine, buffer owners and process.','Restore only instance methods and static-register cache state in adapter exit; original engine remains sole buffer release owner.','Seal public allocation after original seven; ordinary PS budget unchanged; no fixed64MiB CMA floor.'],
        numerical_before_timing=['One fixed original and one integrated12+13 request, same input/159IDs/weights.','Original visual and all logits/72KV/counters exact saved A; integrated candidate feature and all language outputs exact saved M420/M421 B, not only final decision.','Record52 visual calls separately from778 language logical calls, actual retries and total physical transactions.','Check all geometry, release and stable restore; synchronize raw/BOARD/CURRENT/docs before timing.'],
        performance_protocol_required=True,warm_cache_protocol_note='Reuse existing bounded warm-request principle: fixed prewarm, ABBA+BAAB formal order, read_bytes/faults/cache/environment recorded, no sample deletion or add-until-pass. Freeze exact eligibility and decision before running, use hashes outside timing.',
        board_run=False,borrowed_DMA_adapter_implemented=False,integrated_numerical_pass=False,capacity_proven=False,complete_request_performance_pass=False,expanded_24_layers=False,production_changed=False,
        next_concrete_step='Implement default-off borrowed-buffer adapter and CPU ownership/cache-switch failure tests; then one integrated fixed-request numerical gate before complete-request timing. No extra DMA and no new layer expansion.')
    report='# M422 双层视觉接完整请求：原七块DMA复用审计\n\n只读冻结源码和已有结果；不是已接入或上板PASS。\n\n|资源|视觉最大请求|现有语言缓冲|\n|---|---:|---:|\n|四端口权重，各|557056B|6963200B|\n|输入|163856B|389152B|\n|两个输出，各|524288B|2621440B|\n\n几何上全部容纳，计划0额外DMA。视觉12＋13共52次逻辑调用、8912896B权重暂存；778次语言逻辑保持。物理按实际缩放重试另计。容纳几何不代表实际集成已经数值或容量通过。\n\n原 `_stage` 每次都会重新写语言权重窗口；静态寄存器缓存必须在视觉→语言切换时失效，否则缓存值可能与视觉写过的硬件配置不一致。原M238每family退出前收齐pending解析并离开两个worker上下文；借用只能在其完全返回且DMA合法完成后进行。原engine仍为唯一缓冲释放owner，借用adapter不分配、释放或切Overlay。\n\n先用CPU故障组件检查所有权、封锁分配和缓存恢复，再进行一次完整集成数值门禁，候选必须匹配M420特征和M421完整语言结果。该证明完成后才能冻结暖态完整请求性能协议。没有扩大到24层或改变服务。\n'
    out=BASE/'runs/M422-integration-audit-01/RESULT.json';atomic(out,encoded(v),immutable=True);atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m422_shared_DMA_integration_audit',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),extra_DMA_planned=0,board_run=False,performance_pass=False),f'## M422 两层视觉完整请求资源复用审计（2026-10-06）\n\nSHA {sha(out)}；由实际最终SOURCE_CLOSURE定位的原_stage/M238排空/静态寄存器缓存核对，四Linear最大557056B权重/163856B输入/524288B输出均小于原七DMA，计划0新增；52视觉逻辑＋778语言分开统计，额外暂存8912896B。仅离线几何及所有权设计，尚未adapter/实际容量/集成数值/性能；下一步默认关借用组件及故障检查，再完整请求数值，最后固定暖态对照。保持12＋13、原服务和64MiB普通PS余量。')
    print('M422_INTEGRATION_AUDIT_SYNC',sha(out))
if __name__=='__main__':main()
