"""Resume collector checks from saved successful component bytes, never rerun."""
import ast,json,hashlib,subprocess
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    source=HERE/'m425_support.py'
    tree=ast.parse(source.read_text(encoding='utf-8'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    # Keep the actual collector and later checks; replace only setup/run prefix.
    start=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='lines' for t in n.targets))
    prefix=ast.parse("""stage=ROOT/'tmp/m42501/component_stage'
out=ROOT/'tmp/m42501/component'
raw=(out/'stdout.bin').read_bytes()
assert b'M425_COMPONENT=' in raw and b'M425_SYNTHETIC_WARM_COMPONENT_PASS' in raw and b'M425_NO_TEMPERATURE_READER_COMPONENT_PASS' in raw
for name in ('m425_trials.py','m425_timed_visual.py','m425_warm.py','m425_environment.py','m423_trials.py','m369_light_policy.py','VISUAL_EXPECTED.json','WARM_PROTOCOL.json','PERFORMANCE_PLAN.json'):
    assert sha(stage/name)==sha(w.PKG/name)
cp=SimpleNamespace(stdout=raw)
language=json.loads((BASE/'runs/M421-saved-language-board-01/BOARD_RESULT.json').read_bytes())
""").body
    fn.body=prefix+fn.body[start:]
    # Fixture prefill has no real release; collector fixture takes the saved owner
    # evidence unchanged from M423 instead of overwriting it with an empty list.
    i=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='r' and n.value.func.attr=='update' and len(n.value.args)==1 and isinstance(n.value.args[0],ast.Name) and n.value.args[0].id=='fixture')
    fn.body[i+1:i+1]=ast.parse("r['released_buffers']=copy.deepcopy(original['released_buffers'])").body
    tree.body=[n for n in tree.body if not isinstance(n,ast.If)]
    namespace={'__name__':'m425_collector_resume','SimpleNamespace':__import__('types').SimpleNamespace}
    p=BASE/'runs/M425-offline-collector-repair-01/RESULT.json'
    v=dict(status='OFFLINE_COLLECTOR_FIXTURE_MERGE_REJECTED',error='Seven DMA ownership differs: explicitly fake trials released_buffers=[] overwrote saved actual successful ownership in the synthetic collector fixture.',component_stdout_sha256=sha(outpath:=ROOT/'tmp/m42501/component/stdout.bin'),component_stderr_sha256=sha(ROOT/'tmp/m42501/component/stderr.bin'),repair='Restore saved M423 release evidence only in collector fixture. Reuse successful actual component bytes without repeating component or any hardware.',board_run=False)
    atomic(p,encoded(v),immutable=True)
    exec(compile(ast.fix_missing_locations(tree),str(source),'exec'),namespace)
    namespace['main']()
if __name__=='__main__':main()
