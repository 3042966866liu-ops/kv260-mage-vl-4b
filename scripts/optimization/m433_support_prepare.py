"""Prepare actual stream/export/collector support, retaining old frozen harnesses."""
from m351_workflow import HERE, atomic
from m427_prepare import once


def main():
    trial = (HERE / 'test_m425_trials.py').read_text(encoding='utf-8')
    trial = trial.replace('import m425_trials as trials', 'import m433_trials as trials').replace('from m423_saved_features import tensor', 'from m428_saved_features import tensor')
    trial = trial.replace('from m423_trials import COUNTERS', 'from m432_trials import COUNTERS')
    trial = once(trial, "result['transactions']=[dict(method='head-original-execute' if i>=773 else 'fake-language',completed_snapshot=snap) for i in range(781)]", "index=result['fake_variant_index']\n        result['transactions']=copy.deepcopy(fixture['transactions'][index*781:(index+1)*781])")
    trial = once(trial, "language=dict(samples=refs)", "language=dict(samples=refs,transactions=fixture['transactions'])")
    trial = once(trial, "        def __call__(self,index,*args,**kw):\n            if index:", "        def __call__(self,index,*args,**kw):\n            result['fake_variant_index']=index\n            if index:")
    trial = trial.replace('for _ in range(52)', 'for _ in range(286)').replace('for i in (12,13)', 'for i in range(13,24)').replace("result['completed_visual_physical']==312", "result['completed_visual_physical']==1716")
    atomic(HERE / 'test_m433_trials.py', trial.encode('utf-8'), immutable=True)
    source = (HERE / 'm425_support.py').read_text(encoding='utf-8')
    source = source.replace('import m425_workflow as w', 'import m433_workflow as w')
    begin = source.index("    stage=ROOT/'tmp/m42501/component_stage'")
    end = source.index("    cp=subprocess.run(", begin)
    source = source[:begin] + '''    stage=ROOT/'tmp/m43302/component_stage';stage.mkdir(parents=True,exist_ok=False)
    oldstage=ROOT/'tmp/m42501/component_stage'
    for p in oldstage.iterdir():
        if p.is_file() and p.suffix=='.py' and p.name!='entry.py':atomic(stage/p.name,p.read_bytes(),immutable=True)
    for name in ('m433_trials.py','m425_warm.py','m425_environment.py','m432_trials.py','VISUAL_EXPECTED.json','WARM_PROTOCOL.json','PERFORMANCE_PLAN.json','m428_saved_features.py'):
        p=stage/name
        if p.exists():p.unlink()
        atomic(p,(w.PKG/name).read_bytes(),immutable=True)
    atomic(stage/'test_m433_trials.py',(HERE/'test_m433_trials.py').read_bytes(),immutable=True)
    language=json.loads((BASE/'runs/M428-saved-language-board-01/BOARD_RESULT.json').read_bytes())
    for name,value in [('NUMERIC_FIXTURE.json',dict(counts=language['samples'][0]['counts'],transactions=language['transactions'])),('ENVIRONMENT_FIXTURE.json',json.loads((BASE/'runs/M424-environment-board-01/BOARD_RESULT.json').read_bytes()))]:
        atomic(stage/name,encoded(value),immutable=True)
    entry='\\n'.join(['import json,sys','from pathlib import Path','assert sys.flags.isolated',"root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')","stage=root/'tmp/m43302/component_stage'",'sys.path[:0]=[str(stage)]','import torch','torch.set_num_threads(1)','from test_m425_environment import main as environment','from test_m425_warm import main as warm','from test_m433_trials import component as trials','environment();warm()',"print('M433_COMPONENT='+json.dumps(dict(trials=trials(root)),sort_keys=True),flush=True)",''])
    atomic(stage/'entry.py',entry.encode('utf-8'),immutable=True)
''' + source[end:]
    source = source.replace('tmp/m42501/component_stage/entry.py', 'tmp/m43302/component_stage/entry.py').replace("tmp/m42501/component'", "tmp/m43302/component'")
    source = source.replace('M425', 'M433').replace('M423-integrated-video-board-01', 'M432-integrated-video-board-01')
    source = source.replace('fpga_transactions=9685', 'fpga_transactions=11089').replace("('fpga_transactions',9684)", "('fpga_transactions',11088)")
    source = source.replace("r['samples']):", "r['samples']):")
    source = source.replace("    def export(value):", "    def obsolete_manual_export(value):")
    anchor = "    raw=json.dumps(r,separators=(',',':')).encode();assert len(raw)<4<<20;assert w.decode(export(r))[2]==r"
    actual = '''    import contextlib,importlib.util,io,tempfile
    from pathlib import Path
    from unittest.mock import patch
    spec=importlib.util.spec_from_file_location('actual_m433_export',w.PKG/'m433_export.py')
    exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
    export_dir=ROOT/'tmp/m43302/export_fixture';export_dir.mkdir(parents=True,exist_ok=False)
    exporter.OUTPUT=export_dir/'BOARD_RESULT.json'
    def export(value):
        payload=encoded(value);exporter.OUTPUT.write_bytes(payload);out=io.StringIO()
        with patch.object(exporter.os,'geteuid',lambda:0,create=True),patch.object(exporter.time,'sleep',lambda *x:None),contextlib.redirect_stdout(out):exporter.emit_saved()
        return out.getvalue()
    raw=encoded(r);assert len(raw)<4<<20;assert w.decode(export(r))[2]==r
    log=export_dir/'run.log';log.write_text(export(r),encoding='utf-8');notes=[]
    dest=export_dir/'collected/BOARD_RESULT.json'
    with patch.object(w,'OUT',dest),patch.object(w,'sync',lambda *args:notes.append(args)),contextlib.redirect_stdout(io.StringIO()):w.collect(log)
    assert dest.read_bytes()==raw and len(notes)==1 and notes[0][0]=='latest_m433_warm_board'
'''
    source = once(source, anchor, actual.rstrip())
    # Actual exporter reads full root-owned source: only uid and pacing are fixture substitutions.
    source = source.replace("assert g.index(\"if sha256(p)!=perf_plan['integrated_numerical_sha256']\")<g.index('import pynq')", "assert g.index('read_owned(Path(perf_plan')<g.index('import pynq')")
    source = source.replace('m425_gate.py', 'm433_gate.py').replace('m425_control.ps1', 'm433_control.ps1').replace('run_m425.sh', 'run_m433.sh')
    source = source.replace('m425_workflow.py', 'm433_workflow.py').replace('m425_support.py', 'm433_support.py')
    source = source.replace('m425_environment.py', 'm425_environment.py')
    source = source.replace('latest_m425_performance_support', 'latest_m433_performance_support').replace('2026-10-06', '2026-10-07')
    source = source.replace('实际四绑定/原stream AST', '实际后11层provider组件已另存/原stream AST')
    source = source.replace('explicit_synthetic_collector=True', 'explicit_synthetic_collector=True, actual_exporter_and_atomic_collector=True, root_and_pacing_explicit_fake=True')
    atomic(HERE / 'm433_support.py', source.encode('utf-8'), immutable=True)
    print('M433_SUPPORT_SOURCE_PREPARED')


if __name__ == '__main__':
    main()
