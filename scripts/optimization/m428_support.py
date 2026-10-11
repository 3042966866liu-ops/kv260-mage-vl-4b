"""Actual saved loader/exporter/assembler plus explicit synthetic host evidence."""
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
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
import m428_workflow as w


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    pkg = w.PKG; plan = json.loads((pkg / 'PLAN.json').read_bytes()); digest = sha(pkg / 'PACKAGE_MANIFEST.json')
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    loader = module('actual_m428_loader', pkg / 'm428_saved_features.py')
    exporter = module('actual_m428_exporter', pkg / 'm428_export.py')
    assembler = module('actual_m428_assembler', pkg / 'm428_assemble.py')
    rejected = []
    def reject(label, call):
        try:
            call()
        except (ValueError, RuntimeError, KeyError, AssertionError, OSError):
            rejected.append(label)
        else:
            raise AssertionError('Invalid input accepted: '+label)
    actual_lstat = Path.lstat
    def explicit_root_fixture_stat(p, *args, **kwargs):
        s = actual_lstat(p, *args, **kwargs)
        return SimpleNamespace(**{k: getattr(s, k) for k in
            ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink')}, st_uid=0)
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
        root = Path(tmp); folders = {'original': root / 'original', 'candidate': root / 'candidate'}
        for p in folders.values():
            p.mkdir()
        x = np.linspace(-1, 1, 98*2560, dtype=np.float32).reshape(98, 2560)
        arrays = [loader.save_array(folders['original'] / 'original_visual.npy', x),
                  loader.save_array(folders['candidate'] / 'late_13_23_candidate_visual.npy', x+.01)]
        a = json.loads((ROOT / board['latest_m426_range_software_board']['result']).read_bytes())
        r = json.loads((ROOT / board['latest_m427_half_software_board']['result']).read_bytes())
        a['original_visual'] = arrays[0]['tensor']
        a['retained_features'][0] = dict(path=arrays[0]['path'], bytes=arrays[0]['file_bytes'], sha256=arrays[0]['file_sha256'])
        (folders['original'] / 'BOARD_RESULT.json').write_bytes(encoded(a))
        fake = copy.deepcopy(plan)
        fake['M426_raw_sha256'] = sha(folders['original'] / 'BOARD_RESULT.json')
        fake['M426_raw_bytes'] = (folders['original'] / 'BOARD_RESULT.json').stat().st_size
        r['baseline_source_sha256'] = fake['M426_raw_sha256']; r['original_visual'] = arrays[0]['tensor']
        selected = next(row for row in r['ranges'] if row['name'] == 'late_13_23')
        selected['candidate_visual'] = arrays[1]['tensor']
        selected['saved_feature'] = dict(path=arrays[1]['path'], bytes=arrays[1]['file_bytes'], sha256=arrays[1]['file_sha256'])
        def write_source(value):
            p = folders['candidate'] / 'BOARD_RESULT.json'; p.write_bytes(encoded(value))
            return dict(fake, M427_raw_sha256=sha(p), M427_raw_bytes=p.stat().st_size)
        fake['features'] = [dict(row, source=source) for row, source in zip(arrays, ('original', 'candidate'))]
        fake = write_source(r)
        with patch.object(Path, 'lstat', explicit_root_fixture_stat):
            actual, ids = loader.load_features(fake, folders)
            assert len(actual) == 2 and all(not v.flags.writeable for v in actual)
            assert np.array_equal(actual[0], x) and np.array_equal(actual[1], x+.01)
            for key, value in [('status', 'REJECT_M427_BOTH_HALF_RANGES'), ('gate_return_code', True),
                               ('gate_return_code', 1), ('visual_owner_closed', False),
                               ('bindings_restored', False), ('baseline_source_sha256', '0'*64),
                               ('feature_pass_ranges', []), ('overlay_loaded', True),
                               ('dma_allocations', 1), ('language_forward_calls', 1),
                               ('temperature_measurement_enabled', True)]:
                bad = copy.deepcopy(r); bad[key] = value; p = write_source(bad)
                reject('saved-source-'+key+str(value), lambda p=p: loader.load_features(p, folders))
            fake = write_source(r)
            reject('source-raw-SHA', lambda: loader.load_features(dict(fake, M427_raw_sha256='0'*64), folders))
            reject('selected-range', lambda: loader.load_features(dict(fake, selected_layers=[12, 13]), folders))
            bad = copy.deepcopy(r); late = next(row for row in bad['ranges'] if row['name'] == 'late_13_23')
            late['full_visual_quality']['thresholds']['maximum_relative_l2'] = .04
            p = write_source(bad); reject('feature-threshold', lambda: loader.load_features(p, folders))
            fake = write_source(r)
            p = folders['candidate'] / arrays[1]['path']; original_bytes = p.read_bytes()
            p.write_bytes(original_bytes[:-1]+bytes([original_bytes[-1]^1]))
            reject('feature-full-SHA', lambda: loader.load_features(fake, folders)); p.write_bytes(original_bytes)
            reject('file-size', lambda: loader.read_owned(p, 1, sha(p)))
        def explicit_nonroot_fixture_stat(path, *args, **kwargs):
            s = explicit_root_fixture_stat(path, *args, **kwargs)
            s.st_uid = 1000
            return s
        with patch.object(Path, 'lstat', explicit_nonroot_fixture_stat):
            reject('nonroot-owner', lambda: loader.read_owned(p, p.stat().st_size, sha(p)))
        # Actual assembler with original manifest/bytes; only filesystem roots replaced.
        stage = root / 'stage'; stage.mkdir(); old = BASE / 'candidates/M421-combination-saved-language-01'
        old_rows = {x['path']: x for x in json.loads((old / 'PACKAGE_MANIFEST.json').read_bytes())['files']}
        m = json.loads((pkg / 'PACKAGE_MANIFEST.json').read_bytes())
        shutil.copyfile(pkg / 'PACKAGE_MANIFEST.json', stage / 'PACKAGE_MANIFEST.json')
        for row in m['files']:
            if old_rows.get(row['path']) != row:
                shutil.copyfile(pkg / row['path'], stage / row['path'])
        assembler.HERE = stage; assembler.OLD = old
        with patch.object(sys, 'argv', ['assembler', digest]), contextlib.redirect_stdout(io.StringIO()) as assembly_output:
            assembler.main()
        assert f'M428_ASSEMBLY_PASS {digest} {m["file_count"]} {m["total_bytes"]}' in assembly_output.getvalue()
        assert all(sha(stage / row['path']) == row['sha256'] for row in m['files'])
        with patch.object(sys, 'argv', ['assembler', '0'*64]):
            reject('assembly-manifest', assembler.main)
        (stage / 'PLAN.json').write_bytes(b'corrupt')
        with patch.object(sys, 'argv', ['assembler', digest]):
            reject('assembly-payload-SHA', assembler.main)
        # Explicit synthetic collector fixture from passed language record, new metadata only.
        r = json.loads((ROOT / board['latest_m421_saved_language_board']['result']).read_bytes())
        r.update(status='PASS_M428_SAVED_FEATURE_DECISION_CONSISTENCY', manifest_sha256=digest,
                 selected_layers=plan['selected_layers'], saved_feature_source_sha256=plan['M427_raw_sha256'],
                 temperature_measurement_enabled=False,
                 saved_feature_identities=[dict(path=plan['feature_directories'][x['source']]+'/'+x['path'], file_sha256=x['file_sha256'], tensor=x['tensor']) for x in plan['features']])
        r['samples'][1]['variant'] = 'late13_23_candidate'; r['samples'][1]['visual'] = plan['features'][1]['tensor']
        r['logit_files'][1]['path'] = 'late13_23_candidate_logits.npy'
        path = root / 'export.json'; exporter.OUTPUT = path
        def actual_export(value):
            path.write_bytes(encoded(value)); out = io.StringIO()
            with patch.object(exporter.os, 'geteuid', return_value=0, create=True), \
                 patch.object(exporter.time, 'sleep', return_value=None), contextlib.redirect_stdout(out):
                exporter.emit_saved()
            return out.getvalue()
        text = actual_export(r); assert w.decode(text)[2] == r
        for label in ('wrong-source', 'scope-layer', 'original-logits', 'missing-KV', 'candidate-shape',
                      'logical-count', 'physical-count', 'DMA-release', 'changed-decision', 'visual-recomputed',
                      'tokenizer-restore', 'head-AST', 'logit-file', 'sample-order', 'unsafe', 'observer-alive', 'temperature'):
            bad = copy.deepcopy(r)
            if label == 'wrong-source': bad['saved_feature_source_sha256'] = '0'*64
            elif label == 'scope-layer': bad['selected_layers'] = [12]
            elif label == 'original-logits': bad['samples'][0]['logits']['sha256'] = '0'*64
            elif label == 'missing-KV': bad['samples'][1]['values'].pop()
            elif label == 'candidate-shape': bad['samples'][1]['logits']['shape'] = [1]
            elif label == 'logical-count': bad['samples'][1]['counts']['logical_calls'] -= 1
            elif label == 'physical-count': bad['fpga_transactions'] -= 1
            elif label == 'DMA-release': bad['released_buffers'].pop()
            elif label == 'changed-decision': bad['logit_comparison']['same_constrained_decision'] = False
            elif label == 'visual-recomputed': bad['vision_forward_calls'] = 1
            elif label == 'tokenizer-restore': bad['request_tokenizer_restored_before_prefill'] = False
            elif label == 'head-AST': bad['head_observer_proof']['removed_observation_calls_ast_equals_original'] = False
            elif label == 'logit-file': bad['logit_files'][1]['file_bytes'] -= 1
            elif label == 'sample-order': bad['samples'].reverse()
            elif label == 'unsafe': bad['final_snapshot']['ap_return'] = 0
            elif label == 'observer-alive': bad['samples'][1]['sampled_memory']['observer_stopped'] = False
            else: bad['temperature_measurement_enabled'] = True
            reject('collector-'+label, lambda bad=bad: w.check(bad))
        for label, bad in [('truncated', text[:text.index('M428_RESULT_CHUNK=1/')]), ('duplicate', text+text),
                           ('unordered', text.replace('M428_RESULT_CHUNK=1/', 'M428_RESULT_CHUNK=0/')),
                           ('wrong-rc', text.replace('M428_SAVED_GATE_RC=0', 'M428_SAVED_GATE_RC=1'))]:
            reject('export-'+label, lambda bad=bad: w.decode(bad))
        failure = dict(r, status='FAIL', errors=['Explicit synthetic source failure'], gate_return_code=1,
                       features_verified_before_overlay=False, overlay_loaded=False, model_forward_calls=0)
        assert w.decode(actual_export(failure))[2] == failure
        wrong = dict(r, gate_level='CPU-only-two-half-visual-MLP-screen')
        reject('actual-exporter-gate-level', lambda: actual_export(wrong))
    for p in pkg.glob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'), feature_version=(3, 10))
    g = (pkg / 'm428_gate.py').read_text(encoding='utf-8')
    assert g.index('load_features(plan)') < g.index('import pynq') < g.index('engine.load()') < g.index("patch(tokenizers,'Tokenizer',original_tokenizer)")
    assert 'Same-terminal root required' in g and 'Allocator sealed: extra DMA allocation refused' in g
    cp = subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe', '-NoProfile', '-File', str(HERE / 'm428_control.ps1'), '-Mode', 'SelfTest'], capture_output=True)
    assert cp.returncode == 0 and b'M428_CONTROL_SELF_TEST_PASS' in cp.stdout
    cp = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', '/bin/bash', '-n', '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(pkg / 'run_m428.sh').relative_to(ROOT).as_posix()], capture_output=True)
    atomic(ROOT / 'tmp/m42801/bash.stdout.bin', cp.stdout, immutable=True)
    atomic(ROOT / 'tmp/m42801/bash.stderr.bin', cp.stderr, immutable=True)
    assert cp.returncode == 0, (cp.stdout, cp.stderr)
    value = dict(status='PASS_M428_ACTUAL_SAVED_LOADER_EXPORT_ASSEMBLY_SUPPORT', manifest_sha256=digest,
                 negative_checks=rejected, actual_full_size_NPY_save_load=True,
                 actual_exporter_to_actual_decoder=True, actual_assembler_complete_manifest=True,
                 fixture_root_owner_and_euid_pacing_explicitly_mocked=True, synthetic_language_collector_fixture=True,
                 complete_unchanged_language_AST_proof_reused=True, Python310_syntax=True,
                 runner_bash_n=True, control_failure_collection_selftest=True, board_run=False,
                 task_pass=False, performance_pass=False, temperature_measurement_enabled=False,
                 source_sha256={n: sha(HERE / n) for n in ('m428_prepare02.py', 'm428_host_prepare.py', 'm428_support.py', 'm428_workflow.py', 'm428_control.ps1')})
    out = BASE / 'runs/M428-saved-language-support-01/RESULT.json'
    atomic(out, encoded(value), immutable=True)
    sync('latest_m428_saved_language_support', dict(status=value['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=digest),
         f'## M428 保存后11层特征任务门禁支持（2026-10-06）\n\nSHA {sha(out)}；实际全尺寸NPY保存/加载、原件SHA/身份/源quality及原阈值，实际exporter→实际decoder、真实manifest组装和{len(rejected)}项拒绝检查通过。root身份/导出euid/限速在离线fixture明确模拟，语言结果为明确合成结构校验，不宣称任务质量或新硬件。Python3.10/bash-n/故意失败收集通过；只允许同COM3 sudo后一次保存特征原语言判断，不重复视觉、不测温。')
    print('M428_SUPPORT_SYNC', sha(out), len(rejected))


if __name__ == '__main__':
    main()
