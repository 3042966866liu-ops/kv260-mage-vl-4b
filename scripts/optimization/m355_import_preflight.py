"""Exact package imports, Linux-only standard library adapter on Windows only."""
import sys
import types
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
if sys.platform=='win32':
    # fcntl is imported only; no fake locks, MMIO or PYNQ execution is performed.
    sys.modules['fcntl']=types.ModuleType('fcntl')
import m355_device_phase_probe
import m355_export_result
print('M355_PACKAGE_IMPORT_PREFLIGHT_PASS no_main_no_pynq')
