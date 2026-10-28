"""Fresh complete student reload with exported recovery, not cached-only acceptance."""
import sys, traceback, gc, importlib.util
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common02 import *

def main():
    p = verify()
    fit = read(FIT / 'RESULT.json')
    assert fit['primary_rc'] == 0 and fit['selected_arm'] is not None
    selected = fit['arms'][fit['selected_arm']]
    folder = ROOT / selected['package']
    assert sha(folder / 'PACKAGE_MANIFEST.json') == selected['manifest_sha256']
    for r in read(folder / 'PACKAGE_MANIFEST.json')['files']:
        assert sha(folder / r['path']) == r['sha256']
    RELOAD.mkdir(exist_ok=False)
    v = dict(status='FAIL_M541_EXPORTED_FULL_RELOAD', primary_rc=1, samples=[], board_commands=0, heldout_opened=False)
    start = time.monotonic()
    e = None
    override = None
    try:
        spec = importlib.util.spec_from_file_location('_m541_fresh_head', folder / 'learned_head.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        head = mod.LearnedHead(folder, read(folder / 'HEAD_MANIFEST.json'))
        e = setup_engine()
        torch = e.torch
        e.set_active(p['vision'], p['language'])
        sys.path.insert(0, str(ROOT / 'experiments/v4_recovery_20261025'))
        from v4_recovery_native import V4Recovery
        override = V4Recovery(torch, core(e.original_vision[4]).mlp, BODY, lambda: None)
        override.select(True)
        versions = [(q, q._version, q.data_ptr(), tuple(q.shape)) for m in override.new for q in m.parameters()]
        capture = read(CAP / 'RESULT.json')
        rows = {r['key']: r for r in capture['student']}
        expected = {r['key']: r for r in selected['evaluations']}
        requests = [r for r in p['student_cases'] if r['role'] != 'fit']
        assert len(requests) == p['budgets']['reload_prefills']
        for r in requests:
            assert time.monotonic() - start < p['budgets']['reload_seconds']
            f = ROOT / r['frame']
            assert sha(f) == r['frame_sha256']
            x, z, features = forward(e, np.load(f, allow_pickle=False), p['token_ids'])
            final = head.add(x[None], z[None])[0]
            prior = rows[r['key']]
            assert sha(ROOT / prior['source']) == prior['sha256']
            with np.load(ROOT / prior['source'], allow_pickle=False) as a:
                assert np.array_equal(a['x'], x) and np.array_equal(a['z'], z), 'Full student rerun differs from captured training/evaluation body'
            score = decision(final, r['target'], e.tokenizer)
            assert score['token_id'] == expected[r['key']]['token_id']
            assert all((q._version == n and q.data_ptr() == ptr and (tuple(q.shape) == shape) for q, n, ptr, shape in versions))
            file = RELOAD / (r['key'] + '.npz')
            npz(file, x=x, base_logits=z, logits=final, features=features)
            row = dict(r, **score, payload=rel(file), sha256=sha(file), base_logits_and_hidden_reproduced_exact=True, tokens=128, views=2, visual_slots=98, cache_before=0, cache_after_clear=0, cache_layers=18, parameter_versions_unchanged=True, decode_calls=0)
            v['samples'].append(row)
            save(RELOAD / (r['key'] + '.json'), row)
            print('M541_RELOAD', r['key'], repr(score['raw_token']), score['correct'], flush=True)
            gc.collect()
        assert head.calls == len(requests) == len(v['samples'])
        v.update(status='COMPLETE_M541_FRESH_EXPORTED_FULL_STUDENT_RELOAD', primary_rc=0, all_acceptance_correct=all((r['correct'] for r in v['samples'])), correct=sum((r['correct'] for r in v['samples'])), n=len(v['samples']), selected_arm=fit['selected_arm'], package=selected['package'], body_unchanged=True, no_board_TTFT=True, not_independent_test=True, production_promoted=False)
    except BaseException:
        v['traceback'] = traceback.format_exc()
    finally:
        if override is not None:
            override.close()
        if e is not None:
            e.close()
        v['elapsed_s'] = time.monotonic() - start
        save(RELOAD / 'RESULT.json', v)
        print(v['status'], v.get('traceback', ''), flush=True)
    return v['primary_rc']
if __name__ == '__main__':
    raise SystemExit(main())
