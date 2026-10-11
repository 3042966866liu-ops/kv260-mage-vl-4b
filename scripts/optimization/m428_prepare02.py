"""Accepted late11 saved-feature task gate, unchanged actually passed language executor."""
import ast
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
OLD = BASE / 'candidates/M421-combination-saved-language-01'
PKG = BASE / 'candidates/M428-late11-saved-language-02'


def once(s, a, b):
    if s.count(a) != 1:
        raise RuntimeError('Derivation anchor differs: '+a[:80])
    return s.replace(a, b)


def main():
    if PKG.exists():
        raise RuntimeError('Immutable packet exists')
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior = {}
    for k in ('latest_m427_half_software_board', 'latest_m427_half_closure',
              'latest_m426_range_software_board', 'latest_m421_saved_language_board',
              'latest_m421_saved_language_closure', 'latest_m368_video_closure'):
        e = board[k]
        assert sha(ROOT / e['result']) == e['sha256']
        assert all(e['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig')
                   for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        prior[k] = e
    r = json.loads((ROOT / prior['latest_m427_half_software_board']['result']).read_bytes())
    a = json.loads((ROOT / prior['latest_m426_range_software_board']['result']).read_bytes())
    assert r['feature_pass_ranges'] == ['late_13_23'] and r['visual_owner_closed'] and r['bindings_restored']
    passed = json.loads((ROOT / prior['latest_m421_saved_language_board']['result']).read_bytes())
    assert passed['status'] == 'PASS_M421_SAVED_FEATURE_DECISION_CONSISTENCY'
    manifest = json.loads((OLD / 'PACKAGE_MANIFEST.json').read_bytes())
    assert prior['latest_m421_saved_language_board']['manifest_sha256'] == sha(OLD / 'PACKAGE_MANIFEST.json')
    for row in manifest['files']:
        assert sha(OLD / row['path']) == row['sha256'] and (OLD / row['path']).stat().st_size == row['bytes']
    row = next(x for x in r['ranges'] if x['name'] == 'late_13_23')
    orig = a['retained_features'][0]; cand = row['saved_feature']
    plan = json.loads((OLD / 'PLAN.json').read_bytes())
    plan.pop('M420_raw_sha256'); plan.pop('feature_directory')
    plan.update(prerequisites=prior, accepted_range='late_13_23', selected_layers=list(range(13, 24)),
                M426_raw_sha256=prior['latest_m426_range_software_board']['sha256'],
                M426_raw_bytes=(ROOT / prior['latest_m426_range_software_board']['result']).stat().st_size,
                M427_raw_sha256=prior['latest_m427_half_software_board']['sha256'],
                M427_raw_bytes=(ROOT / prior['latest_m427_half_software_board']['result']).stat().st_size,
                feature_directories=dict(original='/home/ubuntu/m426_range_software_02', candidate='/home/ubuntu/m427_half_ranges_software_01'),
                features=[dict(path=orig['path'], file_bytes=orig['bytes'], file_sha256=orig['sha256'], tensor=a['original_visual'], source='original'),
                          dict(path=cand['path'], file_bytes=cand['bytes'], file_sha256=cand['sha256'], tensor=row['candidate_visual'], source='candidate')],
                variants=['original', 'late13_23_candidate'], temperature_measurement_enabled=False,
                performance_unlocked=False, actual_visual_forward_calls=0)
    texts = {}
    for name in ('m421_gate.py', 'm421_trials.py', 'm421_export.py', 'run_m421.sh'):
        text = (OLD / name).read_text(encoding='utf-8').replace('m421', 'm428').replace('M421', 'M428').replace('layer12_13_candidate', 'late13_23_candidate')
        if name == 'm421_gate.py':
            text = once(text, "plan['M420_raw_sha256']", "plan['M427_raw_sha256']")
            text = once(text, "performance_pass=False, formal_promotion_allowed=False,", "performance_pass=False, formal_promotion_allowed=False, temperature_measurement_enabled=False,")
        texts[name.replace('421', '428')] = text
    normal = texts['m428_trials.py'].replace('m428', 'm421').replace('M428', 'M421').replace('late13_23_candidate', 'layer12_13_candidate')
    assert ast.dump(ast.parse(normal)) == ast.dump(ast.parse((OLD / 'm421_trials.py').read_text(encoding='utf-8')))
    helper = (HERE / 'm428_saved_features02.py').read_text(encoding='utf-8')
    old_helper = (OLD / 'm421_saved_features.py').read_text(encoding='utf-8')
    helper += '\n\n' + old_helper[old_helper.index('def save_array'):]
    helper += '\n\n' + old_helper[old_helper.index('def tensor'):old_helper.index('def load_features')]
    texts['m428_saved_features.py'] = helper
    assembly = (OLD / 'm421_assemble.py').read_text(encoding='utf-8')
    assembly = once(assembly, '/home/ubuntu/m415_saved_feature_candidate_04', '/home/ubuntu/m421_saved_feature_candidate_01')
    assembly = once(assembly, '20d90f813051938818301c1c7714cc73a6b977c663f7b47c1156e90dae423e2d', sha(OLD / 'PACKAGE_MANIFEST.json'))
    texts['m428_assemble.py'] = assembly.replace('M421_ASSEMBLY_PASS', 'M428_ASSEMBLY_PASS')
    gate = texts['m428_gate.py']
    assert gate.index('load_features(plan)') < gate.index('import pynq') < gate.index('engine.load()') < gate.index("patch(tokenizers,'Tokenizer',original_tokenizer)")
    assert not any(word in gate for word in ('thermal_zone', 'temperature_mC'))
    PKG.mkdir()
    changed = {row['path'] for row in manifest['files'] if row['path'].startswith('m421') or row['path'] in ('PLAN.json', 'SHA256SUMS', 'run_m421.sh')}
    for row in manifest['files']:
        if row['path'] not in changed:
            atomic(PKG / row['path'], (OLD / row['path']).read_bytes(), immutable=True)
    for name, text in texts.items():
        if name.endswith('.py'):
            ast.parse(text, feature_version=(3, 10))
        atomic(PKG / name, text.encode('utf-8'), immutable=True)
    atomic(PKG / 'PLAN.json', encoded(plan), immutable=True)
    atomic(PKG / 'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'), immutable=True)
    files = sorted(PKG.iterdir())
    m = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files), files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(m), immutable=True)
    value = dict(status='PREPARED_M428_ACCEPTED_LATE11_SAVED_FEATURE_TASK', prerequisites=prior,
                 manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'), file_count=m['file_count'], total_bytes=m['total_bytes'],
                 plan=plan, unchanged_language_trial_AST_except_names=True, features_before_Overlay=True,
                 complete_original_reference_preserved=True, tokenizer_restore_preserved=True,
                 actual_visual_forward_calls=0, extra_DMA=0, temperature_measurement_enabled=False,
                 task_pass=False, board_run=False, performance_pass=False)
    p = BASE / 'runs/M428-saved-language-preparation-02/RESULT.json'
    atomic(p, encoded(value), immutable=True)
    sync('latest_m428_saved_language_preparation', dict(status=value['status'], result=p.relative_to(ROOT).as_posix(), sha256=sha(p), manifest_sha256=value['manifest_sha256']),
         f'## M428 后11层保存特征接原语言准备（2026-10-06）\n\nSHA {sha(p)}；manifest {value["manifest_sha256"]}。仅M427已过原特征阈值13–23范围，与M426保存原版同159输入接相同M421实际通过语言/LM head执行器，数学AST除名字相同。0视觉重算，原七DMA封锁新增，无固定CMA floor，PS1024MiB＋64MiB余量保持，不测温。先真实helper/完整collector/实际exporter配套组件，任务通过前不解锁PL视觉性能。未上板。')
    print('M428_PREPARATION_SYNC', sha(p), value['manifest_sha256'], m['file_count'], m['total_bytes'])


if __name__ == '__main__':
    main()
