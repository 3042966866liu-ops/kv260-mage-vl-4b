"""Read-only identity probe, no model/overlay allocation."""
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
import textwrap

if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=sys.argv[1]:raise RuntimeError('Probe SHA differs')
root=Path('/home/ubuntu/tellme_m120_m89x2_20260901')
config=json.loads((root/'optimization_v1/OP01-SYS-04/sys_config.json').read_text())
sys.path[0:0]=[str(root/p) for p in config['python_path']]
for name in ('numpy','cv2','torch','tokenizers','transformers','m238_prefill_runtime',
             'm241_video_language_runtime','m222_vectorized_w4_runtime'):
    importlib.import_module(name)
import board_runtime
source=textwrap.dedent(inspect.getsource(board_runtime.copy_window_to_buffer)).strip().replace('\r\n','\n')
instrument_created=False
if len(sys.argv)==3:
    target=Path('/home/ubuntu/transfer_trace_verified.py')
    if hashlib.sha256(target.read_bytes()).hexdigest()!=sys.argv[2]:raise RuntimeError('Instrument SHA differs')
    spec=importlib.util.spec_from_file_location('transfer_trace_verified',target)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.instrument(board_runtime.copy_window_to_buffer,None)
    instrument_created=True
print('TRANSFER_IDENTITY_JSON_BEGIN')
print(json.dumps(dict(python=sys.version,module=board_runtime.__file__,instrument_created=instrument_created,
    file_sha256=hashlib.sha256(Path(board_runtime.__file__).read_bytes()).hexdigest(),
    source_sha256=hashlib.sha256(source.encode()).hexdigest(),source=source)))
print('TRANSFER_IDENTITY_JSON_END')
