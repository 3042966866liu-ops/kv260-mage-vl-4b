"""Freeze late11 full-request numerical preparation, never execute a model."""
import ast
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once

OLD = BASE / 'candidates/M423-integrated-video-01'
LANG = BASE / 'candidates/M428-late11-saved-language-02'
VIS = BASE / 'candidates/M430-late11-visual-warm-02'
PKG = BASE / 'candidates/M432-late11-integrated-video-01'


def main():
    if PKG.exists():
        raise RuntimeError('Immutable preparation exists')
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior = {}
    for key in ('latest_m431_borrowed_CPU_board', 'latest_m431_borrowed_CPU_closure', 'latest_m430_complete_visual_board',
                'latest_m430_complete_visual_closure', 'latest_m429_late11_visual_board', 'latest_m428_saved_language_board', 'latest_m427_half_software_board'):
        # The numerical key is discovered by exact raw identity below if older hosts use another spelling.
        if key == 'latest_m429_late11_visual_board' and key not in board:
            candidates = [(k, e) for k, e in board.items() if isinstance(e, dict) and e.get('sha256') == 'aea5b14fef0237ed9c4a5d04cd2f4e38af36f68a97f53ad4796f10fcf89d4813']
            if len(candidates) != 1:
                raise RuntimeError('Unique accepted visual numerical evidence required')
            actual_key, e = candidates[0]
        else:
            actual_key, e = key, board[key]
        if sha(ROOT / e['result']) != e['sha256'] or not all(e['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md')):
            raise RuntimeError('Prerequisite not synchronized')
        prior[actual_key] = e
        if key == 'latest_m429_late11_visual_board':
            visual_e = e
    if not board['latest_m431_borrowed_CPU_closure']['CPU_component_pass'] or not board['latest_m430_complete_visual_closure']['performance_pass']:
        raise RuntimeError('CPU and worthwhile visual prerequisites required')
    for folder in (OLD, LANG, VIS):
        m = json.loads((folder / 'PACKAGE_MANIFEST.json').read_bytes())
        for row in m['files']:
            if (folder / row['path']).stat().st_size != row['bytes'] or sha(folder / row['path']) != row['sha256']:
                raise RuntimeError('Frozen prior packet changed')
    plan = json.loads((LANG / 'PLAN.json').read_bytes())
    vp = json.loads((VIS / 'PLAN.json').read_bytes())
    plan.update(prerequisites=prior, integrated_visual_calls=2, integrated_language_calls=2, extra_DMA=0,
                performance_measurement=False, visual_logical_calls=286, total_language_logical_calls=1556,
                additional_visual_stage_bytes=49020928, actual_visual_forwards=2,
                CPU_manifest_sha256=board['latest_m431_borrowed_CPU_board']['manifest_sha256'],
                visual_reused_packages=[dict(directory='/home/ubuntu/m430_late11_visual_warm_candidate_02', manifest_sha256=sha(VIS / 'PACKAGE_MANIFEST.json'))] + vp['reused_packages'],
                layout_sha256=vp['layout_sha256'], chains=vp['chains'], windows=vp['windows'],
                numerical_rule='A and B each exact their accepted M428 sample: complete visual/embedding/154families/72KV/logits/decision/retry; candidate additionally all286 wire and24 visual boundaries exact saved M427. No new quality threshold.',
                request_boundary='Two sequential fixed numerical requests, original visual then late11 PL visual, each unchanged original language and full LM head. No performance claim or service admission.',
                temperature_measurement_enabled=False)
    sources = {
        'visual': (visual_e, '/home/ubuntu/m429_late11_visual_numeric_02/BOARD_RESULT.json'),
        'language': (board['latest_m428_saved_language_board'], '/home/ubuntu/m428_saved_feature_language_01/BOARD_RESULT.json'),
        'software': (board['latest_m427_half_software_board'], '/home/ubuntu/m427_half_ranges_software_01/BOARD_RESULT.json'),
        'CPU': (board['latest_m431_borrowed_CPU_board'], '/home/ubuntu/m431_borrowed_cpu_result_01/BOARD_RESULT.json'),
    }
    plan['integrated_sources'] = {name: dict(path=remote, bytes=(ROOT / e['result']).stat().st_size, sha256=e['sha256'], status=e['status']) for name, (e, remote) in sources.items()}
    g = (OLD / 'm423_gate.py').read_text(encoding='utf-8')
    g = g.replace('m423', 'm432').replace('M423', 'M432')
    g = once(g, '/home/ubuntu/m432_integrated_video_01', '/home/ubuntu/m432_late11_integrated_video_01')
    g = g.replace('from m432_saved_features import', 'from m428_saved_features import')
    g = once(g, "plan['M420_raw_sha256']", "plan['M427_raw_sha256']")
    g = once(g, 'numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,', 'numerical_pass=False, performance_pass=False, formal_promotion_allowed=False, temperature_measurement_enabled=False,')
    g = g.replace('layers12-13', 'layers13-23').replace('two real original/candidate visual calls borrowing existing seven buffers', 'two real original/late11 candidate visual calls borrowing existing seven buffers')
    # Lossless compact result; never discard numerical/physical evidence to fit export.
    g = once(g, 'from measurement import sha256, write_json', '''from measurement import sha256
def write_json(path,value):
    path=Path(path);payload=(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\\n').encode('utf-8')
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+f'.{os.getpid()}.partial')
    with temp.open('wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)''')
    t = (OLD / 'm423_trials.py').read_text(encoding='utf-8').replace('m423', 'm432').replace('M423', 'M432')
    t = t.replace('from m432_saved_features import', 'from m428_saved_features import').replace('layer12_13_candidate', 'late13_23_candidate').replace('saved M421 reference', 'saved M428 reference')
    normalized = t.replace('m432', 'm423').replace('M432', 'M423').replace('from m428_saved_features import', 'from m423_saved_features import').replace('late13_23_candidate', 'layer12_13_candidate').replace('saved M428 reference', 'saved M421 reference')
    if ast.dump(ast.parse(normalized)) != ast.dump(ast.parse((OLD / 'm423_trials.py').read_text(encoding='utf-8'))):
        raise RuntimeError('Original language trial AST drift')
    assert g.index('verify_sources(plan)') < g.index('import pynq') < g.index('engine.load()') < g.index("patch(tokenizers,'Tokenizer',original_tokenizer)")
    # The old production-threshold field is descriptive only; no new CMA floor.
    assert "result['diagnostic_admitted']=True" in g and "result['additional_cma_requests_allowed']=False" in g
    texts = dict(m432_gate=g, m432_trials=t, m432_request_visual=(HERE / 'm432_request_visual.py').read_text(encoding='utf-8'))
    PKG.mkdir(parents=True, exist_ok=False)
    excluded = {'PLAN.json', 'SHA256SUMS', 'PACKAGE_MANIFEST.json', 'm428_gate.py', 'm428_trials.py', 'm428_export.py', 'm428_assemble.py', 'run_m428.sh'}
    for row in json.loads((LANG / 'PACKAGE_MANIFEST.json').read_bytes())['files']:
        if row['path'] not in excluded:
            atomic(PKG / row['path'], (LANG / row['path']).read_bytes(), immutable=True)
    for name, text in texts.items():
        ast.parse(text, feature_version=(3, 10)); atomic(PKG / (name + '.py'), text.encode('utf-8'), immutable=True)
    atomic(PKG / 'm431_borrowed_visual.py', (HERE / 'm431_borrowed_visual.py').read_bytes(), immutable=True)
    export = (LANG / 'm428_export.py').read_text(encoding='utf-8').replace('M428', 'M432').replace('m428_saved_feature_language_01', 'm432_late11_integrated_video_01').replace('saved-feature-fixed159-language-quality', 'integrated-fixed159-visual-language-quality')
    atomic(PKG / 'm432_export.py', export.encode('utf-8'), immutable=True)
    entry = '''"""Frozen release bootstrap before any third-party import; retain -I isolation."""
import hashlib,json,runpy,sys
from pathlib import Path
assert sys.flags.isolated
here=Path(__file__).resolve().parent
reuse=Path('/home/ubuntu/m368_staged_video_candidate_03')
if hashlib.sha256((reuse/'PACKAGE_MANIFEST.json').read_bytes()).hexdigest()!='f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66':raise RuntimeError('Reused bootstrap manifest differs')
for row in json.loads((reuse/'PACKAGE_MANIFEST.json').read_bytes())['files']:
    p=reuse/row['path']
    if p.is_symlink() or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Bootstrap payload differs')
sys.path[:0]=[str(here),str(reuse)]
from frozen_video_identity import module_paths
sys.path[:0]=[str(p) for p in module_paths()]
sys.argv=[str(here/'m432_gate.py')]+sys.argv[1:]
runpy.run_path(str(here/'m432_gate.py'),run_name='__main__')
'''
    atomic(PKG / 'm432_entry.py', entry.encode('utf-8'), immutable=True)
    runner = (LANG / 'run_m428.sh').read_text(encoding='utf-8').replace('m428', 'm432').replace('M428', 'M432').replace('m432_saved_feature_language_01', 'm432_late11_integrated_video_01').replace('M432_ENABLE_SAVED_FEATURES', 'M432_ENABLE_INTEGRATED_VIDEO')
    runner = once(runner, '"$task_python" -B "$task_dir/m432_gate.py"', '"$task_python" -I -B "$task_dir/m432_entry.py"')
    atomic(PKG / 'run_m432.sh', runner.encode('utf-8'), immutable=True)
    atomic(PKG / 'PLAN.json', encoded(plan), immutable=True)
    atomic(PKG / 'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'), immutable=True)
    files = sorted(PKG.iterdir())
    manifest = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files), files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(manifest), immutable=True)
    record = dict(status='M432_INTEGRATED_NUMERICAL_PREPARATION_SUPPORT_PENDING', prerequisites=prior, manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                  file_count=manifest['file_count'], total_bytes=manifest['total_bytes'], language_trial_AST_unchanged_except_names=True,
                  actual_visual_forwards=2, actual_language_prefills=2, visual_transactions=286, expected_language_logical_calls_each=778,
                  language_physical_calls_each='781 if the accepted three retries remain exact; eight LM head included',
                  original_seven_DMA_bytes=33484832, extra_DMA=0, planned_total_physical_calls=1849,
                  fixed_CMA_floor=None, ordinary_MemAvailable_reserve_bytes=64 << 20,
                  original_owner_cleanup_and_head_observer_preserved=True, isolated_release_bootstrap=True,
                  board_run=False, numerical_pass=False, performance_pass=False, temperature_measurement_enabled=False,
                  next_step='Execute the actual isolated provider component, prerequisite negatives, recursive dependency closure and exporter/collector/control PASS/FAIL checks before any upload or model run.')
    out = BASE / 'runs/M432-integrated-preparation-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m432_integrated_preparation', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=record['manifest_sha256']),
         f'## M432 后11层完整请求数值入口准备（2026-10-07）\n\nSHA {sha(out)}，manifest {record["manifest_sha256"]}；两个固定请求，A原视觉/B后11层PL视觉各接相同原语言。七DMA33484832B复用且封锁新增；286视觉PL/22暂存及24边界、两份各778语言逻辑/预期781物理含原3重试与8LM head，合计含minimal1849物理。原owner/语言数学/退出保留，-I显式冻结runtime_site，无固定CMA floor，不测温。仅准备、组件/递归依赖/实际收集控制待验证，未上传或数值/完整请求性能/生产晋级。')
    print('M432_PREPARATION_SYNC', sha(out), record['manifest_sha256'])


if __name__ == '__main__':
    main()
