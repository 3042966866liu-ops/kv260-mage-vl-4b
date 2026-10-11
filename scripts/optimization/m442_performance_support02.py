"""Explicit host fixtures; test the frozen parser selector and raw evidence interface."""
import ast,base64,copy,hashlib,importlib.util,io,json,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
from m441_prepare_layer09 import verify_package
from m437_sequence import ORDER
import m442_performance_decoder01 as c
import m442_parser_switch01 as selector

verify_package(c.PKG)
def parserA(*a):return 'A'
def parserB(*a):return 'B'
class Accepted:_parse_into_and_check=staticmethod(parserA)
class Candidate:_parse_into_and_check=staticmethod(parserB)
buffers=[SimpleNamespace(nbytes=n,address=4096*(i+1)) for i,n in enumerate([6963200]*4+[389152,2621440,2621440])]
rt=SimpleNamespace(staged_buffers=buffers[:4],input_buffer=buffers[4],output_buffer=buffers[5],output_buffer_alt=buffers[6],_parse_into_and_check=parserA,kernel=object(),dma=object())
snapshot=dict(ap_ctrl=4,ap_return=0x4d343431,mm2s_dmasr=4098,s2mm_dmasr=4098,mm2s_idle=True,s2mm_idle=True,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
pol=SimpleNamespace(sealed=True,ever=True,completed=True,active=False,build=0x4d343431,thread=None,safe=lambda:True,capture=lambda *a:None)
base=SimpleNamespace(physical_address=lambda b:b.address,transaction_snapshot=lambda *a:copy.deepcopy(snapshot));result={'released_buffers':[]}
def bind(obj,name,replacement):setattr(obj,name,replacement)
with patch.object(selector,'make_candidate_runtime_class',lambda cls:Candidate):sw=selector.ParserSwitch(rt,pol,base,result,Accepted,bind,enabled=True)
for i,variant in enumerate(ORDER,1):sw.select(variant,i);assert rt._parse_into_and_check()==variant
assert len(result['parser_selections'])==12
def refused(call):
    try:call()
    except RuntimeError:return
    raise AssertionError('Unsafe parser boundary accepted')
# Use a fresh explicit host fixture for actual guards, no model or board.
result2={'released_buffers':[]};rt._parse_into_and_check=parserA
with patch.object(selector,'make_candidate_runtime_class',lambda cls:Candidate):sw2=selector.ParserSwitch(rt,pol,base,result2,Accepted,bind,enabled=True)
for field,value in [('active',True),('completed',False),('sealed',False),('ever',False),('build',0x4d333537)]:
    original=getattr(pol,field);setattr(pol,field,value);refused(lambda:sw2.select('A',1));setattr(pol,field,original)
pol.thread=SimpleNamespace(is_alive=lambda:True);refused(lambda:sw2.select('A',1));pol.thread=None
buffers[0].address+=4096;refused(lambda:sw2.select('A',1));buffers[0].address-=4096
result2['language_scope_active']=True;refused(lambda:sw2.select('A',1));result2['language_scope_active']=False
with patch.object(selector.threading,'enumerate',lambda:[SimpleNamespace(name='m238-parse-fixture')]):refused(lambda:sw2.select('A',1))
refused(lambda:sw2.select('X',1));refused(lambda:sw2.select('A',2))

source=BASE/'runs/M441-complete-request-performance-board-17/BOARD_RESULT.json';r=json.loads(source.read_bytes())
component=sha(c.PKG/'PARSER_COMPONENT.json');plan=json.loads((c.PKG/'PERFORMANCE_PLAN.json').read_bytes())
r.update(status='PASS_M442P_NATURAL_IO_MEASUREMENTS_COLLECTED',manifest_sha256=sha(c.PKG/'PACKAGE_MANIFEST.json'),gate_level='same-visual-same-kernel-parser-complete-request-performance',configuration_CMA_ledger=[],kernel_transitions=[],kernel_switch_environment=[],kernel_switch_minimal_attempts=0,fpga_transactions=12805,parser_original_sha256=selector.ORIGINAL_SHA,parser_candidate_sha256=selector.CANDIDATE_SHA,parser_component_sha256=component,parser_source_checked_before_overlay=True,parser_workers=1,natural_IO_protocol_sha256=plan['protocol_sha256'],m441_video_numerical_source_sha256=plan['m441_video_sha256'])
for s in r['samples']:
    s['kernel_build']='0x4D343431';s['final_snapshot']['ap_return']=0x4d343431;s['parser_sha256']=selector.ORIGINAL_SHA if s['variant']=='A' else selector.CANDIDATE_SHA
r['warmup_samples']=r['samples'][:4];r['formal_samples']=r['samples'][4:]
addresses=[x['address'] for x in r['allocated_buffers']]
r['parser_selections']=[dict(index=i+1,variant=s['variant'],parser_sha256=s['parser_sha256'],completed=True,original_buffer_identities_preserved=True,buffer_ids=list(range(1,8)),buffer_addresses=addresses,completed_snapshot=copy.deepcopy(snapshot),outside_request_timer=True,extra_DMA=0,overlay_loads=0,fpga_transactions=0,parser_workers=1) for i,s in enumerate(r['samples'])]
def raw_bytes(v):return (json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
def emit(v):
    raw=raw_bytes(v);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M442P_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM442P_SAVED_GATE_RC='+str(v['gate_return_code'])+'\n'+''.join(f'M442P_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M442P_DONE gate_rc={v["gate_return_code"]} export_rc=0\n'
assert c.decode(emit(r))[2]==r
assert c.decode(emit(dict(r,status='FAIL',gate_return_code=1,errors=['Explicit saved-byte schema fixture NOT board'])))[2]['gate_return_code']==1
bads=[emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('export_rc=0','export_rc=1')]
for key,value in [('manifest_sha256','0'*64),('gate_level','wrong'),('fpga_transactions',12813),('configuration_CMA_ledger',[{}]),('kernel_transitions',[{}]),('kernel_switch_environment',[{}]),('kernel_switch_minimal_attempts',1),('parser_workers',2),('parser_candidate_sha256','0'*64),('parser_original_sha256','0'*64),('parser_component_sha256','0'*64),('parser_source_checked_before_overlay',False),('all12_requests_completed',False),('safe_buffers_released',False),('unsafe_buffers_retained',True),('additional_cma_requests_allowed',True),('temperature_measurement_enabled',True),('performance_pass',True),('full_hashes_after_timers',False),('completed_language_physical',0),('completed_visual_physical',0)]:bads.append(emit(dict(r,**{key:value})))
for key,value in [('outside_request_timer',False),('overlay_loads',1),('fpga_transactions',1),('parser_sha256','0'*64),('buffer_addresses',[0]*7),('buffer_ids',[1]*7),('completed',False)]:
    b=copy.deepcopy(r);b['parser_selections'][3][key]=value;bads.append(emit(b))
for log in bads:
    try:c.decode(log)
    except (ValueError,RuntimeError,AssertionError,KeyError):pass
    else:raise AssertionError('Invalid full-request fixture accepted')
spec=importlib.util.spec_from_file_location('actual_m442_performance_export',c.PKG/'m441_performance_export.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
folder=ROOT/'tmp/m442_performance01/export_fixture';folder.mkdir(parents=True,exist_ok=False);saved=folder/'BOARD_RESULT.json';atomic(saved,raw_bytes(r),immutable=True);buf=io.StringIO()
with patch.object(ex,'OUTPUT',saved),patch.object(ex.os,'geteuid',lambda:0,create=True),patch.object(ex.time,'sleep',lambda unused:None),patch('sys.stdout',buf):ex.emit_saved()
assert c.decode(buf.getvalue())[2]==r
try:
    with patch.object(ex.os,'geteuid',lambda:1000,create=True):ex.emit_saved()
except RuntimeError:pass
else:raise AssertionError('Exporter accepted non-root')
cp=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m442_performance_control01.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
assert 'M442_COMPONENT_CONTROL_SELFTEST_PASS' in cp.stdout
# Actual recursive package imports resolved only to exact reused visual manifests/runtime.
packages=[];pplan=json.loads((c.PKG/'PLAN.json').read_bytes())
for row in pplan['visual_reused_packages']:
    matches=[p.parent for p in (BASE/'candidates').glob('*/PACKAGE_MANIFEST.json') if sha(p)==row['manifest_sha256']];assert len(matches)==1;verify_package(matches[0]);packages.append(matches[0])
reuse=BASE/'candidates/M368-staged-video-03';verify_package(reuse);packages.append(reuse)
closure=json.loads((c.PKG/'SOURCE_CLOSURE.json').read_bytes());release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
for row in closure['files']:assert sha(release/row['path'])==row['sha256']
names={p.stem for p in c.PKG.glob('*.py')}|set(closure['modules'])|set(sys.stdlib_module_names)|{'numpy','torch','pynq','tokenizers'}
for root in packages:names|={p.stem for p in root.glob('*.py')}
for p in c.PKG.glob('*.py'):
    for n in ast.walk(ast.parse(p.read_bytes(),feature_version=(3,10))):
        refs=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
        assert all(not ref or ref in names for ref in refs),(p.name,refs)
gate=(c.PKG/'m441_performance_gate.py').read_text(encoding='utf-8');assert gate.index('make_candidate_runtime_class(board_cls)')<gate.index('engine.load()')
assert 'KernelSwitch' not in gate and 'prepare_programming(' not in gate
trials=(c.PKG/'m441_performance_trials.py').read_text(encoding='utf-8');assert trials.index('switch.select(variant,n+1)')<trials.index('for event,payload in engine.stream(request)')
out=BASE/'runs/M442-complete-request-parser-support-01/RESULT.json';v=dict(status='PASS_M442_PARSER_COMPLETE_REQUEST_SUPPORT01',manifest_sha256=sha(c.PKG/'PACKAGE_MANIFEST.json'),fixture_explicitly_not_board=True,reference_raw_sha256=sha(source),support_source_sha256=sha(__import__('pathlib').Path(__file__)),negative_decoder_checks=len(bads),actual_selector_owner_worker_build_rejections=11,actual_exporter_full_decoder_pass=True,controller_failure_collection_verified=True,recursive_import_missing=0,source_identity_before_overlay=True,PL_switches=0,board=False,performance=False)
atomic(out,encoded(v),immutable=True);sync('latest_m442_complete_request_parser_support',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False),'## M442完整请求支持检查01（2026-10-10）\n\nSHA '+sha(out)+'；实际selector11拒绝/逐12绑定、exporter→decoder/'+str(len(bads))+'负例、控制失败仍Collect/原安装递归missing0通过；fixture明确非板端。原CMA严格不重置，0请求间切核。')
print(v['status'],sha(out))
