"""Explicit numerical/protocol fixtures for the frozen new video gate; no hardware."""
import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import m351_workflow as w
from m441_host_io08 import atomic
from m443_transfer import verify_directory
import m443_video_collect01 as c


def emit(r):
    raw=w.encoded(r);chunks=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M443V_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM443V_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M443V_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(chunks))+f'M443V_DONE gate_rc={r["gate_return_code"]} export_rc=0\n'


def support():
    verify_directory(c.PKG,w.sha(c.PKG/'PACKAGE_MANIFEST.json'))
    prep_path=w.BASE/'runs/M443-fixed-video-preparation-01/RESULT.json';prep=json.loads(prep_path.read_bytes())
    # Execute the same actual wrapper component guards, excluding all layer decoder/receipts.
    component_source=(w.HERE/'m443_layer_support01.py').read_text(encoding='utf-8')
    component_source=component_source[:component_source.index('    prep=json.loads(c.PREP.read_bytes())')]
    namespace={'__name__':'_explicit_configuration_wrapper_component_only'}
    exec(compile(component_source,'<actual-wrapper-component-guards>','exec'),namespace);namespace['fixtures']()
    old=w.BASE/'runs/M441-fixed-video-board-09/BOARD_RESULT.json';r=json.loads(old.read_bytes())
    assert r['status']=='PASS_M441V_INTEGRATED_VIDEO_NUMERICAL'
    build=json.loads((c.PKG/'M443_BUILD_CONFIGURATION_PROOF.json').read_bytes())
    r.update(status='PASS_M443V_INTEGRATED_VIDEO_NUMERICAL',build_id='0x4D343433',manifest_sha256=prep['manifest_sha256'],
             prior_board_sha256=prep['prior_raw_sha256'],prior_fixed_text_raw_sha256=prep['prior_text_raw_sha256'],
             configuration_application_build_raw_sha256=prep['configuration_build_raw_sha256'],configuration_record=build['configuration_record'],
             configuration_application_accepted=True,unknown_configuration_ownership=False)
    snapshots=[r['final_snapshot'],r['same_overlay_minimal_proof']['snapshot']]+[s['final_snapshot'] for s in r['samples']]+[t['completed_snapshot'] for t in r['visual_transactions']]
    for snapshot in snapshots:snapshot['ap_return']=0x4d343433
    assert c.decode(emit(r))[2]==r
    failed=dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['explicit unknown configuration fixture'],configuration_application_accepted=False,unknown_configuration_ownership=True,safe_buffers_released=False,unsafe_buffers_retained=True)
    assert c.decode(emit(failed))[2]==failed
    mutations=[('manifest_sha256','0'*64),('build_id','0x4D343431'),('model_forward_calls',2),('vision_forward_calls',2),('fpga_transactions',1067),('logical_calls',1556),('transactions',r['transactions'][:-1]),('integrated_boundaries',r['integrated_boundaries'][:-1]),('visual_transactions',r['visual_transactions'][:-1]),('visual_staging',r['visual_staging'][:-1]),('saved_reference_variant','original'),('borrowed_extra_DMA',1),('peak_live_visual_layer_scopes',2),('visual_static_cache_invalidated',False),('safe_buffers_released',False),('unsafe_buffers_retained',True),('source_compatibility_checked_before_overlay',False),('prior_fixed_text_raw_sha256','0'*64),('prior_board_sha256','0'*64),('temperature_measurement_enabled',True),('performance_pass',True),('gate_return_code',False),('configuration_application_accepted',False),('unknown_configuration_ownership',True),('configuration_application_build_raw_sha256','0'*64),('additional_cma_requests_allowed',True),('head_AST_checked_before_overlay',False)]
    negatives=[emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('export_rc=0','export_rc=1'),emit(r).replace('SAVED_GATE_RC=0','SAVED_GATE_RC=1')]
    for key,value in mutations:negatives.append(emit(dict(r,**{key:value})))
    for field in ('keys','values','families','logits','decision','counts'):
        bad=copy.deepcopy(r)
        if isinstance(bad['samples'][0][field],list):bad['samples'][0][field].pop()
        elif field=='logits':bad['samples'][0][field]['sha256']='0'*64
        elif field=='decision':bad['samples'][0][field]['knife_score']=0.1
        else:bad['samples'][0][field]['stage_bytes']-=1
        negatives.append(emit(bad))
    bad=copy.deepcopy(r);bad['visual_transactions'][0]['completed_snapshot']['ap_return']=0;negatives.append(emit(bad))
    for key,value in [('manifest_sha256','0'*64),('bit_sha256','0'*64),('pid',1),('configuration_credits_granted',1904)]:
        bad=copy.deepcopy(r);bad['configuration_record'][key]=value;negatives.append(emit(bad))
    bad=copy.deepcopy(r);bad['configuration_record']['trace']['own_instance_removed']=False;negatives.append(emit(bad))
    for bad in negatives:
        try:c.decode(bad)
        except (ValueError,KeyError,RuntimeError,AssertionError):pass
        else:raise AssertionError('Broken full new video result accepted')
    # Run the actual exporter on an explicit offline prior-raw fixture.
    spec=importlib.util.spec_from_file_location('actual_m443_video_export',c.PKG/'m443_video_export.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
    folder=w.ROOT/'tmp/m443_video01/export_fixture';folder.mkdir(parents=True,exist_ok=False);saved=folder/'BOARD_RESULT.json';atomic(saved,w.encoded(r),immutable=True)
    buf=io.StringIO()
    with patch.object(ex,'OUTPUT',saved),patch.object(ex.os,'geteuid',lambda:0,create=True),patch.object(ex.time,'sleep',lambda unused:None),patch('sys.stdout',buf):ex.emit_saved()
    assert c.decode(buf.getvalue())[2]==r
    try:
        with patch.object(ex.os,'geteuid',lambda:1000,create=True):ex.emit_saved()
    except RuntimeError:pass
    else:raise AssertionError('Exporter accepted non-root')
    # Original one-B dispatch and pre-import provider scope stay exact.
    tree=ast.parse((c.PKG/'m432_trials.py').read_text(encoding='utf-8'))
    loop=next(n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [x.id for x in n.target.elts]==['i','visual'])
    assert eval(compile(ast.Expression(loop.iter),'<original-dispatch>','eval'),{'features':['A','B']})==((1,'B'),)
    tree=ast.parse((c.PKG/'m432_request_visual.py').read_text(encoding='utf-8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef));fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__call__')
    guard=next(n for n in fn.body if isinstance(n,ast.If));test=compile(ast.Expression(guard.test),'<original-provider-guard>','eval')
    from types import SimpleNamespace
    for index,count,rejected in ((1,0,False),(0,0,True),(1,1,True),(2,0,True)):
        assert eval(test,{'index':index,'self':SimpleNamespace(result={'integrated_visual':[None]*count},disposed=False)}) is rejected
    control=w.HERE/'m443_video_control01.ps1'
    tested=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoLogo','-NoProfile','-File',str(control),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert tested.returncode==0 and 'M443V_CONTROL_SELFTEST_PASS' in tested.stdout,tested.stdout+tested.stderr
    paths=list(sorted(c.PKG.iterdir()))+[control,w.HERE/'m443_video_collect01.py',w.HERE/'m443_layer_configuration01.py',w.HERE/'m443_layer_support01.py',Path(__file__)]
    out=w.BASE/'runs/M443-fixed-video-support-01';value=dict(status='PASS_M443_FIXED_VIDEO_SUPPORT_FIXTURES01',manifest_sha256=prep['manifest_sha256'],preparation_sha256=w.sha(prep_path),explicit_prior_raw_fixture_not_new_board_evidence=True,prior_fixture_raw_sha256=w.sha(old),collector_negative_checks=len(negatives),collector_pass_and_unknown_failure_verified=True,actual_exporter_full_decoder_pass=True,actual_one_B_dispatch_and_preimport_guard=True,configuration_wrapper_component_guards_pass=True,unknown_overlay_object_retained=True,allocator_refused_without_actual_proof=True,control_parser_and_failure_collection_pass=True,files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in paths],board_executed=False,performance_pass=False,promoted=False)
    atomic(out/'CONTROL_SELFTEST.stdout.txt',tested.stdout.encode('utf-8'),immutable=True);atomic(out/'CONTROL_SELFTEST.stderr.txt',tested.stderr.encode('utf-8'),immutable=True);atomic(out/'CONTROL_SELFTEST.rc.txt',(str(tested.returncode)+'\n').encode(),immutable=True)
    atomic(out/'RESULT.json',w.encoded(value),immutable=True);s=w.sha(out/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_fixed_video_support01',dict(status=value['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,manifest_sha256=prep['manifest_sha256']),
           '## M443固定视频支持组件01（2026-10-11）\n\nSHA '+s+'；原完整参考明确fixture及'+str(len(negatives))+'采集破坏负例、实际exporter完整字节解码/非root拒绝、原单B及provider前置范围检查、实际新配置wrapper正负例/未知对象保留/分配拒绝、PowerShell失败仍Collect原stdout/stderr/rc0核对。不是新板数值；所有包/host控制/collector精确SHA冻结后才逐SHA上传一次视频。')
    print(value['status'],s,len(negatives))


def receipt():
    logs=w.ROOT/'tmp/m443_video01';a=logs/'assembly.log';s=logs/'upload_syntax.log'
    assert 'M443V_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a.read_text(encoding='utf-8-sig') and '__M443V_ASSEMBLY_RC_0__' in a.read_text(encoding='utf-8-sig')
    assert '__M443V_SYNTAX_RC_0__' in s.read_text(encoding='utf-8-sig')
    out=w.BASE/'runs/M443-fixed-video-transfer-01';value=dict(status='PASS_M443_FIXED_VIDEO_TRANSFER_ONLY01',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),logs=[dict(path=p.relative_to(w.ROOT).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(logs.glob('*.log'))],assembly_whole_whitelist_verified=True,bash_n_pass=True,board_executed=False,overlay_loaded=False,numerical_pass=False,performance_pass=False)
    atomic(out/'RESULT.json',w.encoded(value),immutable=True);d=w.sha(out/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_fixed_video_transfer01',dict(status=value['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),
           '## M443固定159视频传输01（2026-10-11）\n\nSHA '+d+'；manifest-first900B分块及逐SHA上传，已有M441视频/M443文本/原实际proof只精确SHA组装，全成员白名单/root bash-n通过；尚无视频执行。下一步唯一Run，已有attempt只Collect。')
    print(value['status'],d)


if __name__=='__main__':
    if sys.argv[1:]==['receipt']:receipt()
    else:support()
