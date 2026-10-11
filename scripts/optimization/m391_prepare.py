"""Freeze CPU-only real-input component only after M390 saved closure."""
import ast
import json
import shutil
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync

PKG=BASE/'candidates/M391-silu-real-input-component-01'
def main():
    if PKG.exists():raise RuntimeError('Immutable preparation exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m390_capture_closure'];assert prior['status']=='PASS_ACTUAL_FIXED159_GATE_UP_CAPTURE_ONLY'
    for entry in (prior,board['latest_m390_capture_board'],board['latest_m389_silu_workspace_preparation']):
        assert sha(ROOT/entry['result'])==entry['sha256']
        assert all(entry['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    capture=json.loads((ROOT/board['latest_m390_capture_board']['result']).read_text(encoding='utf-8'))
    sources=json.loads((BASE/'candidates/M389-silu-workspace-component-01/SOURCE_IDENTITY.json').read_text(encoding='utf-8'))['sources']
    source=ROOT/sources['video_language_runtime']['path'];assert sha(source)==sources['video_language_runtime']['sha256']
    tree=ast.parse(source.read_text(encoding='utf-8'));node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='silu')
    original='import numpy as np\n\n'+ast.get_source_segment(source.read_text(encoding='utf-8'),node)+'\n'
    assert 'return (x / (1.0 + np.exp(-x))).astype(np.float32)' in original
    PKG.mkdir(parents=True)
    for n in ['m391_silu_gate.py','m391_export.py','run_m391_silu.sh']:shutil.copyfile(HERE/n,PKG/n)
    old=BASE/'candidates/M389-silu-workspace-component-01/m389_silu_workspace.py'
    assert sha(old)==sha(HERE/'m389_silu_workspace.py');shutil.copyfile(old,PKG/old.name)
    atomic(PKG/'original_silu.py',original.encode('utf-8'))
    atomic(PKG/'INPUT_IDENTITY.json',encoded(dict(capture_raw_sha256=board['latest_m390_capture_board']['sha256'],capture_closure=prior,
                                               fixtures=capture['actual_gate_up_fixtures'],original_source=sources['video_language_runtime'])))
    for p in PKG.glob('*.py'):
        t=ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
        imports={a.name.split('.')[0] for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names}
        assert not imports.intersection({'pynq','torch','video_server','board_runtime'})
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M391-real-input-CPU-component-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    value=dict(status='PASS_OFFLINE_M391_CPU_COMPONENT_PREPARATION',prior_capture=prior,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               original_source=sources['video_language_runtime'],file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
               tests_pending=True,board_run=False,model_integrated=False,performance_pass=False,
               component_policy='Exact real-input FP32 bits; four warmup calls each; six rounds of ABBA+BAAB, six calls per batch; all group gains positive and exceed largest within-group range, maxB<minA; no stable benefit closes candidate',
               timed_scope='A original cast+allocation and deletion; B lease, five ufunc out and release; one workspace creation/close recorded separately; file loading and SHA outside timers')
    out=BASE/'runs/M391-cpu-component-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m391_silu_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),
         f'## M391 真实gate/up CPU组件准备（2026-10-04）\n\n捕获闭合后默认关闭包，SHA {d}，冻结原silu源码函数与M389工作缓冲。板端原数组完整SHA/身份、真实尺寸、前后逐位和输入不变；六组ABBA＋BAAB/每批6次、相同预热，建立/关闭另计。60秒有界CPU-only，无Overlay/模型/FPGA；仅组件收益，缺乏稳定收益在此关闭。尚需实际入口和回收负例、控制支持；未上板。')
    print(json.dumps(value|{'result_sha256':d}))

if __name__=='__main__':main()
