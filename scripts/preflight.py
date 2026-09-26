#!/usr/bin/env python3
"""Read-only release preflight and first-install M254 launcher.

This wrapper never imports PYNQ during --help, --dry-run or --check.
The historical board gate remains unchanged and is not a first-install entry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
STABLE = ROOT / "deployment/mage_vl4b"
M254 = STABLE / "m254_dual_path_web_candidate"
M181 = STABLE / "m181_m120_video_board_candidate"
M175 = STABLE / "m175_m120_fixed_text_candidate"
M249 = STABLE / "m249_ssdlite_board_candidate"
M223 = ROOT / "tmp/m223_realtime/m223_realtime_delta"
RUNTIME_SITE = ROOT / "runtime_site"
RUNTIME_BUNDLE_SHA = "5b414672750e1e62ebbe6360e96a3a991a293d8da3dd9fa292eb8a29d0b07c96"
PILLOW_WHEEL_SHA = "a40905599d8079e09f25027423aed94f2823adaf2868940de991e53a449e14a8"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(4 << 20), b""):
            h.update(part)
    return h.hexdigest()


def resolve(value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else ROOT / path).resolve()


def display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return "<external>/" + path.name


def required_paths(config: dict) -> dict[str, Path]:
    weights = resolve(config["weights_root"])
    return {
        "candidate_manifest": M181 / "PACKAGE_MANIFEST.json",
        "candidate_ready": M181 / "PACKAGE_READY.json",
        "text_manifest": M175 / "PACKAGE_MANIFEST.json",
        "predecessor_summary": M223 / "M223_PREDECESSOR_SUMMARY.json",
        "m243_result": M254 / "M243_WEB_PREFILL_BOARD_RESULT_05.json",
        "m253_result": M254 / "M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json",
        "m249_result": M254 / "M249_KV260_SSDLITE_BOARD_RESULT_03.json",
        "overlay_bit": M175 / "overlay/m120_m89x2_t32.bit",
        "overlay_hwh": M175 / "overlay/m120_m89x2_t32.hwh",
        "fixed_text_auxiliary": M175 / "auxiliary/m77_text_aux_fp16.npz",
        "layer0_reference": M175 / "reference/m143_m120_layer0_boundaries.npz",
        "video_overlay_bit": M181 / "text_runtime/overlay/m120_m89x2_t32.bit",
        "video_overlay_hwh": M181 / "text_runtime/overlay/m120_m89x2_t32.hwh",
        "language_layout": weights / "language_fourport/SIXPORT_LAYOUT_MANIFEST.json",
        "lmhead_layout": weights / "lmhead_fourport/SIXPORT_LAYOUT_MANIFEST.json",
        **{f"language_shard_{i}": weights / f"language_fourport/weights{i}.bin" for i in range(4)},
        **{f"lmhead_shard_{i}": weights / f"lmhead_fourport/weights{i}.bin" for i in range(4)},
        "vision_layout": M181 / "vision_layout/SIXPORT_LAYOUT_MANIFEST.json",
        **{f"vision_shard_{i}": M181 / f"vision_layout/weights{i}.bin" for i in range(4)},
        "vision_weights": M181 / "ps_vision_payload/vision_bf16.safetensors",
        "vision_code": M181 / "ps_vision_payload/modeling_mage_vl.py",
        "model_config": M181 / "ps_vision_payload/config.json",
        "tokenizer": M181 / "text_auxiliary/tokenizer/tokenizer.json",
        "vocab": M181 / "text_auxiliary/tokenizer/vocab.json",
        "embedding": M181 / "text_auxiliary/embedding.fp16.rowmajor.bin",
        "text_norms": M181 / "text_auxiliary/text_norms.fp16.npz",
        "raw_vision": M181 / "auxiliary/m90_vision_raw_bf16.bin",
        "detector": M249 / "model/ssdlite320_mobilenet_v3_large_coco-a79551df.pth",
        "runtime_wheel_bundle": ROOT / "external_assets/runtime_wheels/m327_runtime_wheels_20260926.tar",
        "pillow_wheel": ROOT / "external_assets/runtime_wheels/pillow-12.1.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
    }


def inspect(config: dict, port_check: bool) -> dict:
    paths = required_paths(config)
    missing = [name for name, path in paths.items() if not path.is_file()]
    mismatched = []
    expected = {
        "overlay_bit": "1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac",
        "overlay_hwh": "9bd6100bcc274486ddd51133e4dc2247f35c030d49e53cc709438f2a74ee3520",
        "fixed_text_auxiliary": "7f2dfc14ae47cb537e148cafc9b1c6cc285e1fe546dec901275a4078a8458ffd",
        "layer0_reference": "9565ec2f7d1df162997456a6ccb01234c3b3e4802107ed318827553c3aa66eab",
        "video_overlay_bit": "1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac",
        "video_overlay_hwh": "9bd6100bcc274486ddd51133e4dc2247f35c030d49e53cc709438f2a74ee3520",
        "tokenizer": "ba0c439f7be467bf47d12a7e6f9adc6116201056fc60c67f431c679b7c16afc8",
        "vocab": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
        "embedding": "ec02de7da15a1569e96e50d886a3e4532617197e7a7aa84ac7196489caab4df4",
        "vision_weights": "312065d24f13432406b2016b02d28ee213ca545287748808a46796e05d36be0e",
        "vision_shard_0": "2e902f5f4ddec7165da4a873c713045fbb74bf0551d9dbda5fb0ce036776718e",
        "vision_shard_1": "ed7618c3337da91fcf52d1d3a1b153d828b7ef19ded48c4f149647cfa474b3fd",
        "vision_shard_2": "98c518e426d8bca035220d6a59bee13879d23f5f70eb4b6a3080921457588346",
        "vision_shard_3": "5b9ce87baab34a7b43df4ed436e09200635866d71a154a6e598b26a44ac08b2a",
        "text_norms": "c0d1e5fb6268bf28a4fbbbd6898715b5b39494a02b9e53d7c6e4c083bcbe2051",
        "raw_vision": "ae4353135414bf1691ce663f5973b67ab390f500b1b71789481d919c9d8a6eb2",
        "detector": "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2",
        "runtime_wheel_bundle": RUNTIME_BUNDLE_SHA,
        "pillow_wheel": PILLOW_WHEEL_SHA,
        "language_layout": "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d",
        "lmhead_layout": "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef",
        "language_shard_0": "7c037f04f65e9b13d5587c55af9861f6445f98dea47ffc942dcab8d825c25e65",
        "language_shard_1": "61dcf114ad1a87cbf8d455d5eef0b90f09a24cc89507678e2c7fee19f7857bed",
        "language_shard_2": "b8aabd302c0aba91dada96cde8967d088714b4e68cff5871ef36b6b2b7152101",
        "language_shard_3": "2218e49d70ea9c83a389a4244924855a3ebf335e6fe948898ca7d4d59ca4ae5c",
        "lmhead_shard_0": "71ee269ecaf5fcf1e07d06336f5b520d6bab473f4bfab02968a01011a278d50e",
        "lmhead_shard_1": "708422c93ebd4a517dcb25d205a6c330ae97ee15007ab455f214a8fa56c6d4f4",
        "lmhead_shard_2": "64b29a83ca5b2df16a6dd51b9a01eab5974eb722dd1fbc276ba8c4ad68d25c42",
        "lmhead_shard_3": "a5d954679387d0eef09dc50a16d5c124c8c7fbe5683b362a38c89e94057716f8",
        "vision_layout": "2d9bea77b8868d24fa7775886feb1b9c88b8e768d51b2e192802a439060b03c1",
        "text_manifest": "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f",
        "m243_result": "80ea2b8e1d142ef4400aa7e545cf62b3c6ae7a5531e4466df06b35758df096c6",
        "m253_result": "d9e56ea4dbb7b981f8aa02ed834317dca430f252b4ac412c7dbf762478ebc4eb",
        "m249_result": "e45597c3cc14a68420b09d389dde8c2b1cd81ab23eacc5833b5a527d4f633681",
    }
    for name, value in expected.items():
        if name not in missing and digest(paths[name]) != value:
            mismatched.append(name)
    if "candidate_manifest" not in missing and "candidate_ready" not in missing:
        ready = json.loads(paths["candidate_ready"].read_text(encoding="utf-8"))
        if digest(paths["candidate_manifest"]) != ready.get("package_manifest_sha256"):
            mismatched.append("candidate_manifest:ready_hash")
    for name in ("candidate_manifest", "predecessor_summary"):
        if name not in missing:
            try:
                data = json.loads(paths[name].read_text(encoding="utf-8"))
                if name == "candidate_manifest" and data.get("build_id", "").lower() != "0x4d395832":
                    mismatched.append(name + ":build_id")
            except (ValueError, OSError):
                mismatched.append(name + ":invalid_json")
    port_free = None
    if port_check:
        with socket.socket() as sock:
            try:
                sock.bind((config["host"], int(config["port"])))
                port_free = True
            except OSError:
                port_free = False
    return {"status": "READY_FOR_BOARD_PREFLIGHT" if not missing and not mismatched and port_free is not False else "BLOCKED",
            "build_id": "0x4D395832", "missing": missing, "hash_or_identity_mismatch": mismatched,
            "port_free": port_free, "checked_paths": {k: display(v) for k, v in paths.items()},
            "board_execution_run": False}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="configs/deployment.example.json")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="list planned action and missing files; no device access")
    group.add_argument("--check", action="store_true", help="fail closed on missing files; no device access")
    group.add_argument("--run", action="store_true", help="start original M254 service only after preflight")
    args = p.parse_args()
    config_path = resolve(args.config)
    if not config_path.is_file():
        p.error(f"config not found: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for name in ("weights_root", "host", "port"):
        if name not in config:
            p.error(f"missing config field: {name}")
    status = inspect(config, port_check=args.run)
    status["planned_entry"] = "deployment/mage_vl4b/m254_dual_path_web_candidate/m254_video_server.py"
    print(json.dumps(status, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0
    if status["status"] != "READY_FOR_BOARD_PREFLIGHT":
        return 2
    if args.check or not args.run:
        return 0
    marker = RUNTIME_SITE / "RUNTIME_SITE_READY.json"
    if (RUNTIME_SITE.is_symlink() or not RUNTIME_SITE.resolve().is_relative_to(ROOT)
            or not marker.is_file() or not (RUNTIME_SITE / "torch/__init__.py").is_file()
            or not (RUNTIME_SITE / "torchvision/__init__.py").is_file()):
        print("BLOCKED: isolated Torch runtime is not installed; run scripts/install_runtime_wheels.py first", file=sys.stderr)
        return 3
    try:
        ready = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("BLOCKED: isolated runtime marker is unreadable", file=sys.stderr)
        return 3
    if (ready.get("status") != "PASS" or ready.get("bundle_sha256") != RUNTIME_BUNDLE_SHA
            or ready.get("pillow_sha256") != PILLOW_WHEEL_SHA):
        print("BLOCKED: isolated runtime marker identity mismatch", file=sys.stderr)
        return 3
    # Exact historical Python import precedence, but rooted only in this release.
    module_dirs = [RUNTIME_SITE, M254, STABLE / "m243_web_prefill_board_candidate",
                   STABLE / "m242_m241_fixed_text_board_candidate",
                   STABLE / "m238_input_prefetch_board_candidate",
                   STABLE / "m241_grouped_gqa_board_candidate",
                   STABLE / "m231_parse_reuse_board_candidate",
                   ROOT / "tmp/m227_runtime_base/m227_runtime_base_patch",
                   ROOT / "tmp/m223_realtime/m223_realtime_delta",
                   ROOT / "tmp/m218_dual_source/m218_dual_source_delta",
                   M181 / "text_runtime", M181 / "ps_vision_payload", M181,
                   M175 / "runtime", M175 / "runtime/support"]
    # Initial board startup is intentionally blocked until this wrapper is
    # independently validated on KV260 with the external assets installed.
    if os.environ.get("TELLME_RELEASE_BOARD_LAUNCH_UNVERIFIED") != "ACKNOWLEDGED":
        print("BLOCKED: release launcher has not been tested on KV260; set explicit acknowledgment only after board validation", file=sys.stderr)
        return 3
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        print("BLOCKED: board launch requires root in the same authorized terminal", file=sys.stderr)
        return 4
    if subprocess.run(["sudo", "-n", "true"], check=False).returncode != 0:
        print("BLOCKED: same-terminal sudo -n true failed", file=sys.stderr)
        return 4
    board_env_gate = M175 / "runtime/m120_board_env_preflight.py"
    env_gate_result = Path("/dev/shm/tellme_release_board_env_preflight.json")
    rc = subprocess.run([sys.executable, str(board_env_gate), "--candidate", str(M175),
                         "--expected-package-manifest-sha256",
                         "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f",
                         "--result", str(env_gate_result)], check=False).returncode
    if rc != 0:
        print("BLOCKED: fixed root/XRT/PYNQ/package environment gate failed", file=sys.stderr)
        return 4
    os.environ["PYTHONPATH"] = os.pathsep.join(str(x) for x in module_dirs)
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["M200_STATIC_ROOT"] = str(M254 / "static")
    resolved = required_paths(config)
    os.environ["M254_M243_RESULT"] = str(resolved["m243_result"])
    os.environ["M254_M253_RESULT"] = str(required_paths(config)["m253_result"])
    os.environ["M254_M249_RESULT"] = str(required_paths(config)["m249_result"])
    os.environ["M254_M249_CANDIDATE"] = str(M249)
    argsv = [sys.executable, str(M254 / "m254_video_server.py"), "--candidate", str(M181),
             "--text-candidate", str(M175), "--weights-root", str(resolve(config["weights_root"])),
             "--board-gate", str(resolved["predecessor_summary"]), "--host", str(config["host"]), "--port", str(config["port"])]
    os.execvpe(sys.executable, argsv, os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
