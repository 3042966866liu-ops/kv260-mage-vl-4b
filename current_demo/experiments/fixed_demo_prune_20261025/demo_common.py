"""Fixed, predeclared two-video demo: unforced model decision field."""
import sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];PREVIOUS=ROOT/'experiments/whole_layer_20261025'
sys.dont_write_bytecode=True;sys.path.insert(0,str(PREVIOUS))
from common import read,sha,save,array,rel,OPT,R,copy,time,np,json
H=Path(__file__).resolve().parent
PREFIX='M523-fixed-demo-pruning-128';PREP=R/(PREFIX+'-protocol-01');OUT=R/(PREFIX+'-search-01')
OLDSEARCH=R/'M523-whole-layer-joint-128-search-01';SEMANTIC=R/'M523-whole-layer-semantic-128-search-01';OLDQUALITY=R/'M523-whole-layer-joint-128-quality-01'
ALIASES={'yes':'Yes','true':'Yes','no':'No','false':'No'}
def decision(text):return ALIASES.get(text.strip().casefold().rstrip('.,!?;:'),'Invalid')
def mask(v,l=None):
    import hashlib
    return hashlib.sha256(json.dumps([v,l],separators=(',',':')).encode()).hexdigest()[:20]
def verify():
    p=read(PREP/'RESULT.json')
    for path,h in p['frozen'].items():assert sha(ROOT/path)==h,path
    return p
