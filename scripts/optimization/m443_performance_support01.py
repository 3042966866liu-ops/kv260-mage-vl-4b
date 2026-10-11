"""Explicit offline fixtures exercise the real full-request collector and switch."""
import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import m351_workflow as w
from m441_host_io08 import atomic
from m443_transfer import verify_directory


def emit(r):
    raw=(json.dumps(r,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8');chunks=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M443P_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM443P_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M443P_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(chunks))+f'M443P_DONE gate_rc={r["gate_return_code"]} export_rc=0\n'


def support():
    w.atomic=atomic
    import m443_performance_collect01 as c
    from m443_prepare_performance01 import builds
    verify_directory(c.PKG,w.sha(c.PKG/'PACKAGE_MANIFEST.json'))
    prep_path=w.BASE/'runs/M443-complete-request-performance-preparation-01/RESULT.json';prep=json.loads(prep_path.read_bytes())
    # The actual new switch has ordinary NumPy buffers and explicit fake Overlay/DMA only.
    sys.path.insert(0,str(c.PKG))
    source=builds((w.HERE/'test_m441_kernel_switch09.py').read_text(encoding='utf-8')).replace('m441_kernel_switch09','m443_kernel_switch01').replace('M441-kernel-switch-component-09','M443-kernel-switch-component-01').replace('PASS_M441_KERNEL_SWITCH_CPU_COMPONENT_ONLY','PASS_M443_KERNEL_SWITCH_CPU_COMPONENT_ONLY').replace('latest_m441_kernel_switch_component','latest_m443_kernel_switch_component01')
    source=source.replace('def loader(path):overlays.append(path);return overlay','def loader(path,*,download):\n            assert download is True;overlays.append(path);return overlay').replace('def broken(path):raise RuntimeError','def broken(path,*,download):raise RuntimeError')
    source=source.replace('policy.safe=lambda:not policy.active and policy.completed','policy.prepare_programming=lambda path,index,variant:None\n        policy.safe=lambda:not policy.active and policy.completed')
    source=source.replace("w.sha(w.HERE/'m443_kernel_switch01.py')","w.sha(c.PKG/'m443_kernel_switch01.py')").replace('## M441 性能隔离核绑定组件09（2026-10-09）','## M443 性能隔离核绑定组件01（2026-10-11）')
    namespace={'__name__':'_explicit_actual_switch_component','c':c};exec(compile(source,'<actual-new-switch-component-fixtures>','exec'),namespace);namespace['component']()
    # Initial configuration guards: actual component source, no layer collector execution.
    source=(w.HERE/'m443_layer_support01.py').read_text(encoding='utf-8');source=source[:source.index('    prep=json.loads(c.PREP.read_bytes())')]
    ns={'__name__':'_explicit_initial_configuration_component'};exec(compile(source,'<actual-wrapper-component-only>','exec'),ns);ns['fixtures']()
    old=w.BASE/'runs/M441-complete-request-performance-board-17/BOARD_RESULT.json';r=json.loads(old.read_bytes())
    assert r['status']=='PASS_M441P_NATURAL_IO_MEASUREMENTS_COLLECTED'
    build=json.loads((c.PKG/'M443_BUILD_CONFIGURATION_PROOF.json').read_bytes());cfg=copy.deepcopy(build['configuration_record'])
    r.update(status='PASS_M443P_NATURAL_IO_MEASUREMENTS_COLLECTED',manifest_sha256=prep['manifest_sha256'],build_id='0x4D343433',prior_board_sha256=prep['prior_raw_sha256'] if 'prior_raw_sha256' in prep else json.loads((c.PKG/'M443_CHAIN_PREREQUISITE.json').read_bytes()).get('raw_sha256',w.sha(c.PKG/'M443_CHAIN_PREREQUISITE.json')),
             configuration_application_build_raw_sha256=prep['configuration_build_raw_sha256'],configuration_record=cfg,configuration_application_accepted=True,unknown_configuration_ownership=False,source_compatibility_checked_before_overlay=True,configuration_driver_sources_checked_before_overlay=True,
             M443_configuration_prerequisite=dict(sha256=prep['configuration_build_raw_sha256'],application_sha256=cfg['application_sha256'],manifest_sha256=prep['candidate_manifest_sha256'],actual_new_bit_application=True,configuration_credits_granted=0),m443_video_numerical_source_sha256=prep['prior_video_raw_sha256'])
    r.pop('CMA14_prerequisite',None);r.pop('m441_video_numerical_source_sha256',None)
    r['same_overlay_minimal_proof']['snapshot']['ap_return']=0x4d343433;r['final_snapshot']['ap_return']=0x4d343433
    for sample in r['samples']:
        b=0x4d343431 if sample['variant']=='A' else 0x4d343433
        sample['kernel_build']=f'0x{b:08X}';sample['final_snapshot']['ap_return']=b;sample['semantic']['proof']['build_id']=f'0x{b:08X}'
    r['warmup_samples']=r['samples'][:4];r['formal_samples']=r['samples'][4:]
    before=0x4d343433
    for row in r['kernel_transitions']:
        b=0x4d343431 if row['variant']=='A' else 0x4d343433
        row.update(from_build=before,to_build=b);row['before_snapshot']['ap_return']=before;row['completed_snapshot']['ap_return']=b;before=b
    for env in r['kernel_switch_environment']:env['manifest_sha256']=prep['baseline_manifest_sha256'] if env['variant']=='A' else prep['candidate_manifest_sha256']
    # Relabeled real trace bytes are explicit offline fixtures, never new board evidence.
    original=r['configuration_CMA_ledger'];baseline=copy.deepcopy(original[0]['before']);records=[]
    for j,row in enumerate(original,1):
        record=copy.deepcopy(row if row['variant']=='A' else cfg);record.update(index=row['index'],variant=row['variant'],pid=cfg['pid'])
        record['bit_sha256']='73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e' if row['variant']=='A' else cfg['bit_sha256']
        if row['variant']=='A':
            record['trace']=copy.deepcopy(next(x for x in original if x['bit_sha256']=='73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e')['trace'])
        record['trace']['trace_text']=re.sub(r'python-\d+\s',lambda m:'python-'+str(cfg['pid'])+' ',record['trace']['trace_text']);record['trace']['pid']=cfg['pid'];record['trace']['trace_sha256']=hashlib.sha256(record['trace']['trace_text'].encode()).hexdigest()
        record['before']={k:v+(j-1)*1904 if k=='reserved:alloc_pages_success' else v for k,v in baseline.items()}
        record['after']={k:v+j*1904 if k=='reserved:alloc_pages_success' else v for k,v in baseline.items()}
        record.update(verified_released_configuration_pages={'reserved:alloc_pages_success':1904},cumulative_verified_credits={'reserved:alloc_pages_success':j*1904},original_baseline_unchanged=copy.deepcopy(baseline))
        records.append(record)
    r['configuration_CMA_ledger']=records
    assert c.decode(emit(r))[2]==r
    failed=dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['explicit unknown switch fixture'],unsafe_buffers_retained=True,safe_buffers_released=False)
    assert c.decode(emit(failed))[2]==failed
    mutations=[('manifest_sha256','0'*64),('build_id','0x4D343431'),('all12_requests_completed',False),('fpga_transactions',12805),('logical_calls',1),('original_buffer_release_count',6),('released_buffers',[]),('safe_buffers_released',False),('stable_overlay_reloaded',False),('unsafe_buffers_retained',True),('numerical_pass',False),('performance_pass',True),('formal_promotion_allowed',True),('temperature_measurement_enabled',True),('additional_cma_requests_allowed',True),('head_AST_checked_before_overlay',False),('full_hashes_after_timers',False),('configuration_application_accepted',False),('unknown_configuration_ownership',True),('source_compatibility_checked_before_overlay',False),('configuration_application_build_raw_sha256','0'*64),('kernel_switch_minimal_attempts',7),('vision_forward_calls',11),('configuration_CMA_ledger',records[:-1]),('samples',r['samples'][:-1])]
    mutations.append(('configuration_driver_sources_checked_before_overlay',False))
    negatives=[emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('SAVED_GATE_RC=0','SAVED_GATE_RC=1'),emit(r).replace('export_rc=0','export_rc=1')]
    for key,value in mutations:bad=copy.deepcopy(r);bad[key]=value;negatives.append(emit(bad))
    for key,value in [('kernel_build','0x4D333537'),('language_physical_observed',780),('numerical_SHA_after_timer',{}),('exact_saved_reference',{'full':False}),('physical_record_SHA_after_timer','0'*64),('visual_staging',[]),('original_seven_DMA_still_resident',False)]:
        bad=copy.deepcopy(r);bad['samples'][4][key]=value;bad['formal_samples']=bad['samples'][4:];negatives.append(emit(bad))
    for key,value in [('pid',1),('before',{}),('original_baseline_unchanged',{}),('verified_released_configuration_pages',{}),('cumulative_verified_credits',{}),('bit_sha256','0'*64)]:
        bad=copy.deepcopy(r);bad['configuration_CMA_ledger'][1][key]=value;negatives.append(emit(bad))
    for key,value in [('completed',False),('outside_request_timer',False),('original_buffer_identities_preserved',False),('extra_DMA',1)]:
        bad=copy.deepcopy(r);bad['kernel_transitions'][0][key]=value;negatives.append(emit(bad))
    for text in negatives:
        try:c.decode(text)
        except (AssertionError,KeyError,ValueError,RuntimeError,TypeError):pass
        else:raise AssertionError('Corrupted complete request fixture accepted')
    # The actual original full exporter and decoder, explicit OS-root fixture only.
    spec=importlib.util.spec_from_file_location('explicit_m443_perf_export',c.PKG/'m443_performance_export.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
    folder=w.ROOT/'tmp/m443_performance01/export_fixture';folder.mkdir(parents=True,exist_ok=False);saved=folder/'BOARD_RESULT.json';atomic(saved,(json.dumps(r,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'),immutable=True)
    buf=io.StringIO()
    with patch.object(ex,'OUTPUT',saved),patch.object(ex.os,'geteuid',lambda:0,create=True),patch.object(ex.time,'sleep',lambda unused:None),patch('sys.stdout',buf):ex.emit_saved()
    assert c.decode(buf.getvalue())[2]==r
    control=w.HERE/'m443_performance_control01.ps1'
    cp=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoLogo','-NoProfile','-File',str(control),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert cp.returncode==0 and 'M443P_CONTROL_SELFTEST_PASS' in cp.stdout,cp.stdout+cp.stderr
    # Initial admission and sealed switching compose different exact loaders.
    tree=ast.parse((c.PKG/'m443_performance_gate.py').read_text(encoding='utf-8'));fn=next(x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name=='configuration_overlay')
    ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual-initial-resident-routing>','exec'),ns)
    from types import SimpleNamespace as NS
    calls=[];ns.update(policy=NS(sealed=False),configuration=NS(load=lambda *a,**kw:calls.append(('initial',a,kw))),original_overlay=object(),resident_overlay=lambda *a,**kw:calls.append(('resident',a,kw)))
    ns['configuration_overlay']('exact.bit',download=True);ns['policy'].sealed=True;ns['configuration_overlay']('exact.bit',download=True);assert [x[0] for x in calls]==['initial','resident']
    paths=list(sorted(c.PKG.iterdir()))+[control,w.HERE/'m443_performance_collect01.py',w.HERE/'m443_prepare_performance01.py',w.HERE/'test_m441_kernel_switch09.py',w.HERE/'m443_layer_support01.py',Path(__file__)]
    out=w.BASE/'runs/M443-complete-request-performance-support-01';v=dict(status='PASS_M443_PERFORMANCE_SUPPORT_FIXTURES01',manifest_sha256=prep['manifest_sha256'],preparation_sha256=w.sha(prep_path),explicit_prior_raw_fixture_only=True,prior_fixture_raw_sha256=w.sha(old),collector_negative_checks=len(negatives),actual_new_switch_component_and_unknown_retention_pass=True,initial_configuration_and_resident_loader_routing_pass=True,complete_original_collector_and_exporter_pass=True,original_parser_and_balanced_sequence_unchanged=True,control_parser_and_failure_collection_pass=True,files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in paths],board_executed=False,configuration_credits_granted=0,performance_pass=False,promoted=False)
    for name,raw in [('CONTROL_SELFTEST.stdout.txt',cp.stdout.encode('utf-8')),('CONTROL_SELFTEST.stderr.txt',cp.stderr.encode('utf-8')),('CONTROL_SELFTEST.rc.txt',(str(cp.returncode)+'\n').encode())]:atomic(out/name,raw,immutable=True)
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);s=w.sha(out/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_complete_request_support01',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,manifest_sha256=v['manifest_sha256']),'## M443原完整请求支持组件01（2026-10-11）\n\nSHA '+s+'；明确offline原完整raw重标fixture、'+str(len(negatives))+'完整采集破坏负例、实际新switch/默认禁用/未知保留、实际初始配置guard及sealed原loader组合、原完整exporter及host失败仍Collect检查通过。仅组件，不是板端性能或配置credit。冻结所有控制/输入SHA后才逐SHA上传并唯一固定4+8。')
    print(v['status'],s,len(negatives))


def receipt():
    import m443_performance_collect01 as c
    logs=w.ROOT/'tmp/m443_performance01';a=(logs/'assembly.log').read_text(encoding='utf-8-sig');s=(logs/'upload_syntax.log').read_text(encoding='utf-8-sig')
    assert 'M443P_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a and '__M443P_ASSEMBLY_RC_0__' in a and '__M443P_SYNTAX_RC_0__' in s
    out=w.BASE/'runs/M443-complete-request-performance-transfer-01';v=dict(status='PASS_M443_PERFORMANCE_TRANSFER_ONLY01',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),logs=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(logs.glob('*.log'))],board_executed=False,overlay_loaded=False,performance_pass=False)
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);d=w.sha(out/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_complete_request_transfer01',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=v['manifest_sha256']),'## M443完整请求传输01（2026-10-11）\n\nSHA '+d+'；manifest-first900B及逐SHA/旧精确源组装/root bash-n通过，无请求执行；下一步唯一固定4+8，不补样本。')
    print(v['status'],d)


if __name__=='__main__':
    if sys.argv[1:]==['receipt']:receipt()
    else:support()
