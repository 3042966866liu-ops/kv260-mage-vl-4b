"""Matched final-checkpoint head recovery, correct teacher KD and harder student."""
import sys, traceback, math, importlib.util
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common02 import *

def main():
    p = verify()
    c = read(CAP / 'RESULT.json')
    assert c['primary_rc'] == 0
    FIT.mkdir(exist_ok=False)
    started = time.monotonic()
    v = dict(status='FAIL_M541_MATCHED_HEAD_RECOVERY', primary_rc=1, arms={}, board_commands=0, heldout_opened=False)
    try:
        import torch
        import torch.nn.functional as F
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        torch.manual_seed(p['training']['seed'])
        torch.backends.cuda.matmul.allow_tf32 = False
        assert torch.cuda.is_available()
        data = {}
        for r in c['student']:
            f = ROOT / r['source']
            assert sha(f) == r['sha256']
            with np.load(f, allow_pickle=False) as a:
                data[r['key']] = {k: torch.from_numpy(a[k].copy()).cuda() for k in ['x', 'z', 'old_logits']}
        teachers = {}
        for r in c['teacher']:
            f = ROOT / r['source']
            assert sha(f) == r['sha256']
            with np.load(f, allow_pickle=False) as a:
                teachers[r['id']] = torch.from_numpy(a['z'].copy()).cuda()
        A0 = torch.from_numpy(np.load(HEAD / 'A.npy', allow_pickle=False).copy()).cuda()
        B0 = torch.from_numpy(np.load(HEAD / 'B.npy', allow_pickle=False).copy()).cuda()
        source_rows = {r['key']: r for r in c['student']}
        newfit = [r for r in c['student'] if r['role'] == 'fit' and r['view'] == 'clean']
        legacy = [r for r in c['student'] if r['role'] == 'legacy-fit']
        pos = [r for r in newfit if r['target'] == 9454]
        neg = [r for r in newfit if r['target'] == 2753]
        lp = [r for r in legacy if r['target'] == 9454]
        ln = [r for r in legacy if r['target'] == 2753]
        spec = importlib.util.spec_from_file_location('_m541_export_head', HEAD / 'learned_head.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for arm in ['clean_control', 'harder_student']:
            A = torch.nn.Parameter(A0.clone())
            B = torch.nn.Parameter(B0.clone())
            optimizer = torch.optim.AdamW([A, B], lr=p['training']['learning_rate'], weight_decay=0.0)
            history = []
            for step in range(p['training']['steps_per_arm']):
                assert time.monotonic() - started < p['budgets']['fit_seconds']
                optimizer.zero_grad(set_to_none=True)
                batch = [pos[step % len(pos)], neg[step % len(neg)], lp[step % len(lp)], ln[step % len(ln)]]
                losses = []
                records = []
                for r in batch:
                    key = r['key']
                    hard = arm == 'harder_student' and step >= p['training']['clean_steps'] and (r['role'] == 'fit')
                    if hard:
                        key = r['id'] + '_hard-train'
                    x = data[key]
                    z = x['z'] + F.linear(F.linear(x['x'], A), B)
                    ce = F.cross_entropy(z[None], torch.tensor([r['target']], device='cuda'))
                    kd = z.sum() * 0
                    if r['role'] == 'legacy-fit':
                        t = x['old_logits']
                        weight = p['training']['legacy_KL']
                    else:
                        t = teachers[r['id']]
                        weight = p['training']['teacher_KL'] if int(t.argmax()) == r['target'] else 0.0
                    if weight:
                        kd = F.kl_div(F.log_softmax(z / 2, -1), F.softmax(t / 2, -1), reduction='sum') * 4
                    losses.append((ce + weight * kd) / len(batch))
                    records.append(dict(id=r['id'], key=key, target=r['target'], hard_student=hard, CE=float(ce.detach()), KL=float(kd.detach()), KL_weight=weight))
                loss = sum(losses)
                assert torch.isfinite(loss)
                loss.backward()
                norm = float(torch.nn.utils.clip_grad_norm_([A, B], 1.0))
                assert math.isfinite(norm)
                optimizer.step()
                history.append(dict(step=step, loss=float(loss.detach()), gradient_norm=norm, batch=records))
                if step % 32 == 0:
                    print('M541_TRAIN', arm, step, float(loss.detach()), flush=True)
            folder = OPT / 'candidates' / ('M541-demo-head-' + arm + '-01')
            folder.mkdir(exist_ok=False)
            for name, value in [('A', A.detach().float().cpu().numpy()), ('B', B.detach().float().cpu().numpy())]:
                file = folder / (name + '.npy')
                with file.open('xb') as out:
                    np.save(out, np.ascontiguousarray(value), allow_pickle=False)
            (folder / 'learned_head.py').open('xb').write((HEAD / 'learned_head.py').read_bytes())
            manifest = dict(scale=1.0, rank=8, full_vocab=151936, arm=arm, inference_extra_MACs=1235968, body_unmodified=True, no_token_specific_bias=True, source_sha256=sha(folder / 'learned_head.py'), training_scope='Only existing rank8 full-vocabulary head; frozen actual student body,not body recovery.', protocol_sha256=sha(PROTO), capture_sha256=sha(CAP / 'RESULT.json'), steps=p['training']['steps_per_arm'], A=dict(path='A.npy', sha256=sha(folder / 'A.npy'), bytes=(folder / 'A.npy').stat().st_size), B=dict(path='B.npy', sha256=sha(folder / 'B.npy'), bytes=(folder / 'B.npy').stat().st_size))
            save(folder / 'HEAD_MANIFEST.json', manifest)
            files = [dict(path=f.name, sha256=sha(f), bytes=f.stat().st_size) for f in sorted(folder.iterdir())]
            save(folder / 'PACKAGE_MANIFEST.json', dict(files=files, file_count=len(files), total_bytes=sum((r['bytes'] for r in files))))
            head = module.LearnedHead(folder, manifest)
            evaluated = []
            for r in c['student']:
                f = ROOT / r['source']
                with np.load(f, allow_pickle=False) as a:
                    cpu = head.add(a['x'][None], a['z'][None])[0]
                target = r['target']
                i = int(cpu.argmax())
                other = cpu.copy()
                other[target] = -np.inf
                ev = dict(key=r['key'], id=r['id'], role=r['role'], view=r['view'], target=target, token_id=i, correct=i == target, target_gap=float(cpu[target]) - float(other.max()))
                evaluated.append(ev)
            first = c['student'][0]
            with np.load(ROOT / first['source'], allow_pickle=False) as a:
                single = head.add(a['x'][None], a['z'][None])
                padded = np.repeat(a['z'][None], 32, axis=0)
                out = head.add(a['x'][None], padded)
                assert np.array_equal(single, out[:1]) and np.array_equal(out[1:], padded[1:])
            acceptance = [r for r in evaluated if r['role'] != 'fit']
            passed = all((r['correct'] for r in acceptance))
            v['arms'][arm] = dict(package=rel(folder), manifest_sha256=sha(folder / 'PACKAGE_MANIFEST.json'), steps=p['training']['steps_per_arm'], history=history, evaluations=evaluated, acceptance_correct=sum((r['correct'] for r in acceptance)), acceptance_n=len(acceptance), acceptance_pass=passed, fit_correct=sum((r['correct'] for r in evaluated if r['role'] == 'fit')), fit_n=sum((r['role'] == 'fit' for r in evaluated)), minimum_acceptance_target_gap=min((r['target_gap'] for r in acceptance)), single_and_padded32_interface_pass=True)
            print('M541_FINAL', arm, v['arms'][arm]['acceptance_correct'], len(acceptance), passed, flush=True)
        a = v['arms']['clean_control']
        b = v['arms']['harder_student']
        assert a['history'][:p['training']['clean_steps']] == b['history'][:p['training']['clean_steps']]
        chosen = 'harder_student' if b['acceptance_pass'] else 'clean_control' if a['acceptance_pass'] else None
        v.update(status='COMPLETE_M541_MATCHED_DEMO_HEAD_TRAINING', primary_rc=0, selected_arm=chosen, selection_rule='Both fixed final checkpoints only;prefer harder if all predeclared acceptance correct,else clean if all correct,else no candidate. No epoch/seed search.', total_optimizer_updates=2 * p['training']['steps_per_arm'], equal_initialization_and_clean_prefix=True, base_body_unchanged=True, changed_rank_or_inference_work=False, independent_generalization_claim=False)
    except BaseException:
        v['traceback'] = traceback.format_exc()
    v['elapsed_s'] = time.monotonic() - started
    save(FIT / 'RESULT.json', v)
    print(v['status'], v.get('traceback', ''), v.get('selected_arm'), flush=True)
    return v['primary_rc']
if __name__ == '__main__':
    raise SystemExit(main())
