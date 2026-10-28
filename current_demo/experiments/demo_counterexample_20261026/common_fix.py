"""M542 finite full-batch counterexample replay after M541 final-checkpoint failure."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'experiments/demo_adapt_20261026'))
from common_adapt import read,sha,rel,digest,save,npz,setup_engine,forward,decision,classify,core,OPT,RUNS,HEAD,BODY,PARENT
import numpy as np,json,time,hashlib
PROTO=RUNS/'M542-demo-counterexample-protocol-01/RESULT.json'
FRAMEPROTO=RUNS/'M542-demo-counterexample-frames-protocol-01/RESULT.json'
FRAMES=RUNS/'M542-demo-counterexample-new-frames-01'
CAP=RUNS/'M541-demo-adaptation-capture-03'
FIT=RUNS/'M542-demo-counterexample-fit-01'
RELOAD=RUNS/'M542-demo-counterexample-reload-01'
def verify(file=PROTO):
    p=read(file)
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    return p
