"""Read-only real runtime import/interface probe. Never instantiate hardware."""
import ast
import base64
import hashlib
import inspect
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
RELEASE = Path('/home/ubuntu/tellme_release_install_20260926')
EXPECTED_MANIFEST = 'fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e'


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result = dict(status='FAIL_IMPORT_ONLY', overlay_loaded=False, model_loaded=False,
                  hardware_gate_run=False, performance_pass=False)
    try:
        if digest(RELEASE / 'INSTALL_PACKAGE_MANIFEST.json') != EXPECTED_MANIFEST:
            raise RuntimeError('Installed manifest identity mismatch')
        d = RELEASE / 'deployment/mage_vl4b'
        paths = [RELEASE / 'runtime_site']
        paths += [d / name for name in (
            'm277_m276_fixed_window_board_candidate', 'm254_dual_path_web_candidate',
            'm243_web_prefill_board_candidate', 'm242_m241_fixed_text_board_candidate',
            'm238_input_prefetch_board_candidate', 'm241_grouped_gqa_board_candidate',
            'm231_parse_reuse_board_candidate')]
        paths += [RELEASE / name for name in (
            'tmp/m227_runtime_base/m227_runtime_base_patch',
            'tmp/m223_realtime/m223_realtime_delta',
            'tmp/m218_dual_source/m218_dual_source_delta')]
        paths += [d / 'm181_m120_video_board_candidate' / name for name in
                  ('text_runtime', 'ps_vision_payload', '')]
        paths += [d / 'm175_m120_fixed_text_candidate/runtime',
                  d / 'm175_m120_fixed_text_candidate/runtime/support']
        if not all(p.is_dir() for p in paths): raise RuntimeError('Import directory missing')
        sys.path[0:0] = list(map(str, paths))
        import board_runtime
        import m238_prefill_runtime
        import m241_video_language_runtime
        modules = (board_runtime, m238_prefill_runtime, m241_video_language_runtime)
        result['modules'] = {}
        for module in modules:
            path = Path(module.__file__).resolve()
            path.relative_to(RELEASE.resolve())
            result['modules'][module.__name__] = dict(path=str(path), sha256=digest(path))
        runtime = m238_prefill_runtime.M238PrefillRuntime
        model = m241_video_language_runtime.M241VideoLanguageModel
        for name in ('_prepare_block', '_parse_buffer', '_parse_into_and_check',
                     '_launch_prepacked', '_launch_once', '_stage', 'lm_head'):
            if not callable(getattr(runtime, name, None)): raise RuntimeError('Missing '+name)
        module = sys.modules[model.prefill.__module__]
        for name in ('rms_norm', 'apply_rope', 'causal_attention_grouped', 'silu'):
            if not callable(getattr(module, name, None)): raise RuntimeError('Missing PS '+name)
        source = inspect.getsource(board_runtime.copy_window_to_buffer)
        import textwrap
        source = textwrap.dedent(source).strip().replace('\r\n', '\n')
        result['transfer_source_sha256'] = hashlib.sha256(source.encode()).hexdigest()
        if result['transfer_source_sha256'] != '56825701b6bda461c87340986bd67165a7bca59d7652a055bbb7bb2d8b3597d9':
            raise RuntimeError('Transfer implementation differs from pinned source')
        ast.parse(source)
        result['status'] = 'PASS_REAL_RUNTIME_IMPORT_INTERFACES_ONLY'
    except BaseException as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    payload = (json.dumps(result, indent=2)+'\n').encode()
    print('M338_RESULT_SHA256='+hashlib.sha256(payload).hexdigest(), flush=True)
    print('M338_RESULT_BASE64='+base64.b64encode(payload).decode(), flush=True)
    return 0 if result['status'].startswith('PASS') else 1


if __name__ == '__main__': raise SystemExit(main())
