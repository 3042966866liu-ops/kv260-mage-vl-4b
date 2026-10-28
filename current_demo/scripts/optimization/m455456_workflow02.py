"""Independent M455/M456 offline candidates, immutable inputs and bounded tools.

No board, shell implementation, boot, stable runtime, or service mutations.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
import msvcrt
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m441_host_io08 import atomic
from m351_workflow import sync

BASE = ROOT / "deployment/mage_vl4b/optimization_v1"
SOURCE = ROOT / "tmp/m443_pair_pipeline_03"
ENTRY = Path("hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp")
RUNTIME = ROOT / "release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime"
PROJECT_ROOT = Path("D:/CodexHome/visualizations/2026/10/11/01a12a98-44b4-7503-9ea1-46a7b5bcdc3f/native_hls")
VARIANTS = {"455": "dense_output", "456": "decode_overlap"}


def build(number):
    return f"0x4D3435{0x30 + int(number[-1]):02X}"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode()


def locations(number):
    label = f"M{number}-{VARIANTS[number]}-02"
    return BASE / "candidates" / label, BASE / "runs" / label, PROJECT_ROOT / label


def record(number, name, value, description):
    _, evidence, _ = locations(number)
    path = evidence / (name + ".json")
    atomic(path, encoded(value), immutable=True)
    digest = sha(path)
    synchronized(f"latest_m{number}_{name.lower()}02",
                 dict(status=value["status"], result=path.relative_to(ROOT).as_posix(), sha256=digest,
                      build_id=build(number), board=False, performance_pass=False, promoted=False),
                 f"## M{number} {description}02（2026-10-11）\n\nSHA {digest}；{value['status']}。"
                 f" Build{build(number)}，独立M443派生候选。无板端收益或晋级；"
                 "原工具启动01及状态竞争证据保留；稳定0x4D395832及M443冻结制品保持。"
                 "失败仅本级；下一步以结果内next_step为准。")
    print(value["status"], digest, flush=True)
    return path


def synchronized(key, value, note):
    # Both tools may run concurrently; their shared evidence updates must not.
    lock = ROOT / "tmp/m455456_state_sync.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+b") as f:
        if f.seek(0, 2) == 0:
            f.write(b"0")
            f.flush()
        deadline = time.monotonic() + 30
        while True:
            f.seek(0)
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Shared evidence writer lock timed out")
                time.sleep(.1)
        try:
            sync(key, value, note)
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def dense_source(original):
    begin = original.index("static void m89x_merge(")
    end = original.index("\nstatic void m89x_four(", begin)
    merge = '''static void m89x_merge(hls::stream<m89s_pair_t> r[4],
                       hls::stream<m89_axis64_t> &rx,
                       unsigned rows, bool final_descriptor) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=r complete
  for (unsigned block = 0; block < rows / 8; ++block)
    for (unsigned token = 0; token < 32; ++token)
      for (unsigned shard = 0; shard < 4; ++shard)
      {
        ap_uint<32> held = 0;
        for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
          // One pair read per cycle; emit one dense beat per two pair reads.
          ap_uint<32> value = r[shard].read().data;
          if ((pair & 1) == 0) {
            held = value;
          } else {
            m89_axis64_t item;
            item.data.range(31, 0) = held;
            item.data.range(63, 32) = value;
            item.keep = -1;
            item.strb = -1;
            item.last = final_descriptor && block + 1 == rows / 8 &&
                        token == 31 && shard == 3 && pair == 3;
            rx.write(item);
          }
        }
      }
}
'''
    # Intentionally do not require two reads from one FIFO in an II=1 loop.
    # Actual merge schedule must be measured; packing alone does not double it.
    return (original[:begin] + merge + original[end:]).replace("0x4D343433U", "0x4D343535U")


def overlap_source(original):
    begin = original.index("static void m443_compute(")
    decoder = '''struct m456_record_t {
  ap_uint<2560> weights;
  ap_uint<256> scales;
};

static void m456_decode_records(hls::stream<ap_uint<128> > &records,
                               hls::stream<m456_record_t> &decoded,
                               unsigned groups, unsigned rows, unsigned bits) {
#pragma HLS INLINE off
  const unsigned words = 1 + 4 * bits;
  for (unsigned block = 0; block < rows / 8; ++block)
    for (unsigned group = 0; group < groups; ++group) {
      ap_uint<128> record[17];
#pragma HLS BIND_STORAGE variable=record type=ram_2p impl=lutram
      for (unsigned i = 0; i < words; ++i) {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=9 max=17
        record[i] = records.read();
      }
      ap_uint<128> tagged = record[0];
      m456_record_t packet;
      for (unsigned pair = 0; pair < 4; ++pair) {
        ap_int<5> w0[64], w1[64];
#pragma HLS ARRAY_PARTITION variable=w0 complete
#pragma HLS ARRAY_PARTITION variable=w1 complete
        ap_uint<16> tag0 = tagged.range(32 * pair + 15, 32 * pair);
        ap_uint<16> tag1 = tagged.range(32 * pair + 31, 32 * pair + 16);
        m89x_decode_pair(record, pair, bits, tag0, tag1, w0, w1);
        for (unsigned k = 0; k < 64; ++k) {
#pragma HLS UNROLL
          unsigned at = (pair * 128 + k) * 5;
          packet.weights.range(at + 4, at) = (ap_uint<5>)w0[k];
          at += 320;
          packet.weights.range(at + 4, at) = (ap_uint<5>)w1[k];
        }
        fp_struct<float> s0(m89x_scale_float(tag0 & 0x7fff));
        fp_struct<float> s1(m89x_scale_float(tag1 & 0x7fff));
        packet.scales.range(pair * 64 + 31, pair * 64) = s0.data();
        packet.scales.range(pair * 64 + 63, pair * 64 + 32) = s1.data();
      }
      decoded.write(packet);
    }
}

'''
    candidate = original[:begin] + decoder + original[begin:]
    candidate = candidate.replace("static void m443_compute(hls::stream<ap_uint<128> > &records,",
                                  "static void m456_compute(hls::stream<m456_record_t> &decoded,")
    candidate = candidate.replace("  ap_uint<128> record[17];\n#pragma HLS BIND_STORAGE variable=record type=ram_2p impl=lutram\n  float acc0", "  float acc0")
    begin = candidate.index("      for (unsigned i = 0; i < words; ++i) {", candidate.index("static void m456_compute"))
    end = candidate.index("      for (unsigned work = 0; work < 64; ++work)", begin)
    old = candidate[begin:end]
    begin_weights = old.index("      ap_int<5> weight0[4][64]")
    end_weights = old.index("      for (unsigned pair = 0; pair < 4; ++pair)")
    storage = old[begin_weights:end_weights]
    replacement = "      m456_record_t packet = decoded.read();\n" + storage + '''      for (unsigned pair = 0; pair < 4; ++pair) {
        for (unsigned k = 0; k < 64; ++k) {
#pragma HLS UNROLL
          unsigned at = (pair * 128 + k) * 5;
          weight0[pair][k] = (ap_int<5>)packet.weights.range(at + 4, at);
          at += 320;
          weight1[pair][k] = (ap_int<5>)packet.weights.range(at + 4, at);
        }
        fp_struct<float> s0((ap_uint<32>)packet.scales.range(pair * 64 + 31, pair * 64));
        fp_struct<float> s1((ap_uint<32>)packet.scales.range(pair * 64 + 63, pair * 64 + 32));
        scale0[pair] = s0.to_float();
        scale1[pair] = s1.to_float();
      }
'''
    candidate = candidate[:begin] + replacement + candidate[end:]
    anchor = "  m441_load_records(memory, records, groups, rows, bits);\n  m443_compute(records, x, as, out, groups, rows, bits);"
    assert candidate.count(anchor) == 1
    candidate = candidate.replace(anchor, '''  hls::stream<m456_record_t> decoded("decoded");
#pragma HLS STREAM variable=decoded depth=2
#pragma HLS BIND_STORAGE variable=decoded type=fifo impl=lutram
  m441_load_records(memory, records, groups, rows, bits);
  m456_decode_records(records, decoded, groups, rows, bits);
  m456_compute(decoded, x, as, out, groups, rows, bits);''')
    # Exactly the original dot/scale/accumulator expression and group order.
    mac_start = "      for (unsigned work = 0; work < 64; ++work)"
    mac_end = "\n    }\n    for (unsigned token"
    assert original[original.index(mac_start):original.index(mac_end, original.index(mac_start))] == candidate[candidate.index(mac_start):candidate.index(mac_end, candidate.index(mac_start))]
    return candidate.replace("0x4D343433U", "0x4D343536U")


def closure(root, entries):
    pending, seen = list(entries), {}
    while pending:
        p = pending.pop().resolve()
        p.relative_to(root.resolve())
        if p in seen:
            continue
        if not p.is_file():
            raise RuntimeError("Missing quoted header: " + str(p))
        seen[p] = p.read_bytes()
        for inc in re.findall(r'^\s*#\s*include\s*"([^"]+)"', seen[p].decode("utf-8-sig"), re.M):
            pending.append(p.parent / inc)
    return seen


def boundary_tb(number, raw):
    raw = raw.replace("int main()", "int m455456_boundary_main()")
    raw = raw.replace("0x4D343433U", build(number) + "U")
    if number == "455":
        # Compare every scalar against the existing independent integer/FP32 oracle.
        start = raw.index("          for (unsigned pair = 0; pair < 4; ++pair) {")
        end = raw.index("\n    if (!rx.empty()", start)
        raw = raw[:start] + '''          for (unsigned pair_block = 0; pair_block < 2; ++pair_block) {
            m89_axis64_t item = rx.read();
            const ap_uint<128> *base = &weights[shard][offsets[descriptor_index]];
            for (unsigned scalar = 0; scalar < 4; ++scalar) {
              unsigned row = pair_block * 4 + scalar;
              ap_uint<16> expected = half_bits(independent_golden(
                  base, bits[descriptor_index], groups, activation, token, row));
              if (item.data.range(scalar * 16 + 15, scalar * 16) != expected)
                return 9;
            }
            bool last = descriptor_index + 1 == count && token == 31 && shard == 3 && pair_block == 1;
            if (bool(item.last) != last || item.keep != 0xff || item.strb != 0xff)
              return 10;
            ++total_output_words;
          }''' + raw[end:]
    return raw


def full_tb(number):
    raw = (ROOT / "scripts/optimization/m441_full_chain_tb.cpp").read_text(encoding="utf-8")
    raw = raw.replace("int main()", "int m455456_boundary_main();\nint main()")
    raw = raw.replace("ordinal<3", "ordinal<5")
    raw = raw.replace("0x4D343431U", build(number) + "U")
    if number == "455":
        at = "    if(!in||in.peek()!=std::char_traits<char>::eof()) return 4;"
        packed = '''    std::vector<ap_uint<64> > compact(expected.size()/2);
    if(expected.size()%2) return 14;
    for(unsigned j=0;j<compact.size();++j) {
      ap_uint<64> a=expected[2*j], b=expected[2*j+1];
      if(a.range(31,16)!=0||a.range(63,48)!=0||b.range(31,16)!=0||b.range(63,48)!=0) return 15;
      compact[j].range(15,0)=a.range(15,0);
      compact[j].range(31,16)=a.range(47,32);
      compact[j].range(47,32)=b.range(15,0);
      compact[j].range(63,48)=b.range(47,32);
    }
    expected.swap(compact);
'''
        assert raw.count(at) == 1
        raw = raw.replace(at, at + "\n" + packed)
    raw = raw.replace('  std::cout<<"M441_FULL_REAL_WEIGHT_NUMERICAL_PASS"<<std::endl;',
                      f'  if(m455456_boundary_main()!=0) return 16;\n  std::cout<<"M{number}_ALL_NUMERICAL_PASS"<<std::endl;')
    return raw


def protocol_fixture(bits):
    # Max descriptor count and 8192-word per-shard output, without a model task.
    groups, rows, count = 1, 512, 10
    words, blocks = 1 + 4 * bits, rows // 8
    window = groups * blocks * words * 16 * count
    descriptors = b"".join(struct.pack("<QQ", i * groups * blocks * words | rows << 32 | bits << 42, 0) for i in range(count))
    # Zero activation => independent exact zero golden; nonzero weight codes/tags.
    activation = bytes(groups * 32 * 80)
    record = struct.pack("<8H", *([0x3c00] * 8)) + bytes([0x5a] * ((words - 1) * 16))
    weights = record * (groups * blocks * count)
    assert len(weights) == window
    output = count * rows * 4 * 32 * 4
    return b"M441FUL1" + struct.pack("<5I", groups | bits << 8 | count << 16, count, len(descriptors + activation), output, window) + descriptors + activation + weights * 4 + bytes(output)


def host_components(number, package):
    import numpy as np
    sys.path.insert(0, str(RUNTIME))
    from contract_runtime import parse_chain_output
    from m455_dense_output import dense_contract, parse_dense_output, compact_reference
    prep = json.loads((ROOT / "tmp/m445_csim_01/PREPARATION.json").read_bytes())
    records, negatives = [], 0
    if number == "456":
        return dict(status="NOT_APPLICABLE_UNCHANGED_OUTPUT_ABI", checks=0)
    for variant in ("A", "B"):
        for family in ("gate_up", "down"):
            item = prep["variants"][variant][family]
            golden = ROOT / "tmp/m445_csim_01" / item["path"] / "golden.bin"
            assert sha(golden) == item["files"]["golden.bin"]["sha256"]
            original, dense = item["chain"], dense_contract(item["chain"])
            payload = golden.read_bytes()
            packed = compact_reference(payload)
            assert len(packed) * 2 == len(payload)
            for shift in (0, 1, 10):
                a = parse_chain_output(original, payload, shift)
                b = parse_dense_output(dense, packed, shift)
                assert a.keys() == b.keys()
                assert all(np.array_equal(a[k].view(np.uint32), b[k].view(np.uint32)) for k in a)
            for bad in (packed[:-8], packed + bytes(8), payload):
                try:
                    parse_dense_output(dense, bad)
                except ValueError:
                    negatives += 1
                else:
                    raise AssertionError("Wrong size accepted")
            records.append(dict(variant=variant, family=family, original_bytes=len(payload), dense_bytes=len(packed), original_contract_unchanged=original == item["chain"], shifts=[0, 1, 10]))
    # Exhaustive binary16 payloads check signed zero, denormals, infinities and NaN bits.
    values = np.arange(65536, dtype="<u2").reshape(-1, 2)
    legacy = np.zeros((len(values), 4), dtype="<u2")
    legacy[:, 0], legacy[:, 2] = values[:, 0], values[:, 1]
    assert compact_reference(legacy.tobytes()) == values.tobytes()
    return dict(status="PASS_DENSE_HOST_COMPONENTS", real_family_cases=records, bit_patterns_preserved=65536, wrong_size_rejections=negatives,
                board=False, performance=False, module_sha256=sha(package / "m455_dense_output.py"))


def prepare(number):
    package, evidence, project = locations(number)
    if package.exists() or evidence.exists() or project.exists():
        raise RuntimeError("Existing attempt: collect only")
    recovery = {}
    texts = {}
    for name in ("CURRENT_STATE.md", "docsMILESTONES.md", "DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md", "AGENTS.md", "deployment/mage_vl4b/BOARD_GATE_RESULT.json"):
        path = ROOT / name
        texts[name] = path.read_text(encoding="utf-8-sig")
        recovery[name] = dict(sha256=sha(path), bytes=path.stat().st_size, lines=len(texts[name].splitlines()))
    board = json.loads(texts["deployment/mage_vl4b/BOARD_GATE_RESULT.json"])
    prerequisites = {}
    for key in ("latest_m443_full_shell04", "latest_m443_complete_request_closure01", "latest_m445_complete_MLP_comparison"):
        item = board[key]
        assert sha(ROOT / item["result"]) == item["sha256"]
        assert all(item["sha256"] in texts[n] for n in ("CURRENT_STATE.md", "docsMILESTONES.md"))
        prerequisites[key] = item
    selection = BASE / "contracts/EVALUATION_DATASET.json"
    assert json.loads(selection.read_bytes())["dataset_id"] == "sar_visible_infrared_v1"
    original = (SOURCE / ENTRY).read_text(encoding="utf-8")
    assert sha(SOURCE / ENTRY) == "4da9eadbe97d8b8b072e109ab44c155e5f45d715fff87b4f972a1ff538421040"
    candidate = dense_source(original) if number == "455" else overlap_source(original)
    dependencies = closure(SOURCE, [SOURCE / ENTRY])
    for p, raw in dependencies.items():
        atomic(package / p.relative_to(SOURCE), candidate.encode() if p == (SOURCE / ENTRY).resolve() else raw, immutable=True)
    atomic(package / "SOURCE.diff", "".join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True), fromfile="frozen-M443.cpp", tofile=f"independent-M{number}.cpp")).encode(), immutable=True)
    boundary = SOURCE / "hls/mage_prefill_m89x_runtime/tb_m128_m120_numerical.cpp"
    include = '#include "mage_prefill_m89x_runtime.hpp"'
    explicit = '#include "hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.hpp"'
    atomic(package / "boundary_tb.cpp", boundary_tb(number, boundary.read_text(encoding="utf-8")).replace(include, explicit).encode(), immutable=True)
    atomic(package / "full_tb.cpp", full_tb(number).replace(include, explicit).encode(), immutable=True)
    sample_prep = ROOT / "tmp/m445_csim_01/PREPARATION.json"
    sample = json.loads(sample_prep.read_bytes())
    assert sample["selected_sample"]["sample"]["modality"] == "SAR"
    for i, (variant, family) in enumerate((("A", "gate_up"), ("A", "down"), ("B", "down"))):
        item = sample["variants"][variant][family]
        path = ROOT / "tmp/m445_csim_01" / item["path"] / "fixture.bin"
        assert sha(path) == item["files"]["fixture.bin"]["sha256"]
        atomic(package / f"case{i}.bin", path.read_bytes(), immutable=True)
    for i, bits in enumerate((2, 4), 3):
        atomic(package / f"case{i}.bin", protocol_fixture(bits), immutable=True)
    fixture = ROOT / "deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin"
    assert sha(fixture) == "f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9"
    atomic(package / "boundary_fixture.bin", fixture.read_bytes(), immutable=True)
    atomic(package / "m455_dense_output.py", (Path(__file__).parent / "m455_dense_output.py").read_bytes(), immutable=True)
    header_files = closure(package, [package / ENTRY, package / "boundary_tb.cpp", package / "full_tb.cpp"])
    # Testbenches' header resides under the explicit -I include path, not sibling.
    host = host_components(number, package)
    atomic(package / "HOST_COMPONENT_RESULT.json", encoded(host), immutable=True)
    tcl = f'''set root {{{package.as_posix()}}}
set project {{{project.as_posix()}}}
if {{[file exists $project]}} {{error "Existing HLS project: collect only"}}
set ::env(M441_FULL_FIXTURE_ROOT) $root
set ::env(M128_FIXTURE_PATH) [file join $root boundary_fixture.bin]
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root {ENTRY.as_posix()}]
add_files -tb [file join $root full_tb.cpp] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
add_files -tb [file join $root boundary_tb.cpp] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {{xck26-sfvc784-2LV-c}}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean -O
csynth_design
exit
'''
    atomic(package / "run_hls.tcl", tcl.encode(), immutable=True)
    rows = [dict(path=p.relative_to(package).as_posix(), sha256=sha(p), bytes=p.stat().st_size) for p in sorted(package.rglob("*")) if p.is_file()]
    assert not list(package.rglob("__pycache__")) and not list(package.rglob("*.pyc"))
    manifest = dict(schema="m455456-offline-candidate-v1", number=number, files=rows, file_count=len(rows), total_bytes=sum(p["bytes"] for p in rows), missing_headers=0)
    atomic(package / "PACKAGE_MANIFEST.json", encoded(manifest), immutable=True)
    record(number, "PREPARATION", dict(status=f"PREPARED_M{number}_INDEPENDENT_OFFLINE_CANDIDATE", recovery_read=recovery,
        build_id=build(number), baseline_build_id="0x4D343433", prerequisites=prerequisites,
        source_sha256=sha(package / ENTRY), baseline_source_sha256=sha(SOURCE / ENTRY), manifest_sha256=sha(package / "PACKAGE_MANIFEST.json"),
        recursive_headers=len(header_files), missing_headers=0, project=str(project), tool="D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat",
        evaluation_dataset_sha256=sha(selection), real_SAR_fixture_preparation_sha256=sha(sample_prep), real_sample=sample["selected_sample"],
        fixtures="three frozen SAR full chains; W2/W4 max-output/count synthetic protocol; seven historical text numeric boundaries",
        no_new_knife_evaluation=True, same_MAC_expressions=True, output_ABI_changed=number == "455", extra_MAC_lanes=0,
        host_components=host, CSim=False, RTL=False, routed=False, board=False, performance=False,
        next_step="Run bounded numerical CSim then HLS resource/II admission once; failed level only. RTL/shell/board remain locked."), "独立硬件候选准备")


def verify(number):
    package, evidence, _ = locations(number)
    prep = json.loads((evidence / "PREPARATION.json").read_bytes())
    assert sha(package / "PACKAGE_MANIFEST.json") == prep["manifest_sha256"]
    manifest = json.loads((package / "PACKAGE_MANIFEST.json").read_bytes())
    assert all(sha(package / row["path"]) == row["sha256"] for row in manifest["files"])
    actual = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()}
    assert actual == {r["path"] for r in manifest["files"]} | {"PACKAGE_MANIFEST.json"}
    assert manifest["file_count"] == len(manifest["files"])
    assert manifest["total_bytes"] == sum((package / r["path"]).stat().st_size for r in manifest["files"])
    assert all(sha(evidence / "PREPARATION.json") in (ROOT / n).read_text(encoding="utf-8-sig") for n in ("CURRENT_STATE.md", "docsMILESTONES.md", "deployment/mage_vl4b/BOARD_GATE_RESULT.json"))
    return prep


def collect(number):
    package, evidence, project = locations(number)
    verify(number)
    receipt = json.loads((evidence / "EXIT.json").read_bytes())
    assert not receipt["process_retained"]
    log = project / "hls/csim/report/m89x_runtime_kernel_csim.log"
    text = log.read_text(encoding="utf-8-sig") if log.is_file() else ""
    expected = []
    for i in range(5):
        with (package / f"case{i}.bin").open("rb") as f:
            head = f.read(28)
        output_bytes = struct.unpack("<5I", head[8:])[3]
        expected.append((str(i), str(output_bytes // (16 if number == "455" else 8))))
    found = re.findall(r"^M441_FULL_CHAIN_PASS ordinal=(\d+) output_words=(\d+)\s*$", text, re.M)
    checks = dict(original_rc=receipt["original_rc"] == 0,
                  full_real_and_max_cases=found == expected,
                  boundary_cases=len(re.findall(r"^M128_CHAIN_PASS ordinal=", text, re.M)) == 7,
                  numeric_marker=f"M{number}_ALL_NUMERICAL_PASS" in text,
                  csim_completion="CSim done with 0 errors" in text,
                  no_numerical_error=not re.search(r"mismatch|wrong status|short output", text, re.I))
    top = project / "hls/syn/report/m89x_runtime_kernel_csynth.xml"
    resources, capacity, loops = {}, {}, []
    if top.is_file():
        root = ET.parse(top).getroot()
        resources = {x.tag: int(x.text) for x in root.find("AreaEstimates/Resources")}
        capacity = {x.tag: int(x.text) for x in root.find("AreaEstimates/AvailableResources")}
        checks["same_clock"] = float(root.findtext("UserAssignments/TargetClockPeriod")) == 4.8 and float(root.findtext("UserAssignments/ClockUncertainty")) == 1.3
        checks["resources_fit"] = all(resources[k] <= capacity[k] for k in resources)
        for path in sorted(top.parent.glob("*compute*Pipeline*csynth.xml")):
            r = ET.parse(path).getroot()
            if int(r.findtext("AreaEstimates/Resources/DSP", "0")) != 288:
                continue
            for loop in r.find("PerformanceEstimates/SummaryOfLoopLatency"):
                loops.append(dict(path=str(path), sha256=sha(path), trip=int(loop.findtext("TripCount")), II=int(loop.findtext("PipelineII")), depth=int(loop.findtext("PipelineDepth")), DSP=288))
        checks["same_four_MAC_lanes_II1"] = len(loops) == 4 and all(r["trip"] == 64 and r["II"] == 1 for r in loops)
    else:
        checks["HLS_report_exists"] = False
    passed = all(checks.values())
    result = dict(status=f"{'PASS' if passed else 'FAIL'}_M{number}_OFFLINE_NUMERICAL_AND_HLS_ADMISSION", checks=checks,
                  original_rc=receipt["original_rc"], resources=resources, capacity=capacity, actual_MAC_loops=loops,
                  cases=found, expected_cases=expected, output_words=sum(int(t[1]) for t in expected),
                  console_sha256=sha(evidence / "console.log"), CSim_log_sha256=sha(log) if log.is_file() else None,
                  top_report_sha256=sha(top) if top.is_file() else None, elapsed_s=receipt["elapsed_s"],
                  finite_CSim_queues=False, RTL=False, routed=False, board=False, performance=False,
                  next_step="Prepare bounded RTL max occupancy/backpressure/TLAST/done/return/timeout gates; no shell or board yet." if passed else "Diagnose only this failed numerical/HLS level; preserve original attempt and do not start RTL/shell/board.")
    record(number, "RESULT", result, "数值及HLS门禁")
    return 0 if passed else 1


def run(number):
    package, evidence, project = locations(number)
    verify(number)
    if (evidence / "ACTIVE.json").exists() or project.exists():
        raise RuntimeError("Existing launch: observe/collect only")
    project.parent.mkdir(parents=True, exist_ok=True)
    command = ["D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat", "--mode", "hls", "--tcl", str(package / "run_hls.tcl"), "--log", str(evidence / "vitis")]
    started, budget = time.monotonic(), 7200
    with (evidence / "console.log").open("xb") as log:
        child = subprocess.Popen(command, cwd=project.parent, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        from m441_supervisor04 import boot, process, classify
        birth = process(child.pid)
        start_boot = boot()
        record(number, "ACTIVE", dict(status=f"RUNNING_M{number}_BOUNDED_OFFLINE_HLS", pid=child.pid, creation_FILETIME=birth.get("creation_FILETIME"), command=command,
              controller_sha256=sha(__file__), wall_budget_s=budget, board=False, next_step="Observe this exact attempt; collect saved bytes on completion; no duplicate launch."), "有限离线工具启动")
        retained = False
        while child.poll() is None:
            state = process(child.pid, birth.get("creation_FILETIME"))
            elapsed = time.monotonic() - started
            atomic(evidence / "PROGRESS.json", encoded(dict(status=classify(start_boot, boot(), state), elapsed_s=elapsed, process=state)))
            if elapsed > budget:
                retained = True
                break
            time.sleep(10)
        receipt = dict(original_rc=None if retained else child.returncode, elapsed_s=time.monotonic() - started,
                       process_retained=retained, budget_exceeded=retained, process_killed=False, console_sha256=sha(evidence / "console.log"))
        atomic(evidence / "EXIT.json", encoded(receipt), immutable=True)
    return 1 if retained else collect(number)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "run", "collect", "verify"))
    parser.add_argument("number", choices=VARIANTS)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.number)
    elif args.mode == "verify":
        verify(args.number)
        print("FROZEN_MANIFEST_VERIFIED")
    else:
        raise SystemExit(run(args.number) if args.mode == "run" else collect(args.number))
