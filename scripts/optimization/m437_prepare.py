"""Versioned performance packet/host controls from checked immutable predecessors."""
import ast
import json
from pathlib import Path
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once

OLD = BASE/'candidates/M433-late11-complete-request-warm-01'
PKG = BASE/'candidates/M437-late11-natural-IO-performance-01'
REMOTE = '/home/ubuntu/m437_natural_IO_candidate_01'
EVIDENCE = '/home/ubuntu/m437_natural_IO_result_01'


def main():
    if PKG.exists():
        raise RuntimeError('Immutable packet exists')
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior = {}
    for k in ('latest_m437_natural_IO_protocol', 'latest_m436_IO_board', 'latest_m436_IO_interpretation',
              'latest_m433_performance_support', 'latest_m433_timed_provider_component'):
        e = board[k]
        assert sha(ROOT/e['result']) == e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        prior[k] = e
    protocol = (ROOT/prior['latest_m437_natural_IO_protocol']['result']).with_name('PROTOCOL.json')
    assert sha(protocol) == prior['latest_m437_natural_IO_protocol']['protocol_sha256']
    m = json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']:
        assert sha(OLD/row['path']) == row['sha256'] and (OLD/row['path']).stat().st_size == row['bytes']
    gate = (OLD/'m433_gate.py').read_text(encoding='utf-8')
    for a, b in [('M433', 'M437'), ('m433_late11_warm_request_01', 'm437_natural_IO_result_01'),
                 ('controlled-warm-complete-request-performance', 'natural-IO-complete-request-performance'),
                 ('from m433_trials import run', 'from m437_trials import run'),
                 ('from m433_export import emit_saved', 'from m437_export import emit_saved'),
                 ('PASS_M437_CONTROLLED_WARM_MEASUREMENTS_COLLECTED', 'PASS_M437_NATURAL_IO_MEASUREMENTS_COLLECTED')]:
        gate = gate.replace(a, b)
    gate = gate.replace('> 3000', '> 3600')
    gate = once(gate, "result['next_step'] = 'Close exactly the saved fixed warm experiment; no extra requests, fitted threshold or production promotion'",
                "result['next_step'] = 'Close exactly the saved natural-I/O experiment; no extra requests, exclusions, IO adjustment or production promotion'")
    gate = once(gate, "experiment_scope='Original complete runtime objects retained; two real original/late11 candidate visual calls borrowing existing seven buffers, then unchanged language/head; no extra DMA/PS slot; no performance or expansion'",
                "experiment_scope='Four fixed ABBA preconditioning plus eight ABBABAAB formal streams with natural I/O; original seven DMA resident, no additional DMA/slot or other optimization'")
    trials = (OLD/'m433_trials.py').read_text(encoding='utf-8').replace('M433', 'M437')
    trials = trials.replace('from m425_warm import ORDER,WarmSequence', 'from m437_sequence import ORDER,NaturalSequence')
    trials = trials.replace('sequence=WarmSequence(', 'sequence=NaturalSequence(')
    trials = trials.replace('check_call_contract,validate_stream', 'check_call_contract')
    trials = once(trials, "semantic=validate_stream(events,after_cache,'0x4D333537')", "semantic=validate_request_stream(events,after_cache,'0x4D333537')")
    observed = BASE/'candidates/M436-weight-read-observation-03/m435_trials.py'
    source = observed.read_text(encoding='utf-8')
    funcs = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
             and n.name in ('validate_candidate_cache_contract', 'validate_candidate_stream')]
    validators = '\n\n'.join(ast.get_source_segment(source, n) for n in funcs)
    assert len(funcs) == 2
    validators = validators.replace('validate_candidate_stream', 'validate_request_stream')
    trials = once(trials, '\ndef io_snapshot():', '\n'+validators+'\n\n\ndef io_snapshot():')
    trial_plan = json.loads((OLD/'PLAN.json').read_bytes())
    trial_plan.update(prerequisites=prior, request_boundary='Four fixed ABBA preconditioning then exactly eight ABBABAAB formal streams; natural storage I/O included.')
    perf = json.loads((OLD/'PERFORMANCE_PLAN.json').read_bytes())
    perf['protocol_sha256'] = sha(protocol)
    texts = dict(m437_gate_py=gate)  # filled below without relying on version-wide import rewrites
    texts = {'m437_gate.py': gate, 'm437_trials.py': trials,
             'm437_sequence.py': (HERE/'m437_sequence.py').read_text(encoding='utf-8'),
             'm437_entry.py': (OLD/'m433_entry.py').read_text(encoding='utf-8').replace('m433_gate.py', 'm437_gate.py'),
             'm437_export.py': (OLD/'m433_export.py').read_text(encoding='utf-8').replace('M433', 'M437').replace('m433_late11_warm_request_01', 'm437_natural_IO_result_01').replace('controlled-warm-complete-request-performance', 'natural-IO-complete-request-performance'),
             'run_m437.sh': (OLD/'run_m433.sh').read_text(encoding='utf-8').replace('m433_entry.py', 'm437_entry.py').replace('m433_export.py', 'm437_export.py').replace('M433', 'M437').replace('m433_late11_warm_request_01', 'm437_natural_IO_result_01'),
             'm437_assemble.py': (OLD/'m433_assemble.py').read_text(encoding='utf-8').replace('/home/ubuntu/m432_late11_integrated_candidate_02', '/home/ubuntu/m433_late11_warm_candidate_01').replace('37579ee6572d076a547842ba868c04a3797dd2a0375724c2a6fce333a9b9a0ee', sha(OLD/'PACKAGE_MANIFEST.json')).replace('M433_ASSEMBLY_PASS', 'M437_ASSEMBLY_PASS'),
             'WARM_PROTOCOL.json': protocol.read_text(encoding='utf-8'), 'PLAN.json': encoded(trial_plan).decode('utf-8'),
             'PERFORMANCE_PLAN.json': encoded(perf).decode('utf-8')}
    excluded = {'m433_gate.py', 'm433_trials.py', 'm433_entry.py', 'm433_export.py', 'm433_assemble.py',
                'run_m433.sh', 'm425_warm.py', 'SHA256SUMS', 'DEPENDENCY_CLOSURE.json', *texts}
    PKG.mkdir(parents=True)
    for row in m['files']:
        if row['path'] not in excluded:
            atomic(PKG/row['path'], (OLD/row['path']).read_bytes(), immutable=True)
    for n, text in texts.items():
        if n.endswith('.py'):
            ast.parse(text, feature_version=(3, 10))
        atomic(PKG/n, text.encode('utf-8'), immutable=True)
    closure = json.loads((OLD/'DEPENDENCY_CLOSURE.json').read_bytes())
    closure['files'] = {n:d for n,d in closure['files'].items() if n+'.py' not in excluded}
    closure['files'].update({p.stem:sha(p) for p in PKG.glob('*.py')})
    closure['root_modules'] = ['m437_gate', 'm437_entry', 'm437_export', 'm437_assemble']
    # External source closure retains the exact existing frozen package identities.
    module_names=set(closure['files'])
    missing=[]
    for p in PKG.glob('*.py'):
        deps=[a.name.split('.')[0] for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))) if isinstance(n,ast.Import) for a in n.names]
        deps += [(n.module or '').split('.')[0] for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))) if isinstance(n,ast.ImportFrom)]
        missing += [[p.stem,d] for d in deps if len(d)>1 and d[0]=='m' and d[1].isdigit() and d not in module_names]
    assert not missing, missing
    closure.update(missing=missing, recursive_modules=len(module_names))
    atomic(PKG/'DEPENDENCY_CLOSURE.json', encoded(closure), immutable=True)
    atomic(PKG/'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'), immutable=True)
    files=sorted(PKG.iterdir())
    manifest=dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files),
                  files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(PKG/'PACKAGE_MANIFEST.json', encoded(manifest), immutable=True)
    w=(HERE/'m433_workflow.py').read_text(encoding='utf-8')
    w=w.replace('M433','M437').replace('m433','m437')
    w=w.replace('M437-late11-complete-request-warm-01','M437-late11-natural-IO-performance-01').replace('M437-warm-performance-board-01','M437-natural-IO-board-01')
    w=w.replace('controlled-warm-complete-request-performance','natural-IO-complete-request-performance')
    w=w.replace('PASS_M437_CONTROLLED_WARM_MEASUREMENTS_COLLECTED','PASS_M437_NATURAL_IO_MEASUREMENTS_COLLECTED')
    w=w.replace('warm_conditions_established','preconditioning_completed').replace('warm_protocol_sha256','natural_IO_protocol_sha256')
    w=w.replace('from m425_warm import ORDER,WarmSequence','from m437_sequence import ORDER,NaturalSequence').replace('sequence=WarmSequence(','sequence=NaturalSequence(')
    w=w.replace('latest_m437_warm_board','latest_m437_natural_IO_board')
    w=w.replace('M432-late11-integrated-video-02/PACKAGE_MANIFEST.json','M433-late11-complete-request-warm-01/PACKAGE_MANIFEST.json')
    w=w.replace("M437-performance-transfer-01", "M437-natural-IO-transfer-01").replace('latest_m437_performance_transfer','latest_m437_natural_IO_transfer')
    atomic(HERE/'m437_workflow.py', w.encode('utf-8'), immutable=True)
    # Control starts from a known collection-on-failure implementation, with independent roots.
    control=(HERE/'m436_control06.ps1').read_text(encoding='utf-8')
    control=control.replace('M435','M437').replace('m435','m437').replace('M436','M437').replace('m436','m437')
    control=control.replace('M437-weight-read-observation-03','M437-late11-natural-IO-performance-01')
    control=control.replace('/home/ubuntu/m437_weight_read_candidate_01', REMOTE)
    control=control.replace('tmp/m43702/board','tmp/m43701/board').replace('m437_workflow02.py','m437_workflow.py')
    control=control.replace('runs/M437-IO-observation-board-02','runs/M437-natural-IO-board-01')
    start=control.index("foreach ($key in @(")
    end=control.index('foreach ($row in $manifest.files)', start)
    guard="""foreach ($key in @('latest_m437_natural_IO_protocol','latest_m437_preparation','latest_m437_support','latest_m433_performance_transfer')) { VerifyEvidence $key }
$supported=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m437_support.result) | ConvertFrom-Json
if ($supported.manifest_sha256 -ne $digest -or $supported.candidate_remote -ne $remote) { throw 'Supported identity differs' }
foreach ($p in $supported.host_sources.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Supported source changed' }
}
"""
    control=control[:start]+guard+control[end:]
    control=control.replace('M437-weight-read-observation-02/PACKAGE_MANIFEST.json','M433-late11-complete-request-warm-01/PACKAGE_MANIFEST.json')
    control=control.replace("VerifyEvidence 'latest_m437_route_transfer'", "VerifyEvidence 'latest_m437_natural_IO_transfer'")
    control=control.replace('$board.latest_m437_route_transfer.manifest_sha256','$board.latest_m437_natural_IO_transfer.manifest_sha256')
    control=control.replace('-TimeoutSeconds 2100','-TimeoutSeconds 5100')
    atomic(HERE/'m437_control.ps1',control.encode('utf-8'),immutable=True)
    r=dict(status='PREPARED_M437_NATURAL_IO_PACKET_SUPPORT_PENDING',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
           prerequisites=prior,file_count=manifest['file_count'],total_bytes=manifest['total_bytes'],
           candidate_remote=REMOTE,evidence_remote=EVIDENCE,maximum_requests=12,extra_DMA=0,
           board_run=False,performance_pass=False,temperature_measurement_enabled=False,
           old_cache_population_replaced_with_validated_upper_bounds=True,
           heavy_IO_observer_included=False,expected_physical=11089,missing=missing)
    out=BASE/'runs/M437-natural-IO-preparation-01/RESULT.json'
    atomic(out,encoded(r),immutable=True)
    sync('latest_m437_preparation',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),
         f'## M437 自然I/O完整请求包准备（2026-10-07）\n\nBuild0x4D333537，SHA {sha(out)}，manifest {r["manifest_sha256"]}，{manifest["file_count"]}文件/{manifest["total_bytes"]}B。固定4＋8、11089物理，实际新sequence取消I/O删样本规则，stream语义改用已上板缓存上限；原全特征/logits/KV/语言物理核对、七DMA/0新增、provider/轻量内存policy和稳定恢复保持。独立候选/结果根；未上传、未执行或性能，下一步实际stream及统计/export/collector/assembly/transfer/control支持。')
    print('M437_PREPARED',sha(out),r['manifest_sha256'],manifest['file_count'],manifest['total_bytes'])


if __name__=='__main__':main()
