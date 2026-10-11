"""Linux import and shell preflight; no board or FPGA operations."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
package = root/'deployment/mage_vl4b/optimization_v1/candidates/OP01-decode-one-real-chain-01'
sys.path.insert(0, str(package))
import decode_one_minimal_board
from decode_one_real_chain import load_real_chain
from op00_stable_probe import verify_self
verify_self(package, 'fa0254f5050f251ed72cb6f417bc0860e6cf1e9eed8b64bde3f32519744ac525')
fixture = load_real_chain(package/'real_gate_up.bin')
subprocess.run(['bash', '-n', str(package/'run_decode_one_minimal_board.sh')], check=True)
assert not list(package.rglob('*.pyc'))
print(json.dumps(dict(status='PASS_LINUX_IMPORT_FIXTURE_ONLY', input_bytes=len(fixture['packet']),
    output_bytes=fixture['output_bytes'], board_executed=False)))
