import sys,json
from pathlib import Path
if not sys.flags.isolated:raise RuntimeError('Isolated interpreter required')
here=Path(__file__).resolve().parent
plan=json.loads((here/'PLAN.json').read_bytes())
sys.path[:0]=[str(here),plan['component_package']]+[x['directory'] for x in plan['reused_packages']]
from frozen_video_identity import RELEASE,module_paths
if RELEASE!=Path(sys.argv[1]) or str(RELEASE)!=plan['release']:raise RuntimeError('Frozen release root differs')
# -I deliberately ignores PYTHONPATH. Bootstrap only frozen installed paths.
paths=[str(p) for p in module_paths()]
if paths[0]!=str(RELEASE/'runtime_site'):raise RuntimeError('Frozen runtime path differs')
sys.path[:0]=paths
import torch,numpy as np
torch_path=Path(torch.__file__).resolve()
torch_path.relative_to((RELEASE/'runtime_site').resolve())
torch.set_num_threads(1)
print('M429_BOOTSTRAP='+json.dumps(dict(isolated=True,release=str(RELEASE),module_paths=paths,torch_path=str(torch_path),torch_version=torch.__version__,numpy_path=str(Path(np.__file__).resolve()),numpy_version=np.__version__,threads=torch.get_num_threads())),flush=True)
from test_m429_range import component
value=component(RELEASE)
if any(x=='pynq' or x.startswith('pynq.') for x in sys.modules):raise RuntimeError('Unexpected PYNQ import')
print('M429_COMPONENT='+json.dumps(value),flush=True)
