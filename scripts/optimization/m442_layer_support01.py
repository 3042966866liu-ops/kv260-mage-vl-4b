"""Check actual package closure and isolated saved-byte decoder fixtures."""
import ast
import base64
import copy
import hashlib
import json
import subprocess
import sys
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
import m442_layer_workflow01 as w

pkg=w.PKG
closure=json.loads((pkg/'SOURCE_CLOSURE.json').read_bytes())
release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
for row in closure['files']:assert sha(release/row['path'])==row['sha256']
trees={p.stem:ast.parse(p.read_bytes(),feature_version=(3,10)) for p in pkg.glob('*.py')}
allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'pynq','numpy','tokenizers'}
missing=[]
for name,tree in trees.items():
    for n in ast.walk(tree):
        imports=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
        missing.extend((name,item) for item in imports if item and item not in trees and item not in allowed)
assert not missing,missing
def emit(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M442L_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM442L_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M442L_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(part).decode()+'\n' for i,part in enumerate(parts))+f'M442L_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
r=json.loads((BASE/'runs/M441-single-layer-board-09/BOARD_RESULT.json').read_bytes())
r.update(status='PASS_M442L_SINGLE_LAYER_DIAGNOSTIC',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),parser_candidate_sha256=sha(pkg/'m442_output_parser06.py'),parser_component_sha256=sha(pkg/'PARSER_COMPONENT.json'),parser_workers=1,kernel_changed=False)
def decode(log):
    digest,raw,value=w._namespace['decode'](log)
    if value['status']=='PASS_M442L_SINGLE_LAYER_DIAGNOSTIC':
        assert value['parser_candidate_sha256']==sha(pkg/'m442_output_parser06.py') and value['parser_component_sha256']==sha(pkg/'PARSER_COMPONENT.json')
        assert value['parser_workers']==1 and not value['kernel_changed'] and not value['additional_cma_requests_allowed'] and value['source_compatibility_checked_before_overlay']
    return value
assert decode(emit(r))==r
assert decode(emit(dict(r,status='FAIL',gate_return_code=1,errors=['Explicit fixture, not board'])))['gate_return_code']==1
bads=[emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('export_rc=0','export_rc=1')]
for key,value in [('manifest_sha256','0'*64),('parser_candidate_sha256','0'*64),('parser_component_sha256','0'*64),('parser_workers',2),('kernel_changed',True),('numerical_pass',False),('safe_buffers_released',False),('unsafe_buffers_retained',True),('released_buffers',[]),('fpga_transactions',0),('additional_cma_requests_allowed',True)]:bads.append(emit(dict(r,**{key:value})))
for log in bads:
    try:decode(log)
    except (ValueError,AssertionError,KeyError):pass
    else:raise RuntimeError('Invalid fixture accepted')
control=HERE/'m442_layer_control01.ps1'
check=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(control),'-Mode','SelfTest'],capture_output=True,check=True)
record=dict(status='PASS_M442_LIVE_LAYER_SUPPORT01',recursive_import_missing=missing,original_sources_sha_verified=True,fixture_explicitly_not_board=True,negative_decoder_checks=len(bads),controller_failure_collection_verified=True,manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (control,HERE/'m442_layer_workflow01.py',__import__('pathlib').Path(__file__))],board=False)
out=BASE/'runs/M442-live-parser-layer-support-01/RESULT.json'
atomic(out,encoded(record),immutable=True)
sync('latest_m442_live_parser_layer_support',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False),f'## M442单层支持实际检查（2026-10-10）\n\nSHA {sha(out)}；实际AST递归import missing=0，原安装源逐SHA，显式fixture PASS/FAIL/{len(bads)}负例与控制故意失败仍Collect通过；fixture不当新板端证据。完整接收及本支持通过后一次新解析器单层。')
print(record['status'],sha(out))
