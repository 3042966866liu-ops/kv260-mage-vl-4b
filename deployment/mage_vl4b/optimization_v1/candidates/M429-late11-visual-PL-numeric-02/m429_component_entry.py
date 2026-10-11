import sys,json
from pathlib import Path
assert sys.flags.isolated
here=Path(__file__).resolve().parent
plan=json.loads((here/'PLAN.json').read_bytes())
sys.path[:0]=[str(here)]+[x['directory'] for x in plan['reused_packages']]
import torch
torch.set_num_threads(1)
from test_m429_range import component
value=component(Path(sys.argv[1]))
assert not any(x=='pynq' or x.startswith('pynq.') for x in sys.modules)
print('M429_COMPONENT='+json.dumps(value),flush=True)
