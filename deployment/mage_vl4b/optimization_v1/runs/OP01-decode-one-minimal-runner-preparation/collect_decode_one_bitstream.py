"""Collect this candidate only after the original implementation completes.

No Vivado launch, source edits, or device access. Capacity incompleteness survives.
"""
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
from measurement import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'tmp/op01_d1_exp'
HWH = PROJECT / 'op01_d1_exp.gen/sources_1/bd/qwen25_mixed_gs/hw_handoff/qwen25_mixed_gs.hwh'
OUT = ROOT / 'deployment/mage_vl4b/optimization_v1/candidates/OP01-decode-one-experimental-artifacts'


def check_hwh(path):
    tree = ET.parse(path)
    modules = [m for m in tree.iter('MODULE') if m.get('INSTANCE') == 'op01_decode_one_0']
    if len(modules) != 1 or modules[0].get('VLNV') != 'xilinx.com:hls:op01_decode_one_kernel:1.0':
        raise ValueError('Candidate kernel identity missing/ambiguous')
    registers = {}
    for reg in modules[0].iter('REGISTER'):
        props = {x.get('NAME'): x.get('VALUE') for x in reg.findall('PROPERTY')}
        registers[reg.get('NAME')] = int(props['ADDRESS_OFFSET'], 0)
    expected = dict(CTRL=0, ap_return=0x10, s0_1=0x18, s0_2=0x1c,
                    s1_1=0x24, s1_2=0x28, s2_1=0x30, s2_2=0x34,
                    s3_1=0x3c, s3_2=0x40, config_r=0x80)
    if any(registers.get(k) != v for k, v in expected.items()):
        raise ValueError('Candidate register ABI mismatch: ' + str(registers))
    return expected


def check_route_gate(text):
    match = re.fullmatch(r'build=0x4F503131 capacity_pass=false WNS=(\S+) WHS=(\S+) serious_drc=(\d+)\s*', text)
    if match is None:
        raise ValueError('Missing exact candidate route gate')
    wns, whs = map(float, match.group(1, 2))
    serious = int(match[3])
    if not all(math.isfinite(x) and x >= 0 for x in (wns, whs)) or serious:
        raise ValueError('Routed timing or serious DRC failed')
    return dict(wns_ns=wns, whs_ns=whs, serious_drc=serious)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-hwh-only', action='store_true')
    args = parser.parse_args()
    abi = check_hwh(HWH)
    if args.check_hwh_only:
        print(json.dumps(dict(status='PASS_HWH_ABI_ONLY', registers=abi, board_deployed=False)))
        return
    if OUT.exists():
        raise RuntimeError('Refuse existing immutable artifact directory')
    log = ROOT / 'tmp/op01_d1_shell_logs/implementation02.log'
    if 'OP01_EXPERIMENTAL_BITSTREAM_CREATED' not in log.read_text(errors='replace'):
        raise RuntimeError('Original build has not completed bitstream generation')
    route = PROJECT / 'out'
    timing = check_route_gate((route / 'route_gate.txt').read_text())
    bits = list((PROJECT / 'op01_d1_exp.runs/impl_1').glob('*.bit'))
    if len(bits) != 1 or bits[0].stat().st_size == 0:
        raise RuntimeError('Missing/ambiguous bitstream')
    routing = (route / 'impl_route_status.rpt').read_text()
    errors = re.search(r'# of nets with routing errors\.+\s*:\s*(\d+)', routing)
    if errors is None or int(errors[1]) != 0:
        raise RuntimeError('Missing routing error count or nonzero routing errors')
    sources = {'overlay/op01_decode_one.bit': bits[0], 'overlay/op01_decode_one.hwh': HWH,
               'evidence/implementation.log': log}
    for name in ('route_gate.txt', 'impl_utilization.rpt', 'impl_timing_summary.rpt',
                 'impl_drc.rpt', 'impl_route_status.rpt', 'preflight_gate.txt', 'address_audit.txt'):
        sources['evidence/' + name] = route / name
    # Validate all paths before creating any staging directory.
    identities = {name: dict(bytes=p.stat().st_size, sha256=sha256(p)) for name, p in sources.items()}
    OUT.mkdir(parents=True)
    for name, source in sources.items():
        destination = OUT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if sha256(destination) != identities[name]['sha256']:
            raise RuntimeError('Copy verification failed: ' + name)
    write_json(OUT / 'ARTIFACT_MANIFEST.json', dict(
        build_id='0x4F503131', classification='EXPERIMENTAL_IMPLEMENTATION_ONLY',
        capacity_status='STOPPED_BY_USER_NOT_PASS', formal_promotion_allowed=False,
        board_deployed=False, performance_pass=False, timing=timing, registers=abi,
        files=[dict(path=name, **item) for name, item in identities.items()],
        file_count=len(identities), total_bytes=sum(x['bytes'] for x in identities.values())))
    print(json.dumps(dict(status='EXPERIMENTAL_BITSTREAM_COLLECTED_NOT_BOARD_PASS',
                         path=str(OUT), manifest_sha256=sha256(OUT / 'ARTIFACT_MANIFEST.json'))))


if __name__ == '__main__':
    main()
