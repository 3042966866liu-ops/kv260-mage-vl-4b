"""Independent live M238 parser candidate gate; unchanged M441 hardware."""
import ast
import json
import sys
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m442_component_workflow01 import manifest

old=BASE/'candidates/M441-single-layer-09'
pkg=BASE/'candidates/M442-live-parser-layer-01'
boot=BASE/'candidates/M442-live-parser-transfer-01'
remote='/home/ubuntu/m442_live_parser_layer_01'
component=BASE/'runs/M442-A53-parser-component-board-01/BOARD_RESULT.json'
proof=json.loads(component.read_bytes());assert proof['status']=='PASS_M442_A53_COMPONENT01' and proof['numerical_pass']
assert all(sha(component) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
assert not pkg.exists() and not boot.exists()
pkg.mkdir(parents=True)
spec=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
for row in spec['files']:
    p=old/row['path'];assert sha(p)==row['sha256']
    if row['path'] in ('SHA256SUMS','m441_layer_assemble.py'):continue
    raw=p.read_bytes()
    if row['path']=='m441_layer_gate.py':
        s=raw.decode().replace('/home/ubuntu/m441_single_layer_evidence_09','/home/ubuntu/m442_live_parser_evidence_01').replace('M441L','M442L')
        anchor='        board_cls = m243_video_server.M238PrefillRuntime'
        assert s.count(anchor)==1
        s=s.replace(anchor,"        from m442_runtime_adapter02 import make_candidate_runtime_class\n        board_cls = make_candidate_runtime_class(m243_video_server.M238PrefillRuntime)\n        result['parser_candidate_sha256']=sha256(HERE/'m442_output_parser06.py')\n        result['parser_component_sha256']=sha256(HERE/'PARSER_COMPONENT.json')\n        result['parser_workers']=1\n        result['kernel_changed']=False\n        if result['parser_component_sha256']!='"+sha(component)+"':raise RuntimeError('Actual A53 component differs before Overlay')")
        raw=s.encode()
    elif row['path'] in ('m441_layer_export.py','run_m441_layer.sh'):
        raw=raw.replace(b'/home/ubuntu/m441_single_layer_evidence_09',b'/home/ubuntu/m442_live_parser_evidence_01').replace(b'M441L',b'M442L')
    if row['path'].endswith('.py'):ast.parse(raw,feature_version=(3,10))
    atomic(pkg/row['path'],raw,immutable=True)
for name in ('m442_runtime_adapter02.py','m442_output_parser06.py'):
    atomic(pkg/name,(HERE/name).read_bytes(),immutable=True)
atomic(pkg/'PARSER_COMPONENT.json',component.read_bytes(),immutable=True)
spec=manifest(pkg,'m442-live-parser-same-M441-layer-v1')
boot.mkdir(parents=True)
transfer=(HERE/'m441_transfer.py').read_text(encoding='utf-8').replace("DESTINATION=Path('/home/ubuntu/m441_candidate_01')","DESTINATION=Path('"+remote+"')").replace("EVIDENCE=Path('/home/ubuntu/m441_transfer_evidence_01')","EVIDENCE=Path('/home/ubuntu/m442_live_parser_transfer_evidence_01')")
atomic(boot/'m442_transfer01.py',transfer.encode(),immutable=True)
rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(pkg/'PACKAGE_MANIFEST.json').stat().st_size,sha256=sha(pkg/'PACKAGE_MANIFEST.json'))]+spec['files']
atomic(boot/'TRANSPORT_MANIFEST.json',encoded(dict(schema='m441-specific-peer-transfer-v1',package_manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
atomic(boot/'run_m442_transfer.sh',(BASE/'candidates/M442-A53-transfer-bootstrap-01/run_m442_transfer.sh').read_bytes(),immutable=True)
manifest(boot,'m442-live-parser-specific-peer-bootstrap')
# Preserve the proven transport decoder/controller, change only this workflow's paths.
workflow=(HERE/'m442_component_workflow01.py').read_text(encoding='utf-8')
prefix=workflow[:workflow.index('\ndef collect(log):')]
transport=workflow[workflow.index('\ndef transfer_collect(log):'):workflow.index('\n\nif __name__')]
prefix=prefix[:prefix.index('\ndef prepare():')]
prefix=prefix.replace('M442-A53-parser-component-01','M442-live-parser-layer-01').replace('M442-A53-transfer-bootstrap-01','M442-live-parser-transfer-01').replace('M442-A53-parser-component-preparation-01','M442-live-parser-layer-preparation-01')
transport=transport.replace('M442-A53-artifact-transfer-01','M442-live-parser-artifact-transfer-01').replace('latest_m442_a53_artifact_transfer','latest_m442_live_parser_transfer')
collector='''
_source=(HERE/'m365_collect.py').read_text(encoding='utf-8')
_source=_source[:_source.index('\\ndef collect(')].replace('M365-staged-layer-03','M442-live-parser-layer-01').replace('M365','M442L').replace('0x4D333537','0x4D343431').replace('0x4d333537','0x4d343431')
_namespace={'__name__':'_m442_layer_original_decoder'}
exec(compile(_source,'<same strict original M365 decoder>','exec'),_namespace)
def collect(log):
    digest,raw,r=_namespace['decode'](Path(log).read_text(encoding='utf-8-sig'))
    if r['status']=='PASS_M442L_SINGLE_LAYER_DIAGNOSTIC':
        if r['parser_candidate_sha256']!=sha(PKG/'m442_output_parser06.py') or r['parser_component_sha256']!=sha(PKG/'PARSER_COMPONENT.json') or r['parser_workers']!=1 or r['kernel_changed']:
            raise RuntimeError('New parser identity/worker/kernel differs')
        if r['additional_cma_requests_allowed'] is not False or not r['source_compatibility_checked_before_overlay']:
            raise RuntimeError('Source/allocator seal differs')
    out=BASE/'runs/M442-live-parser-layer-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    atomic(out.with_name('COLLECTION.json'),encoded(dict(raw_sha256=digest,log_sha256=sha(Path(log)),hardware_rerun=False)),immutable=True)
    sync('latest_m442_live_parser_layer_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],performance_pass=False),f'## M442真实解析路径单层裁决（2026-10-10）\\n\\nSHA {digest}；{r["status"]}，原rc{r["gate_return_code"]}。同M441硬件/原五family/159token/原完整参考和七DMA封锁；只显式candidate解析器改变，原字节/安全恢复核对。非完整请求性能，失败仅本级。')
    print(r['status'],digest,r.get('errors'),flush=True)
    return r['gate_return_code']
if __name__=='__main__':
    if sys.argv[1:]==['send']:raise SystemExit(send())
    if len(sys.argv)==3 and sys.argv[1]=='collect':raise SystemExit(collect(sys.argv[2]))
    if len(sys.argv)==3 and sys.argv[1]=='transfer-collect':raise SystemExit(transfer_collect(sys.argv[2]))
    raise RuntimeError('Saved collection or explicit send only')
'''
workflow=prefix+transport+collector
ast.parse(workflow,feature_version=(3,10))
atomic(HERE/'m442_layer_workflow01.py',workflow.encode(),immutable=True)
control=(HERE/'m442_component_control01.ps1').read_text(encoding='utf-8')
for a,b in [('M442-A53-parser-component-preparation-01','M442-live-parser-layer-preparation-01'),('M442-A53-parser-component-01','M442-live-parser-layer-01'),('M442-A53-transfer-bootstrap-01','M442-live-parser-transfer-01'),('M442-A53-artifact-transfer-01','M442-live-parser-artifact-transfer-01'),('M442-A53-parser-component-board-01','M442-live-parser-layer-board-01'),('m442_component_workflow01','m442_layer_workflow01'),('/home/ubuntu/m442_a53_component_candidate_01',remote),('/home/ubuntu/m442_a53_transfer_bootstrap_01','/home/ubuntu/m442_live_parser_transfer_bootstrap_01'),('tmp/m442_board01','tmp/m442_layer01'),("'Component'","'Run'")]:control=control.replace(a,b)
control=control.replace('run_m442_component.sh','run_m441_layer.sh').replace("{'Run'}else{'Collect'}","{'Run'}else{'Collect'}")
control=control.replace('sudo -n bash $taskRemote/run_m441_layer.sh $taskSHA $taskAction','sudo -n env M442L_ENABLE_STAGED_LAYER=1 bash $taskRemote/run_m441_layer.sh $taskSHA $taskAction B1').replace('-TimeoutSeconds 300','-TimeoutSeconds 900')
atomic(HERE/'m442_layer_control01.ps1',control.encode(),immutable=True)
record=dict(status='PREPARED_M442_LIVE_PARSER_LAYER01',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),bootstrap_manifest_sha256=sha(boot/'PACKAGE_MANIFEST.json'),parser_component_sha256=sha(component),kernel_build='0x4D343431',hardware_unchanged=True,recursive_import_missing=[],seven_DMA_resident=True,parser_workers=1,board=False,performance=False,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (HERE/'m442_layer_workflow01.py',HERE/'m442_layer_control01.ps1')])
dest=BASE/'runs/M442-live-parser-layer-preparation-01/RESULT.json'
atomic(dest,encoded(record),immutable=True)
sync('latest_m442_live_parser_layer_preparation',dict(status=record['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),f'## M442真实解析单层隔离包（2026-10-10）\n\nSHA {sha(dest)}，manifest {record["manifest_sha256"]}；A53完整数值已经PASS但组件计时未提速。下一步同M441整壳、显式新M238子类、原layer0/159token/完整五family与KV真实参考；不修改稳定源/调度/回滚，不混入MAC改变。原M441 Build/descriptor/chain/RTL/整壳均同SHA复用；新解析先本单层，再文本/视频，最后固定完整请求对照。')
print(record['status'],sha(dest))
