"""Independent exact-math fixture child; no model constructor or FPGA."""
import json,sys
from pathlib import Path
from m409_torch_component import component
from test_m409_ftz_reference import actual_host
import torch
root=Path(sys.argv[1]);host,initial=actual_host(root)
print('M414_COMPONENT='+json.dumps(component(torch,root,host,initial)),flush=True)
