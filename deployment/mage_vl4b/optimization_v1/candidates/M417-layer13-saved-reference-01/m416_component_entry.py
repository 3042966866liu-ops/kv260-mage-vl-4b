"""Isolated real Torch primitive/wrapper fixtures; no model or PYNQ."""
import json,sys
from pathlib import Path
from m408_component04 import component
from m416_target_component import from_sources
from frozen_video_identity import module_paths
sys.path[:0]=[str(p) for p in module_paths() if p.name!='runtime_site']
import torch
import contract_runtime
from m207_ps_vision_runtime import M207FP32GemmW4Linear
answer=dict(component=component(torch,contract_runtime.quantize_t32,M207FP32GemmW4Linear),
            target_component=from_sources(torch,Path(sys.argv[1])))
print('M414_COMPONENT='+json.dumps(answer),flush=True)
