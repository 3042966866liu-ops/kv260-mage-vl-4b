#!/usr/bin/env python3
"""Static stable M254 import audit; never imports device modules."""

import ast
from collections import deque
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "deployment/mage_vl4b"
SEARCH = [D / name for name in (
    "m254_dual_path_web_candidate", "m243_web_prefill_board_candidate",
    "m242_m241_fixed_text_board_candidate", "m238_input_prefetch_board_candidate",
    "m241_grouped_gqa_board_candidate", "m231_parse_reuse_board_candidate",
    "m249_ssdlite_board_candidate", "m246_knife_binary_board_candidate",
)] + [ROOT / x for x in (
    "tmp/m227_runtime_base/m227_runtime_base_patch",
    "tmp/m223_realtime/m223_realtime_delta",
    "tmp/m218_dual_source/m218_dual_source_delta",
)] + [D / "m181_m120_video_board_candidate" / x for x in
      ("text_runtime", "ps_vision_payload", "")] + [D / "m175_m120_fixed_text_candidate" / x for x in
      ("runtime", "runtime/support")]
EXTERNAL = {"numpy", "torch", "torchvision", "tokenizers", "transformers", "safetensors",
            "pynq", "cv2", "PIL", "scipy", "requests", "packaging", "typing_extensions", "tqdm"}


def local(name: str) -> Path | None:
    for directory in SEARCH:
        path = directory / (name + ".py")
        if path.is_file():
            return path
        path = directory / name / "__init__.py"
        if path.is_file():
            return path
    return None


def main() -> int:
    pending = deque(["m254_video_server"])
    seen = set()
    unresolved = set()
    while pending:
        name = pending.popleft()
        if name in seen:
            continue
        source = local(name)
        if source is None:
            unresolved.add(name)
            continue
        seen.add(name)
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [item.name.split(".", 1)[0] for item in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".", 1)[0]]
            else:
                continue
            for child in names:
                if child not in sys.stdlib_module_names and child not in EXTERNAL:
                    pending.append(child)
    print(f"M254_STATIC_PYTHON_CLOSURE local_modules={len(seen)} unresolved={len(unresolved)}")
    for name in sorted(unresolved):
        print("UNRESOLVED", name)
    print("EXTERNAL_RUNTIME_MODULES", ", ".join(sorted(EXTERNAL)))
    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
