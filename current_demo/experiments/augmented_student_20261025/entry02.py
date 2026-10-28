import sys,runpy
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import common_joint
common_joint.engine_class()
if sys.argv[1]=='smoke':import joint_runtime02,train_joint02;print('PASS_ISOLATED_JOINT_STUDENT_IMPORT',flush=True)
else:
    assert sys.argv[1]=='train';runpy.run_path(str(HERE/'train_joint02.py'),run_name='__main__')
