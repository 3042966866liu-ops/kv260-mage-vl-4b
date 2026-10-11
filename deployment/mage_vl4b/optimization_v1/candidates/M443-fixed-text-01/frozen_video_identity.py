import ast
import hashlib
import json
from pathlib import Path
VARIANT = "baseline"

ADDON = Path("/home/ubuntu/tellme_release_video_addon_20260926_v3")

RELEASE = Path("/home/ubuntu/tellme_release_install_20260926")

M277_SHA = "0e1bdfa578f655b2bb6d07b097f1dda115a7936906e3e112137123db65e7f2fa"

FRAMES = {
    "frame_00_0068_rgb448.npy": "efbd192266329db17ab9b233b854fa4086a16ccf8faf8aace75462c164844e8f",
    "frame_01_0102_rgb448.npy": "e334ea6bdeb142a42a443afe27fa8af551895d568149ab8aca92a181fdc69243",
    "frame_02_0137_rgb448.npy": "81ddb1f5358e44bf9263c71f1cd64c68e888c5233f0fe8ab017e6011277d9527",
    "frame_03_0171_rgb448.npy": "7bf716a4f68defdb85066a0afeed955c61305628a2f43563b0b14ee539644b13",
}

STACK_SHA = "5911485955780036ac4c8990bcaa248667f2e86bd1fd6f9b0783002553b4adff"

OMITTED_BOUNDARY_DOCS = {
    "M259_BOUNDARY.md", "M260_BOUNDARY.md", "M261_BOUNDARY.md",
    "M269_BOUNDARY.md", "M273_BOUNDARY.md", "M276_BOUNDARY.md",
    "M277_BOUNDARY.md",
}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(4 << 20), b""):
            h.update(part)
    return h.hexdigest()

def module_paths() -> list[Path]:
    d = RELEASE / "deployment/mage_vl4b"
    paths = [
        RELEASE / "runtime_site",
        d / "m277_m276_fixed_window_board_candidate",
        d / "m254_dual_path_web_candidate",
        d / "m243_web_prefill_board_candidate",
        d / "m242_m241_fixed_text_board_candidate",
        d / "m238_input_prefetch_board_candidate",
        d / "m241_grouped_gqa_board_candidate",
        d / "m231_parse_reuse_board_candidate",
        RELEASE / "tmp/m227_runtime_base/m227_runtime_base_patch",
        RELEASE / "tmp/m223_realtime/m223_realtime_delta",
        RELEASE / "tmp/m218_dual_source/m218_dual_source_delta",
        d / "m181_m120_video_board_candidate/text_runtime",
        d / "m181_m120_video_board_candidate/ps_vision_payload",
        d / "m181_m120_video_board_candidate",
        d / "m175_m120_fixed_text_candidate/runtime",
        d / "m175_m120_fixed_text_candidate/runtime/support",
    ]
    if VARIANT == "candidate":
        paths.insert(0, PACKAGE)
    return paths

def verify_m277_release_subset(candidate: Path) -> dict:
    manifest_path = candidate / "PACKAGE_MANIFEST.json"
    if digest(manifest_path) != M277_SHA:
        raise RuntimeError("M277 frozen manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("schema") != "tellme-m277-m276-fixed-window-v1" or
            manifest.get("status") != "PASS_OFFLINE_READY_FOR_M277_BOARD_GATE" or
            manifest.get("file_count") != len(manifest.get("files", []))):
        raise RuntimeError("M277 frozen manifest schema/count mismatch")
    expected = {item["path"]: item for item in manifest["files"]}
    actual = {path.relative_to(candidate).as_posix() for path in candidate.rglob("*")
              if path.is_file() and path.name != "PACKAGE_MANIFEST.json"}
    if set(expected) - actual != OMITTED_BOUNDARY_DOCS or actual - set(expected):
        raise RuntimeError(f"M277 release subset mismatch omitted={sorted(set(expected)-actual)} extra={sorted(actual-set(expected))}")
    for name in sorted(actual):
        item = expected[name]
        path = candidate / name
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise RuntimeError(f"M277 runtime payload hash mismatch: {name}")
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {"manifest_sha256": M277_SHA, "verified_present_files": len(actual),
            "omitted_nonruntime_docs": sorted(OMITTED_BOUNDARY_DOCS)}
