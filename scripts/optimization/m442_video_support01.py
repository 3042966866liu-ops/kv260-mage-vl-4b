"""Actual producer/exporter/decoder checks with explicit saved-byte host fixtures."""
import ast,base64,copy,hashlib,importlib.util,io,json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
from m441_prepare_layer09 import verify_package
import m442_video_decoder01 as c

verify_package(c.PKG)
source=BASE/'runs/M441-fixed-video-board-09/BOARD_RESULT.json'
r=json.loads(source.read_bytes())
r.update(status='PASS_M442V_INTEGRATED_VIDEO_NUMERICAL',manifest_sha256=sha(c.PKG/'PACKAGE_MANIFEST.json'),prior_fixed_text_raw_sha256=sha(c.PKG/'STAGE_PREREQUISITE.json'),parser_candidate_sha256=sha(c.PKG/'m442_output_parser06.py'),parser_component_sha256=sha(c.PKG/'PARSER_COMPONENT.json'),parser_workers=1,kernel_changed=False)
def emit(v):
    raw=encoded(v);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M442V_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM442V_SAVED_GATE_RC='+str(v['gate_return_code'])+'\n'+''.join(f'M442V_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M442V_DONE gate_rc={v["gate_return_code"]} export_rc=0\n'
assert c.decode(emit(r))[2]==r
assert c.decode(emit(dict(r,status='FAIL',gate_return_code=1,errors=['Explicit fixture NOT board'])))[2]['gate_return_code']==1
bads=[emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('export_rc=0','export_rc=1'),emit(r).replace('SAVED_GATE_RC=0','SAVED_GATE_RC=1')]
for k,v in [('manifest_sha256','0'*64),('build_id','0x4D333537'),('model_forward_calls',2),('vision_forward_calls',2),('fpga_transactions',1067),('logical_calls',1556),('transactions',r['transactions'][:-1]),('integrated_boundaries',r['integrated_boundaries'][:-1]),('visual_transactions',r['visual_transactions'][:-1]),('visual_staging',r['visual_staging'][:-1]),('saved_reference_variant','original'),('borrowed_extra_DMA',1),('peak_live_visual_layer_scopes',2),('visual_static_cache_invalidated',False),('safe_buffers_released',False),('unsafe_buffers_retained',True),('source_compatibility_checked_before_overlay',False),('prior_fixed_text_raw_sha256','0'*64),('prior_board_sha256','0'*64),('temperature_measurement_enabled',True),('performance_pass',True),('gate_return_code',False),('parser_candidate_sha256','0'*64),('parser_component_sha256','0'*64),('parser_workers',2),('kernel_changed',True)]:bads.append(emit(dict(r,**{k:v})))
for field in ('keys','values','families','logits','decision','counts'):
    b=copy.deepcopy(r)
    if isinstance(b['samples'][0][field],list):b['samples'][0][field].pop()
    elif field=='logits':b['samples'][0][field]['sha256']='0'*64
    elif field=='decision':b['samples'][0][field]['knife_score']=0.1
    else:b['samples'][0][field]['stage_bytes']-=1
    bads.append(emit(b))
b=copy.deepcopy(r);b['visual_transactions'][0]['completed_snapshot']['ap_return']=0;bads.append(emit(b))
for log in bads:
    try:c.decode(log)
    except (ValueError,KeyError,AssertionError,RuntimeError):pass
    else:raise AssertionError('Broken full result accepted')
spec=importlib.util.spec_from_file_location('actual_m442_video_export',c.PKG/'m441_video_export.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
folder=ROOT/'tmp/m442_video01/export_fixture';folder.mkdir(parents=True,exist_ok=False);saved=folder/'BOARD_RESULT.json';atomic(saved,encoded(r),immutable=True)
buf=io.StringIO()
with patch.object(ex,'OUTPUT',saved),patch.object(ex.os,'geteuid',lambda:0,create=True),patch.object(ex.time,'sleep',lambda unused:None),patch('sys.stdout',buf):ex.emit_saved()
assert c.decode(buf.getvalue())[2]==r
try:
    with patch.object(ex.os,'geteuid',lambda:1000,create=True):ex.emit_saved()
except RuntimeError:pass
else:raise AssertionError('Exporter accepted non-root')
cp=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m442_video_control01.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
assert 'M442_COMPONENT_CONTROL_SELFTEST_PASS' in cp.stdout
tree=ast.parse((c.PKG/'m432_trials.py').read_bytes())
loop=next(n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [x.id for x in n.target.elts]==['i','visual'])
assert eval(compile(ast.Expression(loop.iter),'<actual-dispatch>','eval'),{'features':['A','B']})==((1,'B'),)
pt=ast.parse((c.PKG/'m432_request_visual.py').read_bytes());cls=next(n for n in pt.body if isinstance(n,ast.ClassDef));fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__call__');guard=next(n for n in fn.body if isinstance(n,ast.If));test=compile(ast.Expression(guard.test),'<actual-provider>','eval')
for index,count,rejected in ((1,0,False),(0,0,True),(1,1,True),(2,0,True)):assert eval(test,{'index':index,'self':SimpleNamespace(result={'integrated_visual':[None]*count},disposed=False)}) is rejected
plan=json.loads((c.PKG/'PLAN.json').read_bytes());packages=[]
for row in plan['visual_reused_packages']:
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
out=BASE/'runs/M442-live-parser-video-support-01/RESULT.json'
v=dict(status='PASS_M442_LIVE_VIDEO_SUPPORT01',manifest_sha256=sha(c.PKG/'PACKAGE_MANIFEST.json'),fixture_explicitly_not_board=True,reference_raw_sha256=sha(source),negative_decoder_checks=len(bads),actual_exporter_full_decoder_pass=True,actual_one_B_dispatch_and_preimport_provider_guard=True,controller_failure_collection_verified=True,recursive_import_missing=0,original_sources_SHA_verified=True,board=False,performance=False,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (Path(__file__),HERE/'m442_video_decoder01.py',HERE/'m442_video_workflow01.py',HERE/'m442_video_control01.ps1')])
atomic(out,encoded(v),immutable=True);sync('latest_m442_live_parser_video_support',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False),'## M442视频支持实际检查01（2026-10-10）\n\nSHA '+sha(out)+'；实际exporter→严格decoder、'+str(len(bads))+'负例、控制失败仍Collect、原单B/资源前provider拒绝/实际递归闭包missing0通过。明确host fixture，不替代新实板原字节。')
print(v['status'],sha(out))
