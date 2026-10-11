import sys,json,contextlib,io
from pathlib import Path
if not sys.flags.isolated:raise RuntimeError('Isolated CPU child required')
here=Path(__file__).resolve().parent
plan=json.loads((here/'PLAN.json').read_bytes())
sys.path[:0]=[str(here),plan['component_package']]+[x['directory'] for x in plan['reused_packages']]
from frozen_video_identity import RELEASE,module_paths
if RELEASE!=Path(sys.argv[1]) or str(RELEASE)!=plan['release']:raise RuntimeError('Frozen release differs')
paths=[str(x) for x in module_paths()]
if paths[0]!=str(RELEASE/'runtime_site'):raise RuntimeError('Frozen runtime bootstrap differs')
sys.path[:0]=paths
import torch,numpy as np
Path(torch.__file__).resolve().relative_to((RELEASE/'runtime_site').resolve())
Path(np.__file__).resolve().relative_to((RELEASE/'runtime_site').resolve())
torch.set_num_threads(1)
print('M431_BOOTSTRAP='+json.dumps(dict(isolated=True,release=str(RELEASE),module_paths=paths,torch_path=str(Path(torch.__file__).resolve()),torch_version=torch.__version__,numpy_path=str(Path(np.__file__).resolve()),numpy_version=np.__version__,threads=torch.get_num_threads())),flush=True)
from test_m431_borrowed_visual import main as negative
text=io.StringIO()
with contextlib.redirect_stdout(text):negative()
lines=[x.split('=',1)[1] for x in text.getvalue().splitlines() if x.startswith('M431_COMPONENT=')]
if len(lines)!=1:raise RuntimeError('Unique negative component required')
from m431_window_component import component
window=component(plan['geometry_references'],here.parent)
if any(x=='pynq' or x.startswith('pynq.') for x in sys.modules):raise RuntimeError('Unexpected PYNQ import')
print('M431_COMPONENT='+json.dumps(dict(window=window,negative=json.loads(lines[0]))),flush=True)
