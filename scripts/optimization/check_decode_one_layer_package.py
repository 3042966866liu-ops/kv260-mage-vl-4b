"""Offline Linux closure for both exact runtime modes, without constructing PYNQ."""
import importlib.util
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b'
is_ab='--ab' in sys.argv[2:]
package=base/('optimization_v1/candidates/OP01-decode-one-ab-01' if is_ab else 'optimization_v1/candidates/OP01-decode-one-layer-01')
mode=sys.argv[1]
if mode not in ('stable','candidate'):raise ValueError('mode')
sys.path[:0]=[str(package),str(base/'m242_m241_fixed_text_board_candidate'),
             str(base/'m175_m120_fixed_text_candidate/runtime'),str(base/'m181_m120_video_board_candidate')]
import board_decode_one_layer
from op01_support import verify_package
verify_package(package,'4468af81c47d58352153ffccf5158192c4eb6e8012b0202cf07930839e3edbff' if is_ab else '4e7226a240b8daca0c29b529910467e30f13a378bbe08a471b61d67ceaeeb5a3')
spec=importlib.util.spec_from_file_location('board_runtime',package/(mode+'_base.py'))
module=importlib.util.module_from_spec(spec);sys.modules['board_runtime']=module;spec.loader.exec_module(module)
from m238_prefill_runtime import M238PrefillRuntime
from m241_video_language_runtime import M241VideoLanguageModel
from decode_one_runtime_adapter import runtime_class
from decode_one_layer_probe import bind_layer_zero
from decode_checkpoint import load_checkpoint
if is_ab:
    from decode_diagnostic import DecodeDiagnostic
    from decode_io_trace import DecodeIOTrace,process_snapshot
    from lifecycle_reads import prepare_reads
    from transfer_trace import instrument
    from summarize_decode_trace import summarize
    instrument(module.copy_window_to_buffer,DecodeIOTrace())
    assert 'read_bytes' in process_snapshot()
if mode=='candidate':runtime_class(M238PrefillRuntime,module)
bind_layer_zero(M241VideoLanguageModel.__new__(M241VideoLanguageModel))
subprocess.run(['bash','-n',str(package/'run_layer.sh')],check=True)
assert not list(package.rglob('*.pyc'))
print('PASS_PACKAGE_LINUX_IMPORT_ONLY '+mode+(' full-decode' if is_ab else ' layer'))
