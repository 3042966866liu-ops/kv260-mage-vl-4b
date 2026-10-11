"""Mechanically derive an isolated shell from the audited stable shell template."""
from pathlib import Path
from measurement import sha256, write_json

root = Path(__file__).resolve().parents[2]
src = root/'vivado/mage_m120_m89x2_highddr/create_candidate_project.tcl'
dst = root/'vivado/op01_decode_one_experimental/create_candidate_project.tcl'
if dst.exists():
    raise RuntimeError('Refuse existing derived script')
text = src.read_text()
changes = {
    'tmp/m120_m89x2_highddr': 'tmp/op01_d1_exp',
    'mage_m120_m89x2_highddr': 'op01_d1_exp',
    '$workspace_root/m132_m120_fifo_backpressure_hls/hls/impl/ip': '$workspace_root/tmp/op01_decode_one_experimental_export/hls/impl/ip',
    'tellme.local:hls:m89x_runtime_kernel:1.0': 'xilinx.com:hls:op01_decode_one_kernel:1.0',
    'mage_m120_m89x2': 'op01_decode_one',
    '0x4D395832': '0x4F503131',
    'M134_': 'OP01_EXPERIMENTAL_',
    'save_project_as -force': 'save_project_as',
    'file delete -force $candidate_dir': 'error "Refuse existing experimental project: $candidate_dir"',
}
for old, new in changes.items():
    if old not in text:
        raise RuntimeError('Template anchor missing: '+old)
    text = text.replace(old, new)
assert 'file delete' not in text
assert 'stop_runs' not in text
assert '0x4D395832' not in text
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text('# Experimental capacity exception: see DECODE_ONE_EXPERIMENTAL_EXECUTION.md\n'+text)
write_json(dst.with_suffix('.derivation.json'), {
    'source': str(src.relative_to(root)), 'source_sha256': sha256(src),
    'derived_sha256': sha256(dst), 'replacements': changes,
    'candidate_build': '0x4F503131', 'capacity_pass': False,
    'board_deployed': False})
print('ISOLATED_SHELL_SCRIPT_PREPARED')
