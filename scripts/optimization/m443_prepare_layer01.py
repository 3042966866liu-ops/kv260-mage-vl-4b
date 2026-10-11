"""Derive one isolated M443 layer gate from exact proven M441 bytes; no board execution."""
import ast
import json
import sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m443_transfer import verify_directory
from m443_configuration01 import validate_record

OLD = w.BASE/'candidates/M441-single-layer-09'
CORE = w.BASE/'candidates/M443-pair-pipeline-01'
PKG = w.BASE/'candidates/M443-single-layer-01'
RUN = w.BASE/'runs/M443-single-layer-preparation-01'
REMOTE = '/home/ubuntu/m443_single_layer_candidate_01'
EVIDENCE = '/home/ubuntu/m443_single_layer_evidence_01'


def once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after, 1)


def main():
    assert not PKG.exists() and not RUN.exists(), 'Fresh immutable preparation required'
    old_sha = w.sha(OLD/'PACKAGE_MANIFEST.json')
    core_sha = w.sha(CORE/'PACKAGE_MANIFEST.json')
    verify_directory(OLD, old_sha)
    verify_directory(CORE, core_sha)
    proofs = {}
    for level in ('BuildID', 'Descriptor', 'Chain'):
        p = w.BASE/('runs/M443-'+level.lower()+'-board-01/BOARD_RESULT.json')
        r = json.loads(p.read_bytes()); s = w.sha(p)
        assert r['status'] == 'PASS_M443_'+level.upper() and r['gate_return_code'] == 0 and not r['errors']
        assert r['stable_restored'] and r['safe_buffers_released'] and not r['unsafe_dma_buffers_retained']
        assert all(s in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
        validate_record(r['configuration_record'], w.sha(CORE/'CONFIGURATION_APPLICATION.json'), core_sha)
        proofs[level] = (p, s)
    chain_sha = proofs['Chain'][1]
    build_sha = proofs['BuildID'][1]
    text = (OLD/'m441_layer_gate.py').read_text(encoding='utf-8')
    text = text.replace('m441_layer_', 'm443_layer_').replace('M441L', 'M443L').replace('_m441l_', '_m443l_')
    text = text.replace('/home/ubuntu/m441_single_layer_evidence_09', EVIDENCE)
    text = once(text, "Path('/home/ubuntu/m441_candidate_01')", "Path('/home/ubuntu/m443_candidate_01')")
    text = once(text, "CAND_SHA = '56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0'", "CAND_SHA = '"+core_sha+"'")
    text = once(text, "PRIOR_SHA = '0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'", "PRIOR_SHA = '"+chain_sha+"'\nBUILD_PROOF_SHA = '"+build_sha+"'")
    text = text.replace("'0x4D343431' if is_candidate", "'0x4D343433' if is_candidate")
    text = text.replace('M441_COMPARE_PREREQUISITE.json', 'M443_CHAIN_PREREQUISITE.json')
    text = once(text, "prerequisite['status'] != 'PASS_M441_COMPARE' or not prerequisite['chain_performance_pass']", "prerequisite['status'] != 'PASS_M443_CHAIN' or prerequisite['gate_return_code'] != 0")
    text = text.replace('Exact M441 balanced single-chain prerequisite differs', 'Exact M443 complete real chain prerequisite differs')
    text = once(text, "        result['prior_board_sha256'] = PRIOR_SHA", """        result['prior_board_sha256'] = PRIOR_SHA
        from m443_configuration01 import validate_record
        build_path = HERE/'M443_BUILD_CONFIGURATION_PROOF.json'
        build_proof = json.loads(build_path.read_bytes())
        if sha256(build_path) != BUILD_PROOF_SHA or build_proof['status'] != 'PASS_M443_BUILDID' or build_proof['gate_return_code'] != 0:
            raise RuntimeError('Actual new-bit BuildID configuration origin differs')
        if prerequisite['configuration_application_build_raw_sha256'] != BUILD_PROOF_SHA:
            raise RuntimeError('Complete chain not bound to actual configuration origin')
        application_sha = sha256(HERE/'CONFIGURATION_APPLICATION.json')
        validate_record(build_proof['configuration_record'],application_sha,CAND_SHA)
        validate_record(prerequisite['configuration_record'],application_sha,CAND_SHA)
        result['configuration_application_build_raw_sha256'] = BUILD_PROOF_SHA""")
    text = once(text, '    initialized = unsafe = False', '    initialized = unsafe = False\n    configuration = None')
    text = once(text, "        patch(pynq,'Overlay',observe_call(pynq.Overlay,'pynq.Overlay',mark,result['io_events']))", """        from m443_layer_configuration01 import LayerConfiguration
        configuration = LayerConfiguration(result,TARGET,TARGET_SHA,HERE/'CONFIGURATION_APPLICATION.json',EVIDENCE)
        original_overlay = pynq.Overlay
        def configuration_overlay(bit,*a,**kw):
            return configuration.load(bit,original_overlay,*a,**kw)
        patch(pynq,'Overlay',observe_call(configuration_overlay,'pynq.Overlay',mark,result['io_events']))""")
    text = once(text, '            index=len(allocations)', '            configuration.require_allocation_eligibility()\n            index=len(allocations)')
    text = once(text, '        # Keep guards installed until all resource cleanup is finished.', '        # Unknown programming ownership preserves Overlay, runtime, seven owners and lock.\n        unsafe = unsafe or (configuration is not None and configuration.retain_required)\n        # Keep guards installed until all resource cleanup is finished.')
    files = {}
    exclude = {'PACKAGE_MANIFEST.json', 'SHA256SUMS', 'M441_COMPARE_PREREQUISITE.json', 'HARDWARE_CLOSURE.json', 'm441_layer_gate.py', 'm441_layer_export.py', 'm441_layer_assemble.py', 'run_m441_layer.sh'}
    for p in OLD.iterdir():
        assert p.is_file() and not p.is_symlink()
        if p.name not in exclude: files[p.name] = p.read_bytes()
    files['m443_layer_gate.py'] = text.encode('utf-8')
    files['m443_layer_export.py'] = (OLD/'m441_layer_export.py').read_text(encoding='utf-8').replace('M441L', 'M443L').replace('/home/ubuntu/m441_single_layer_evidence_09', EVIDENCE).encode()
    files['run_m443_layer.sh'] = (OLD/'run_m441_layer.sh').read_text(encoding='utf-8').replace('M441L', 'M443L').replace('m441_layer_', 'm443_layer_').replace('/home/ubuntu/m441_single_layer_evidence_09', EVIDENCE).encode()
    files['M443_CHAIN_PREREQUISITE.json'] = proofs['Chain'][0].read_bytes()
    files['M443_BUILD_CONFIGURATION_PROOF.json'] = proofs['BuildID'][0].read_bytes()
    files['HARDWARE_CLOSURE.json'] = (CORE/'HARDWARE_CLOSURE.json').read_bytes()
    for name in ('CONFIGURATION_APPLICATION.json', 'm443_configuration01.py', 'm443_cma_contract01.py', 'm443_cma_trace01.py'):
        files[name] = (CORE/name).read_bytes()
    files['m443_layer_configuration01.py'] = (w.HERE/'m443_layer_configuration01.py').read_bytes()
    assembler = '''"""Assemble frozen bytes from previously verified board packages/results only."""
import hashlib,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(expected):
 if os.geteuid()!=0 or sha(ROOT/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Root/exact manifest required')
 source={}
 for directory,digest in SOURCES:
  d=Path(directory);m=d/'PACKAGE_MANIFEST.json'
  if sha(m)!=digest:raise RuntimeError('Pinned source manifest changed')
  for row in json.loads(m.read_bytes())['files']:
   p=d/row['path']
   if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Pinned source member changed')
   source[row['sha256']]=p
 for path,digest in PROOFS:
  p=Path(path)
  if sha(p)!=digest:raise RuntimeError('Actual board proof changed')
  source[digest]=p
 data=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_bytes())
 for row in data['files']:
  if '/' in row['path'] or '\\\\' in row['path']:raise RuntimeError('Flat whitelist required')
  p=ROOT/row['path']
  if not p.exists():
   q=source.get(row['sha256'])
   if q is None or sha(q)!=row['sha256']:raise RuntimeError('Missing frozen source member')
   shutil.copyfile(q,p)
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Assembled member differs')
 if {p.name for p in ROOT.iterdir()}!={r['path'] for r in data['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist changed')
 print('M443L_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
SOURCES=SOURCE_CONSTANT
PROOFS=PROOF_CONSTANT
if __name__=='__main__':main(sys.argv[1])
'''.replace('SOURCE_CONSTANT', repr([('/home/ubuntu/m441_single_layer_candidate_09', old_sha), ('/home/ubuntu/m443_candidate_01', core_sha)])).replace('PROOF_CONSTANT', repr([('/home/ubuntu/m443_board_evidence_01/BuildID/BOARD_RESULT.json', build_sha), ('/home/ubuntu/m443_board_evidence_01/Chain/BOARD_RESULT.json', chain_sha)]))
    files['m443_layer_assemble.py'] = assembler.encode()
    closure = json.loads(files['SOURCE_CLOSURE.json'])
    release = w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']: assert w.sha(release/row['path']) == row['sha256']
    for name in ('frozen_one_layer.py', 'm365_stage_policy.py', 'owned_buffer_release.py', 'LAYER_EXPECTED.json'):
        assert files[name] == (OLD/name).read_bytes()
    trees = {Path(n).stem: ast.parse(raw, feature_version=(3,10)) for n,raw in files.items() if n.endswith('.py')}
    allowed = set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers','fcntl'}
    missing = []
    for module,tree in trees.items():
        for n in ast.walk(tree):
            names = [a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((module,name) for name in names if name and name not in trees and name not in allowed)
    assert not missing, missing
    assert text.index('one_layer=bind(') < text.index("patch(pynq,'Overlay'") < text.index('engine.load()')
    assert text.index('unsafe = unsafe or (configuration') < text.index('        if not unsafe:')
    PKG.mkdir(parents=True)
    for name,raw in files.items(): atomic(PKG/name, raw, immutable=True)
    rows = [dict(path=p.name, bytes=p.stat().st_size, sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS', ''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'), immutable=True)
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    manifest = dict(schema='m443-independent-single-layer-v01',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))
    atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(manifest),immutable=True)
    digest = w.sha(PKG/'PACKAGE_MANIFEST.json'); verify_directory(PKG,digest)
    result = dict(status='PREPARED_M443_SINGLE_LAYER_AFTER_ACTUAL_CHAIN01',build_id='0x4D343433',
                  package_path=PKG.relative_to(w.ROOT).as_posix(),manifest_sha256=digest,remote=REMOTE,evidence=EVIDENCE,
                  prior_raw_sha256=chain_sha,configuration_build_raw_sha256=build_sha,candidate_manifest_sha256=core_sha,
                  original_m441_layer_manifest_sha256=old_sha,unchanged_layer_math_and_seven_owner=True,
                  seven_buffer_geometry=[6963200]*4+[389152,2621440,2621440],ps_growth_limit_bytes=256<<20,ps_available_margin_bytes=64<<20,
                  additional_cma_requests_allowed=False,original_counter_baseline_reset=False,configuration_credits_granted=0,
                  actual_configuration_before_runtime_buffers=True,unknown_configuration_retains_process=True,
                  recursive_import_missing=missing,python310_syntax=True,source_compatibility_before_overlay=True,
                  files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(PKG.iterdir())],
                  board_executed=False,performance_pass=False,promoted=False)
    atomic(RUN/'RESULT.json',w.encoded(result),immutable=True); s=w.sha(RUN/'RESULT.json'); w.atomic=atomic
    w.sync('latest_m443_single_layer_preparation01',dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,manifest_sha256=digest),
           '## M443独立单层准备01（2026-10-11）\n\nSHA '+s+'；manifest '+digest+'；实际完整chain原SHA '+chain_sha+'及新bit BuildID配置原SHA '+build_sha+'绑定。沿用M441原单层数学/七缓冲/PS256MiB增长和64MiB余量/源提前检查；新Overlay实际同PID配置合同必须在原runtime缓冲之前完成，未知保留process/Overlay/buffer/lock。递归依赖missing=0，未执行单层/模型/视频/性能；下一步仅组件正负fixture和控制采集检查后逐SHA上传及一次单层。')
    print(result['status'],s,digest,len(rows),manifest['total_bytes'])


if __name__ == '__main__': main()
