"""Paired-augmentation full student training, separate immutable evidence."""
import sys,json,hashlib,time,copy
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs';PREFIX='M525-joint-augmented-student-128'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(8<<20),b''):h.update(chunk)
    return h.hexdigest()
def relative(p):return Path(p).relative_to(ROOT).as_posix()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
def engine_class():
    old=ROOT/'experiments/demo_recovery_20261025';sys.path.insert(0,str(old))
    from common_recovery import engine_class as prior
    return prior()
