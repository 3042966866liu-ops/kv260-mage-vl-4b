import sys,runpy
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
from demo_common import PREVIOUS
import runtime
assert Path(runtime.__file__).resolve()==(PREVIOUS/'runtime.py').resolve()
from runtime_demo import DemoExperiment
if sys.argv[1]=='smoke':print('PASS_ISOLATED_FIXED_DEMO_IMPORT',runtime.__file__,flush=True)
else:
    assert sys.argv[1]=='search';runpy.run_path(str(H/'search.py'),run_name='__main__')
