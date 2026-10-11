"""Actual exporter/host/assembly/control fixtures, with explicit fake root and ownership."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
import m432_workflow02 as w


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def main():
    pkg = w.PKG; plan = json.loads((pkg / 'PLAN.json').read_bytes()); digest = sha(pkg / 'PACKAGE_MANIFEST.json')
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e = board['latest_m432_provider_component']; assert sha(ROOT / e['result']) == e['sha256']
    # Supply only the actual candidate helper, without importing a development variant.
    helper = module('m428_saved_features', pkg / 'm428_saved_features.py')
    rejected = []
    def reject(label, fn):
        try: fn()
        except (RuntimeError, ValueError, KeyError, AssertionError, OSError): rejected.append(label)
        else: raise AssertionError('Invalid accepted: ' + label)
    def fake_owned_read(path, size, digest_value):
        # Windows fixture cannot attest Linux uid. Full bytes/SHA are real; uid is explicitly fake.
        raw = Path(path).read_bytes()
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest_value: raise ValueError('Actual saved SHA differs')
        return raw
    prior_helper = sys.modules.get('m428_saved_features')
    sys.modules['m428_saved_features'] = helper
    try:
        provider = module('actual_m432_provider', pkg / 'm432_request_visual.py')
        local = copy.deepcopy(plan)
        for name, row in local['integrated_sources'].items():
            matches = [x for x in board.values() if isinstance(x, dict) and x.get('sha256') == row['sha256'] and 'result' in x]
            assert len(matches) == 1; row['path'] = str(ROOT / matches[0]['result'])
        for row in local['visual_reused_packages']:
            matches = [p.parent for p in (BASE / 'candidates').glob('*/PACKAGE_MANIFEST.json') if sha(p) == row['manifest_sha256']]
            assert len(matches) == 1; row['directory'] = str(matches[0])
        with patch.object(helper, 'read_owned', fake_owned_read):
            actual = provider.verify_sources(local)
            with tempfile.TemporaryDirectory(dir=ROOT / 'tmp', prefix='m432-source-') as temp:
                badfile = Path(temp) / 'bad.json'
                changes = [('visual','selected_layers',[12,13]),('visual','matched_wire_batches',285),('visual','stable_restored',False),
                           ('visual','numerical_hardware_proven',False),('language','vision_forward_calls',1),('language','decision_consistency_pass',False),
                           ('language','safe_buffers_released',False),('language','samples',[]),('software','feature_pass_ranges',['early_2_12']),
                           ('CPU','DMA_allocations',1),('CPU','source_identities_verified',48),('CPU','manifest_sha256','0'*64)]
                for role, key, value in changes:
                    bad = copy.deepcopy(actual[role]); bad[key] = value; badfile.write_bytes(encoded(bad))
                    q = copy.deepcopy(local); q['integrated_sources'][role].update(path=str(badfile), bytes=badfile.stat().st_size, sha256=sha(badfile))
                    reject('source-' + role + '-' + key, lambda q=q: provider.verify_sources(q))
                for role in ('visual', 'language', 'software', 'CPU'):
                    bad = copy.deepcopy(actual[role]); bad['gate_return_code'] = True; badfile.write_bytes(encoded(bad))
                    q = copy.deepcopy(local); q['integrated_sources'][role].update(path=str(badfile), bytes=badfile.stat().st_size, sha256=sha(badfile))
                    reject('source-bool-rc-' + role, lambda q=q: provider.verify_sources(q))
                q = copy.deepcopy(local); q['integrated_sources']['CPU']['sha256'] = '0'*64
                reject('source-exact-SHA', lambda: provider.verify_sources(q))
    finally:
        if prior_helper is None: sys.modules.pop('m428_saved_features', None)
        else: sys.modules['m428_saved_features'] = prior_helper
    r = copy.deepcopy(actual['language'])
    r.update(status='PASS_M432_INTEGRATED_VIDEO_NUMERICAL', manifest_sha256=digest, gate_level='integrated-fixed159-visual-language-quality',
             vision_forward_calls=2, integrated_sources_checked_before_overlay=True, visual_provider_disposed=True,
             borrowed_buffer_identity_preserved=True, visual_static_cache_invalidated=True, visual_bindings_restored=True,
             borrowed_extra_DMA=0, peak_live_visual_layer_scopes=1, visual_matched_wire_batches=286,
             integrated_visual=[x['tensor'] for x in plan['features']],
             integrated_exact_comparisons=[{k:True for k in ('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts')} for _ in range(2)])
    accepted = next(x for x in actual['software']['ranges'] if x['name'] == 'late_13_23')
    r['integrated_boundaries'] = [dict(layer=i,tensor=x['candidate']) for i,x in enumerate(accepted['boundary_comparison'])]
    r['fpga_transactions'] += 286
    r['visual_transactions'] = [dict(layer=x['layer'], part=x['part'], start=x['start'], shift=x['shift'], input_bytes=x['input_bytes'], output_bytes=x['output_bytes'], completed=True, completed_snapshot=x['completed_snapshot']) for x in actual['visual']['PL_rows']]
    r['visual_staging'] = actual['visual']['staging']
    w.check(r)
    for label in ('extra-buffer','missing-visual','wrong-shift','unfinished-visual','bad-visual-Build','bad-stage','missing-boundary','bad-boundary',
                  'missing-KV','bad-B-logits','bad-decision','bad-physical','bad-total','no-release','no-cache-clear','no-binding-restore','before-resources','lost-comparison','bool-rc','temperature'):
        bad = copy.deepcopy(r)
        if label=='extra-buffer': bad['borrowed_extra_DMA']=1
        elif label=='missing-visual': bad['visual_transactions'].pop()
        elif label=='wrong-shift': bad['visual_transactions'][0]['shift']=-1
        elif label=='unfinished-visual': bad['visual_transactions'][0]['completed']=False
        elif label=='bad-visual-Build': bad['visual_transactions'][0]['completed_snapshot']['ap_return']=0
        elif label=='bad-stage': bad['visual_staging'][0]['bytes']-=1
        elif label=='missing-boundary': bad['integrated_boundaries'].pop()
        elif label=='bad-boundary': bad['integrated_boundaries'][23]['tensor']['sha256']='0'*64
        elif label=='missing-KV': bad['samples'][1]['keys'].pop()
        elif label=='bad-B-logits': bad['samples'][1]['logits']['sha256']='0'*64
        elif label=='bad-decision': bad['samples'][1]['decision']['knife_score']=0.1
        elif label=='bad-physical': bad['transactions'][0]['chain_index']=999
        elif label=='bad-total': bad['fpga_transactions']-=1
        elif label=='no-release': bad['visual_provider_disposed']=False
        elif label=='no-cache-clear': bad['visual_static_cache_invalidated']=False
        elif label=='no-binding-restore': bad['visual_bindings_restored']=False
        elif label=='before-resources': bad['integrated_sources_checked_before_overlay']=False
        elif label=='lost-comparison': bad['integrated_exact_comparisons'][1]['counts']=False
        elif label=='bool-rc': bad['gate_return_code']=False
        else: bad['temperature_measurement_enabled']=True
        reject('collector-'+label, lambda bad=bad: w.check(bad))
    exporter = module('actual_m432_export', pkg / 'm432_export.py')
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp', prefix='m432-export-') as temp:
        path=Path(temp)/'BOARD_RESULT.json'; exporter.OUTPUT=path
        def export(value):
            path.write_bytes(encoded(value)); out=io.StringIO()
            with patch.object(exporter.os,'geteuid',lambda:0,create=True), patch.object(exporter.time,'sleep',lambda *x:None), contextlib.redirect_stdout(out): exporter.emit_saved()
            return out.getvalue()
        receipt=export(r); assert w.decode(receipt)[2]==r
        failure=dict(r,status='FAIL',gate_return_code=1,errors=['Explicit synthetic pre-resource fixture failure'],features_verified_before_overlay=False,vision_forward_calls=0,model_forward_calls=0)
        assert w.decode(export(failure))[2]==failure
        for label, text in [('duplicate',receipt+receipt),('missing',receipt[:receipt.index('M432_RESULT_CHUNK=1/')]),
                            ('order',receipt.replace('M432_RESULT_CHUNK=1/','M432_RESULT_CHUNK=0/')),
                            ('SHA',receipt.replace(hashlib.sha256(encoded(r)).hexdigest(),'0'*64)),
                            ('rc',receipt.replace('M432_SAVED_GATE_RC=0','M432_SAVED_GATE_RC=1'))]:
            reject('export-'+label,lambda text=text:w.decode(text))
        # Execute the real collector against a sandbox output and sandbox sync; exact raw bytes must survive.
        collected=Path(temp)/'collected/BOARD_RESULT.json'; log=Path(temp)/'run.log'; log.write_text(receipt,encoding='utf-8'); notes=[]
        with patch.object(w,'OUT',collected),patch.object(w,'sync',lambda *args:notes.append(args)),contextlib.redirect_stdout(io.StringIO()): w.collect(log)
        assert collected.read_bytes()==encoded(r) and len(notes)==1 and notes[0][0]=='latest_m432_integrated_board'
    for p in pkg.glob('*.py'): ast.parse(p.read_text(encoding='utf-8-sig'),feature_version=(3,10))
    g=(pkg/'m432_gate.py').read_text(encoding='utf-8')
    assert g.index('verify_sources(plan)')<g.index('import pynq')<g.index('engine.load()')<g.index("patch(tokenizers,'Tokenizer',original_tokenizer)")
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    control=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m432_control02.ps1'),'-Mode','SelfTest'],capture_output=True)
    if control.returncode or b'M432_CONTROL_SELF_TEST_PASS' not in control.stdout: raise RuntimeError('Actual control rejected')
    bash=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(pkg/'run_m432.sh').relative_to(ROOT).as_posix()],capture_output=True)
    if bash.returncode: raise RuntimeError('Actual bash runner rejected')
    record=dict(status='PASS_M432_INTEGRATED_SUPPORT_ONLY',manifest_sha256=digest,provider_component_sha256=e['sha256'],
                actual_saved_sources_full_SHA=True, ownership_and_root_in_host_fixture_explicit_fake=True,
                actual_full_exporter_host_decode_and_atomic_collector=True, full_PASS_and_early_FAIL_exact_bytes=True,
                synthetic_integration_fixture_from_accepted_records=True, negative_checks=rejected,
                actual_control_intentional_failure_collect=True, runner_bash_n=True, Python310_syntax=True,
                assembly_fixture_pending=True, transfer_fixture_pending=True,
                source_sha256={n:sha(HERE/n) for n in ('m432_workflow02.py','m432_control02.ps1','m432_support.py')},
                board_run=False,numerical_pass=False,performance_pass=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M432-integrated-support-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m432_integrated_support',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=digest),
         f'## M432 实际来源/导出/回收/控制配套检查（2026-10-07）\n\nSHA {sha(out)}；实际资源前来源全SHA及{len(rejected)}来源/286事务/24边界/72KV/logits/重试/释放/缓存/测温/分块拒绝，实际完整export→host PASS/早期FAIL原字节及atomic目的地/BOARD键、控制故意失败后collect、bash-n/Python3.10通过。root/uid与完整接入结果明确synthetic；还需实际assembly及transfer回执fixture，禁止提前上传/上板。原数值/性能未新增，不测温。')
    print('M432_SUPPORT_SYNC',sha(out),len(rejected))


if __name__=='__main__': main()
