"""Versioned recovery experiment, separate from every deployment artifact."""
import sys,json,hashlib,time,copy
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs'
PREFIX='M524-demo-layer-distillation-128'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def relative(p):return Path(p).relative_to(ROOT).as_posix()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
def engine_class():
    directory=ROOT/'experiments/fixed_demo_prune_20261025';sys.path.insert(0,str(directory))
    import demo_common,runtime_demo
    assert Path(runtime_demo.__file__).resolve()==directory/'runtime_demo.py'
    return runtime_demo.DemoExperiment
