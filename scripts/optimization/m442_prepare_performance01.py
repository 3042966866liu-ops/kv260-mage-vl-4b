"""Independent same-M441 parser-only A/B, after the actual new video gate."""
import ast,json
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
from m442_component_workflow01 import manifest
from m442_prepare_text01 import once

def main():
    video=BASE/'runs/M442-live-parser-video-board-01/BOARD_RESULT.json';v=json.loads(video.read_bytes());vd=sha(video)
    assert v['status']=='PASS_M442V_INTEGRATED_VIDEO_NUMERICAL' and v['numerical_pass'] and v['safe_buffers_released'] and not v['unsafe_buffers_retained']
    assert all(vd in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    pkg=BASE/'candidates/M442-complete-request-parser-01';boot=BASE/'candidates/M442-complete-request-parser-transfer-01';old=BASE/'candidates/M441-complete-request-performance-17'
    assert not pkg.exists() and not boot.exists()
    pkg.mkdir(parents=True)
    protocol=dict(schema='m442-same-kernel-parser-natural-IO-v1',ORDER='ABBAABBABAAB',preconditioning='ABBA',formal='ABBABAAB',formal_pairs=[[1,2],[4,3],[6,5],[7,8]],sequence_budget_s=3600,request_budget_s=240,original_parser_sha256='d8061b561fe4d2a089523fde0d3860684244e76bca9646f255f03134fb50be56',candidate_parser_sha256=v['parser_candidate_sha256'],kernel_build_both='0x4D343431',request_video_prerequisite_sha256=vd,physical_transactions=12805,PL_switches=0,extra_DMA=0,single_parser=True,PS_prefetch=False,natural_IO_all_samples_retained=True,pass_rule='Both ABBA/BAAB positive net gain AND paired df3 95percent lower bound positive; no additional samples or posthoc selection',timer='Original stream total: complete weight I/O/staging/parser/vision/prefill/head; parser binding and endpoint full SHA outside timer',production_promotion=False)
    atomic(pkg/'WARM_PROTOCOL.json',encoded(protocol),immutable=True)
    perf=json.loads((old/'PERFORMANCE_PLAN.json').read_bytes());perf.update(protocol_sha256=sha(pkg/'WARM_PROTOCOL.json'),m441_video_sha256=vd)
    atomic(pkg/'PERFORMANCE_PLAN.json',encoded(perf),immutable=True)
    text=BASE/'runs/M442-live-parser-text-board-01/BOARD_RESULT.json';td=sha(text);oldtd=sha(old/'STAGE_PREREQUISITE.json')
    for row in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        src=old/row['path'];assert sha(src)==row['sha256']
        if row['path'] in ('SHA256SUMS','m441_performance_assemble.py','m441_kernel_switch15.py','PERFORMANCE_PLAN.json','WARM_PROTOCOL.json'):continue
        data=src.read_bytes()
        if row['path']=='M441_VIDEO_PREREQUISITE.json':data=video.read_bytes()
        elif row['path']=='STAGE_PREREQUISITE.json':data=text.read_bytes()
        elif row['path'].endswith(('.py','.sh')):
            s=data.decode('utf-8').replace('/home/ubuntu/m441_complete_request_evidence_17','/home/ubuntu/m442_complete_request_parser_evidence_01').replace('M441P','M442P').replace('same-visual-kernel-complete-request-performance','same-visual-same-kernel-parser-complete-request-performance')
            if row['path']=='m441_performance_gate.py':
                s=s.replace(oldtd,td).replace('PASS_M441T_FIXED_TEXT_DIAGNOSTIC','PASS_M442T_FIXED_TEXT_DIAGNOSTIC').replace('PASS_M441V_INTEGRATED_VIDEO_NUMERICAL','PASS_M442V_INTEGRATED_VIDEO_NUMERICAL')
                s=s.replace('same-late11-two-kernels-full-request','same-late11-same-M441-two-parsers-full-request')
                s=once(s,'        board_cls = m243_video_server.M238PrefillRuntime',"        board_cls = m243_video_server.M238PrefillRuntime\n        from m442_runtime_adapter02 import make_candidate_runtime_class\n        make_candidate_runtime_class(board_cls)\n        result['parser_component_sha256']=sha256(HERE/'PARSER_COMPONENT.json')\n        if result['parser_component_sha256']!='"+v['parser_component_sha256']+"':raise RuntimeError('Actual parser component differs before Overlay')\n        result['parser_source_checked_before_overlay']=True")
                begin=s.index('        from m441_kernel_switch15 import KernelSwitch');end=s.index('        run(engine,runtime,policy',begin)
                s=s[:begin]+"        from m442_parser_switch01 import ParserSwitch\n        switch=ParserSwitch(runtime,policy,base,result,m243_video_server.M238PrefillRuntime.__bases__[0],patch,enabled=True)\n"+s[end:]
                # OwnedBoard derives from the exact accepted M238 class; capture it before constructor patch.
                s=s.replace('m243_video_server.M238PrefillRuntime.__bases__[0],patch','board_cls,patch')
                s=s.replace('Four fixed ABBA preconditioning plus eight ABBABAAB formal streams with natural I/O; original seven DMA resident, no additional DMA/slot or other optimization','Four ABBA preconditioning plus eight ABBABAAB formal streams: A accepted parser/B fused parser06 on same M441 and same late11 visual; seven DMA resident; no other optimization')
                assert 'KernelSwitch' not in s and 'switch_environment' not in s
            elif row['path']=='m441_performance_trials.py':
                s=once(s,'        switch.select(variant,n+1)',"        if provider.current_owner is not None or not policy.safe():raise RuntimeError('Previous visual/request owner retained before parser binding')\n        switch.select(variant,n+1)")
                s=once(s,"expected_build='0x4D333537' if variant=='A' else '0x4D343431'","expected_build='0x4D343431'")
                s=once(s,"sample=dict(index=n+1,variant=variant,kernel_build=expected_build,", "sample=dict(index=n+1,variant=variant,parser_sha256=switch.result['parser_selections'][-1]['parser_sha256'],kernel_build=expected_build,")
            data=s.encode('utf-8')
        atomic(pkg/row['path'],data,immutable=True)
    for name in ('m442_runtime_adapter02.py','m442_output_parser06.py','PARSER_COMPONENT.json'):atomic(pkg/name,(BASE/'candidates/M442-live-parser-layer-01'/name).read_bytes(),immutable=True)
    atomic(pkg/'m442_parser_switch01.py',(HERE/'m442_parser_switch01.py').read_bytes(),immutable=True)
    for p in pkg.glob('*.py'):ast.parse(p.read_bytes(),feature_version=(3,10))
    spec=manifest(pkg,'m442-same-M441-parser-full-request-natural-IO-v1');boot.mkdir(parents=True)
    transfer=(HERE/'m441_transfer.py').read_text(encoding='utf-8');transfer=once(transfer,"DESTINATION=Path('/home/ubuntu/m441_candidate_01')","DESTINATION=Path('/home/ubuntu/m442_complete_request_parser_01')");transfer=once(transfer,"EVIDENCE=Path('/home/ubuntu/m441_transfer_evidence_01')","EVIDENCE=Path('/home/ubuntu/m442_complete_request_parser_transfer_evidence_01')")
    atomic(boot/'m442_transfer01.py',transfer.encode(),immutable=True)
    rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(pkg/'PACKAGE_MANIFEST.json').stat().st_size,sha256=sha(pkg/'PACKAGE_MANIFEST.json'))]+spec['files']
    atomic(boot/'TRANSPORT_MANIFEST.json',encoded(dict(schema='m441-specific-peer-transfer-v1',package_manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))),immutable=True)
    atomic(boot/'run_m442_transfer.sh',(BASE/'candidates/M442-live-parser-transfer-01/run_m442_transfer.sh').read_bytes(),immutable=True);manifest(boot,'m442-parser-performance-specific-peer-bootstrap')
    decoder=(HERE/'m441_performance_collect17.py').read_text(encoding='utf-8');decoder=decoder[:decoder.index('\ndef collect(log):')]
    begin=decoder.index('from m441_cma_ledger15');end=decoder.index('def check(r):',begin);decoder=decoder[:begin]+decoder[end:]
    decoder=decoder.replace('M441-complete-request-performance-17','M442-complete-request-parser-01').replace('M441-complete-request-performance-board-17','M442-complete-request-parser-board-01').replace('M441P','M442P').replace('same-visual-kernel-complete-request-performance','same-visual-same-kernel-parser-complete-request-performance').replace('12813','12805')
    decoder=once(decoder,'        verify_ledger(r)',"        if r.get('configuration_CMA_ledger')!=[] or r.get('configuration_CMA_rejected') or r.get('kernel_transitions')!=[] or r.get('kernel_switch_environment')!=[] or r.get('kernel_switch_minimal_attempts')!=0:raise ValueError('Parser-only test programmed or credited FPGA configuration')")
    decoder=decoder.replace("        numerical=json.loads", "        if r.get('parser_source_checked_before_overlay') is not True or r.get('parser_component_sha256')!=sha(PKG/'PARSER_COMPONENT.json'):raise ValueError('Parser source/component prerequisite missing before Overlay')\n        numerical=json.loads",1)
    decoder=once(decoder,"expected_build=0x4d333537 if s['variant']=='A' else 0x4d343431","expected_build=0x4d343431")
    decoder=once(decoder,"            sequence.before(i);sequence.record(s)","            if s.get('parser_sha256')!=(r['parser_original_sha256'] if s['variant']=='A' else r['parser_candidate_sha256']):raise ValueError('Sample parser identity differs')\n            sequence.before(i);sequence.record(s)")
    begin=decoder.index("        switches=[(1,'A')");end=decoder.index("        proof=r['same_overlay_minimal_proof']",begin)
    selector="""        selections=r.get('parser_selections',[])
        if len(selections)!=12 or r.get('parser_original_sha256')!='d8061b561fe4d2a089523fde0d3860684244e76bca9646f255f03134fb50be56' or r.get('parser_candidate_sha256')!=sha(PKG/'m442_output_parser06.py') or r.get('parser_workers')!=1:raise ValueError('Exact two parser identities required')
        identities=selections[0]['buffer_ids'];addresses=selections[0]['buffer_addresses']
        if len(set(identities))!=7 or any(type(x) is not int or x<=0 for x in identities) or addresses!=[x['address'] for x in r['allocated_buffers']]:raise ValueError('Seven original addresses/identities differ')
        for index,(row,sample) in enumerate(zip(selections,samples),1):
            if row['index']!=index or row['variant']!=sample['variant'] or row['parser_sha256']!=sample['parser_sha256'] or row['buffer_ids']!=identities or row['buffer_addresses']!=addresses:raise ValueError('Parser binding sequence/owner differs')
            if any(row.get(k) is not True for k in ('completed','original_buffer_identities_preserved','outside_request_timer')) or any(row.get(k)!=0 for k in ('extra_DMA','overlay_loads','fpga_transactions')) or row.get('parser_workers')!=1 or not safe_to_release(row['completed_snapshot']) or row['completed_snapshot']['ap_return']!=0x4d343431:raise ValueError('Parser boundary unsafe')
"""
    decoder=decoder[:begin]+selector+decoder[end:]
    atomic(HERE/'m442_performance_decoder01.py',decoder.encode('utf-8'),immutable=True)
    workflow=(HERE/'m442_video_workflow01.py').read_text(encoding='utf-8')
    for a,b in [('M442-live-parser-video','M442-complete-request-parser'),('m442_video_decoder01','m442_performance_decoder01'),('latest_m442_live_parser_video','latest_m442_complete_request_parser')]:workflow=workflow.replace(a,b)
    workflow=workflow.replace('M442新解析固定159视频裁决','M442新解析完整请求测量回收').replace('非完整请求收益，失败只本级。','固定4＋8全部原样本；测量回收尚非提速裁决，不删样本/不加测。')
    workflow=once(workflow,"    return r['gate_return_code']","    from m442_close_performance01 import main as close\n    close()\n    return r['gate_return_code']")
    atomic(HERE/'m442_performance_workflow01.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m442_video_control01.ps1').read_text(encoding='utf-8')
    for a,b in [('M442-live-parser-video','M442-complete-request-parser'),('m442_video_workflow01','m442_performance_workflow01'),('/home/ubuntu/m442_live_parser_video','/home/ubuntu/m442_complete_request_parser'),('tmp/m442_video01','tmp/m442_performance01'),('run_m441_video.sh','run_m441_performance.sh'),('M442V_ENABLE_INTEGRATED_VIDEO','M442P_ENABLE_INTEGRATED_VIDEO'),('-TimeoutSeconds 1500','-TimeoutSeconds 4300')]:control=control.replace(a,b)
    control=once(control,'$taskSHA=$taskPrep.manifest_sha256',"$taskSHA=$taskPrep.manifest_sha256\n$taskSupportPath=Join-Path $taskBase 'runs/M442-complete-request-parser-support-01/RESULT.json'\nRequire-Sync $taskSupportPath\n$taskSupport=Get-Content $taskSupportPath -Raw -Encoding UTF8|ConvertFrom-Json\nif($taskSupport.status -ne 'PASS_M442_PARSER_COMPLETE_REQUEST_SUPPORT01' -or $taskSupport.manifest_sha256 -ne $taskSHA){throw 'Actual frozen support prerequisite differs'}")
    atomic(HERE/'m442_performance_control01.ps1',control.encode('utf-8'),immutable=True)
    closer=(HERE/'m441_close_performance17.py').read_text(encoding='utf-8')
    for a,b in [('m441_performance_collect17','m442_performance_decoder01'),('latest_m441_complete_request_board','latest_m442_complete_request_parser_board'),('latest_m441_complete_request_closure','latest_m442_complete_request_parser_closure'),('M441-complete-request-closure-17','M442-complete-request-parser-closure-01'),('m441_close_performance17','m442_close_performance01'),('PASS_M441P','PASS_M442P'),('M441 同视觉','M442 同核解析'),('A original M357 vs B new M441 kernel, single parser.','A accepted M236 parser vs B fused parser06 on identical M441 kernel, single parser.'),('M437_CLOSURE_SYNC','M442_CLOSURE_SYNC'),('本轮只评价M441增量收益','本轮只评价M442解析增量收益'),('2026-10-09','2026-10-10')]:closer=closer.replace(a,b)
    begin=closer.index("    report+='A为原M357");end=closer.index('\n',begin)
    closer=closer[:begin]+"    report+='A使用原M236解析；B使用06融合解析，两边同一个M441硬件、13–23层PL视觉、同完整权重数学/输入/提示/原语言调度及七块驻留DMA。只在计时外绑定解析函数，无请求间Overlay切换或额外最小事务。温度不读取。原计时内包含全部读取、暂存、解析、视觉、语言和head；全特征/logits/72份KV/事务哈希计时后核对。\\n\\n'"+closer[end:]
    atomic(HERE/'m442_close_performance01.py',closer.encode('utf-8'),immutable=True)
    for p in (HERE/'m442_performance_workflow01.py',HERE/'m442_performance_decoder01.py'):ast.parse(p.read_bytes(),feature_version=(3,10))
    result=dict(status='PREPARED_M442_SAME_KERNEL_PARSER_COMPLETE_REQUEST01',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),bootstrap_manifest_sha256=sha(boot/'PACKAGE_MANIFEST.json'),prior_video_raw_sha256=vd,protocol_sha256=sha(pkg/'WARM_PROTOCOL.json'),build_id='0x4D343431',physical_transactions=12805,PL_switches=0,extra_DMA=0,board=False,performance=False,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (HERE/'m442_performance_workflow01.py',HERE/'m442_performance_decoder01.py',HERE/'m442_performance_control01.ps1',Path(__file__))])
    out=BASE/'runs/M442-complete-request-parser-preparation-01/RESULT.json';atomic(out,encoded(result),immutable=True)
    sync('latest_m442_complete_request_parser_preparation',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False),'## M442同核解析完整请求冻结01（2026-10-10）\n\nSHA '+sha(out)+'；原4ABBA＋8ABBABAAB自然I/O，同M441硬件/后11层视觉/原权重数学/七DMA/单parser；仅计时外选择原解析与06新解析。12805物理、0切核/配置ledger、原CMA基线严格不重置；计时内全读取暂存解析视觉语言head，数值SHA计时后核对。支持通过后一次完整测试，不据组件外推、不晋级。')
    print(result['status'],sha(out))
if __name__=='__main__':main()
