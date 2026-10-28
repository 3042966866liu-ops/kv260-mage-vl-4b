import sys,runpy
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import common_recovery
if sys.argv[1]=='smoke':
    cls=common_recovery.engine_class();print('PASS_ISOLATED_RECOVERY_IMPORT',cls.__module__,flush=True)
else:
    assert sys.argv[1]=='capture';runpy.run_path(str(HERE/'capture_teacher.py'),run_name='__main__')
