#!/usr/bin/env python3
"""Collect raw M120+A8 logits for the frozen BACT four-baseline pilot.

The collector intentionally has no label-file argument.  It reads only source
identity fields from the M296 manifest and never reads filename hints.  Atomic
per-clip progress allows a stopped run to resume without repeating completed
model forwards under a changed identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time


M120_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
M120_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
BASELINE_IDS = {
    "fixed_high_quality": "high-284",
    "fixed_ratio_visual_pruning": "ratio-164",
    "token_count_aware": "count-144",
    "bact": "bact-159",
}
BASELINE_ORDER = tuple(BASELINE_IDS)
ACTION_NAMES = ("WORKING", "IDLE", "WALKING", "FALLING", "FIGHTING")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".partial-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_inventory(workspace: Path, manifest: dict) -> list[dict]:
    if manifest.get("schema") != "tellme-bact-target-scene-v1":
        raise ValueError("M307 unsupported source manifest schema")
    clips = manifest.get("clips")
    if not isinstance(clips, list) or len(clips) != 12:
        raise ValueError("M307 requires exactly 12 frozen source clips")
    inbox = (workspace / "data/bact_target_scene/inbox").resolve()
    rows = []
    seen_ids = set()
    seen_hashes = set()
    for clip in clips:
        # Deliberately whitelist only source identity fields.  In particular,
        # filename_hints and annotation_status are never consumed here.
        clip_id = str(clip["clip_id"])
        split = str(clip["split"])
        filename = str(clip["source_filename"])
        expected_hash = str(clip["video_sha256"]).lower()
        if clip_id in seen_ids:
            raise ValueError(f"M307 duplicate clip ID: {clip_id}")
        if split not in {"calibration", "test"}:
            raise ValueError(f"M307 unsupported split: {clip_id}/{split}")
        if Path(filename).name != filename or not filename.lower().endswith(".mp4"):
            raise ValueError(f"M307 unsafe source filename: {filename}")
        path = (inbox / filename).resolve()
        if path.parent != inbox or not path.is_file():
            raise ValueError(f"M307 source file missing: {filename}")
        observed_hash = sha256(path)
        if observed_hash != expected_hash:
            raise ValueError(f"M307 source hash mismatch: {filename}")
        if observed_hash in seen_hashes:
            raise ValueError(f"M307 duplicate source hash: {filename}")
        seen_ids.add(clip_id)
        seen_hashes.add(observed_hash)
        rows.append(
            {
                "clipId": clip_id,
                "split": split,
                "sourceFilename": filename,
                "videoSha256": observed_hash,
                "path": path,
            }
        )
    if sum(row["split"] == "calibration" for row in rows) != 6:
        raise ValueError("M307 calibration source count must be 6")
    if sum(row["split"] == "test" for row in rows) != 6:
        raise ValueError("M307 test source count must be 6")
    return rows


def validate_geometry(geometry: dict) -> dict[str, dict]:
    if geometry.get("schema") != "tellme-bact-four-baseline-prediction-geometry-v1":
        raise ValueError("M307 unsupported geometry schema")
    if geometry.get("status") != "PASS_EXACT_GEOMETRY_AND_TASK_TOKEN_CONTRACT":
        raise ValueError("M307 geometry gate is not PASS")
    if geometry.get("baselineIds") != BASELINE_IDS:
        raise ValueError("M307 baseline identity mismatch")
    candidates = geometry.get("candidates")
    if not isinstance(candidates, dict) or set(candidates) != set(BASELINE_IDS):
        raise ValueError("M307 geometry must contain exactly four baselines")
    for name, candidate_id in BASELINE_IDS.items():
        candidate = candidates[name]
        if candidate.get("candidateId") != candidate_id:
            raise ValueError(f"M307 candidate mismatch: {name}")
        if candidate.get("knifePromptTokens") != candidate.get("targetPromptTokensPerProbe"):
            raise ValueError(f"M307 knife geometry mismatch: {name}")
        if candidate.get("actionPromptUsesNeutralPadding") is not False:
            raise ValueError(f"M307 action probe must not use neutral padding: {name}")
        if candidate.get("boardTimingClaimAllowed") is not False:
            raise ValueError(f"M307 offline action probe cannot claim board timing: {name}")
    return candidates


def session_identity(
    *,
    collector_sha256: str,
    manifest_sha256: str,
    geometry_sha256: str,
    model_config_sha256: str,
    checkpoint_manifest_sha256: str,
    checkpoint_blob_sha256: str,
) -> dict:
    return {
        "collectorSha256": collector_sha256,
        "sourceManifestSha256": manifest_sha256,
        "geometrySha256": geometry_sha256,
        "modelConfigSha256": model_config_sha256,
        "checkpointManifestSha256": checkpoint_manifest_sha256,
        "checkpointBlobSha256": checkpoint_blob_sha256,
    }


def load_or_initialize_progress(path: Path, identity: dict) -> dict:
    if path.is_file():
        progress = load_json(path)
        if progress.get("schema") != "tellme-bact-four-baseline-progress-v1":
            raise ValueError("M307 progress schema mismatch")
        if progress.get("sessionIdentity") != identity:
            raise ValueError("M307 progress identity mismatch; do not mix runs")
        if not isinstance(progress.get("completed"), dict):
            raise ValueError("M307 progress records are invalid")
        return progress
    return {
        "schema": "tellme-bact-four-baseline-progress-v1",
        "sessionIdentity": identity,
        "completed": {},
    }


def assemble_predictions(
    inventory: list[dict], candidates: dict[str, dict], completed: dict
) -> dict:
    expected_keys = {
        f"{name}/{row['clipId']}" for name in BASELINE_ORDER for row in inventory
    }
    if set(completed) != expected_keys:
        missing = sorted(expected_keys - set(completed))
        extra = sorted(set(completed) - expected_keys)
        raise ValueError(f"M307 incomplete predictions missing={missing} extra={extra}")
    baselines = {}
    for name in BASELINE_ORDER:
        records = []
        for source in inventory:
            raw = completed[f"{name}/{source['clipId']}"]
            if raw.get("candidateId") != BASELINE_IDS[name]:
                raise ValueError(f"M307 completed candidate mismatch: {name}")
            knife_score = float(raw["knifeScore"])
            action_logits = {
                action: float(raw["actionLogits"][action]) for action in ACTION_NAMES
            }
            if not math.isfinite(knife_score) or not all(
                math.isfinite(value) for value in action_logits.values()
            ):
                raise ValueError(f"M307 non-finite completed logits: {name}/{source['clipId']}")
            records.append(
                {
                    "clipId": source["clipId"],
                    "knifeScore": knife_score,
                    "actionLogits": action_logits,
                    "evidence": {
                        "videoSha256": source["videoSha256"],
                        "knifePromptTokens": raw["knifePromptTokens"],
                        "actionPromptTokens": raw["actionPromptTokens"],
                        "knifeForwardMs": raw["knifeForwardMs"],
                        "actionForwardMs": raw["actionForwardMs"],
                        "finite": raw["finite"],
                    },
                }
            )
        baselines[name] = {
            "candidateId": candidates[name]["candidateId"],
            "predictions": records,
        }
    return {
        "schema": "tellme-bact-four-baseline-predictions-v1",
        "baselines": baselines,
    }


def prepare(processor, views, prompt: str):
    from PIL import Image

    images = [Image.fromarray(frame, mode="RGB") for frame in views]
    messages = [
        {
            "role": "user",
            "content": [{"type": "video"}, {"type": "text", "text": prompt}],
        }
    ]
    rendered = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return processor(
        text=[rendered], videos=[images], return_tensors="pt", padding=True
    )


def run_probe(torch, model, processor, views, prompt: str) -> tuple[object, int, float]:
    inputs = prepare(processor, views, prompt)
    observed_tokens = int(inputs["input_ids"].shape[1])
    started = time.perf_counter()
    with torch.inference_mode():
        output = model(**inputs, use_cache=False)
    forward_ms = (time.perf_counter() - started) * 1000.0
    logits = output.logits[0, -1].to(dtype=torch.float32, device="cpu").contiguous()
    return logits, observed_tokens, forward_ms


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=20)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = workspace / "deployment/mage_vl4b"
    manifest_path = args.manifest.resolve()
    geometry_path = args.geometry.resolve()
    model_path = args.model.resolve()
    checkpoint = args.checkpoint.resolve()
    checkpoint_manifest = checkpoint / "CHECKPOINT_MANIFEST.json"

    manifest = load_json(manifest_path)
    geometry = load_json(geometry_path)
    inventory = source_inventory(workspace, manifest)
    candidates = validate_geometry(geometry)
    if sha256(checkpoint_manifest) != M120_MANIFEST_SHA256:
        raise RuntimeError("M307 M120 manifest hash mismatch")
    checkpoint_json = load_json(checkpoint_manifest)
    if checkpoint_json.get("blob", {}).get("sha256") != M120_BLOB_SHA256:
        raise RuntimeError("M307 M120 blob declaration mismatch")
    model_config = model_path / "config.json"
    identity = session_identity(
        collector_sha256=sha256(Path(__file__).resolve()),
        manifest_sha256=sha256(manifest_path),
        geometry_sha256=sha256(geometry_path),
        model_config_sha256=sha256(model_config),
        checkpoint_manifest_sha256=M120_MANIFEST_SHA256,
        checkpoint_blob_sha256=M120_BLOB_SHA256,
    )
    progress = load_or_initialize_progress(args.progress.resolve(), identity)
    expected_count = len(inventory) * len(BASELINE_ORDER)
    print(
        f"M307_SOURCE_PREFLIGHT_PASS clips={len(inventory)} unique=12 "
        f"completed={len(progress['completed'])}/{expected_count}",
        flush=True,
    )

    sys.path[:0] = [
        str(workspace),
        str(workspace / "scripts"),
        str(root / "scripts"),
        str(root / "m273_latest_binary_source"),
    ]
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor
    from m264_gpu_resolution_semantic_suite import load_two_video_frames
    from m266_gpu_multiscale_semantic_gate import multiscale_views
    from mage_a8_runtime import install_packed_linear_a8_hooks
    from packed_checkpoint_artifact import load_packed_checkpoint

    torch.set_num_threads(args.threads)
    handles = []
    started = time.perf_counter()
    try:
        processor = AutoProcessor.from_pretrained(
            model_path, trust_remote_code=True, local_files_only=True
        )
        print("M307_MODEL_SHELL_LOAD_BEGIN", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            attn_implementation="eager",
            device_map={"": "cpu"},
        ).eval()
        print("M307_M120_RECONSTRUCTION_BEGIN", flush=True)
        reload_info = load_packed_checkpoint(
            torch, model, checkpoint, verify_blob=True, row_chunk=32
        )
        handles, hook_names = install_packed_linear_a8_hooks(
            torch, model, checkpoint, r"^(model\.language_model\.layers\.|lm_head$)"
        )
        if len(hook_names) != 253:
            raise RuntimeError(f"M307 A8 hook closure mismatch {len(hook_names)}")

        for clip_index, source in enumerate(inventory, start=1):
            frames = load_two_video_frames(source["path"])
            all_views = multiscale_views(frames)
            for baseline_index, name in enumerate(BASELINE_ORDER, start=1):
                key = f"{name}/{source['clipId']}"
                if key in progress["completed"]:
                    print(f"M307_RESUME_SKIP key={key}", flush=True)
                    continue
                candidate = candidates[name]
                views = all_views[candidate["viewIndices"]]
                print(
                    f"M307_PROBE_BEGIN clip={clip_index}/12 baseline={baseline_index}/4 "
                    f"id={candidate['candidateId']}",
                    flush=True,
                )
                knife_logits, knife_tokens, knife_ms = run_probe(
                    torch, model, processor, views, candidate["knifePrompt"]
                )
                action_logits_full, action_tokens, action_ms = run_probe(
                    torch, model, processor, views, candidate["actionPrompt"]
                )
                if knife_tokens != candidate["knifePromptTokens"]:
                    raise RuntimeError(f"M307 knife token drift: {key}")
                if action_tokens != candidate["actionPromptTokens"]:
                    raise RuntimeError(f"M307 action token drift: {key}")
                no_id = int(geometry["knifeTokenIds"]["no"])
                yes_id = int(geometry["knifeTokenIds"]["yes"])
                knife_score = float(knife_logits[yes_id] - knife_logits[no_id])
                action_logits = {
                    action: float(action_logits_full[int(geometry["actionTokenIds"][action])])
                    for action in ACTION_NAMES
                }
                finite = bool(torch.isfinite(knife_logits).all().item()) and bool(
                    torch.isfinite(action_logits_full).all().item()
                )
                if not finite or not math.isfinite(knife_score) or not all(
                    math.isfinite(value) for value in action_logits.values()
                ):
                    raise RuntimeError(f"M307 non-finite logits: {key}")
                progress["completed"][key] = {
                    "candidateId": candidate["candidateId"],
                    "clipId": source["clipId"],
                    "videoSha256": source["videoSha256"],
                    "knifeScore": knife_score,
                    "actionLogits": action_logits,
                    "knifePromptTokens": knife_tokens,
                    "actionPromptTokens": action_tokens,
                    "knifeForwardMs": knife_ms,
                    "actionForwardMs": action_ms,
                    "finite": finite,
                }
                atomic_json(args.progress.resolve(), progress)
                print(
                    f"M307_PROBE_PASS key={key} completed={len(progress['completed'])}/{expected_count} "
                    f"knife_ms={knife_ms:.3f} action_ms={action_ms:.3f}",
                    flush=True,
                )

        predictions = assemble_predictions(inventory, candidates, progress["completed"])
        predictions.update(
            {
                "date": "2026-09-03",
                "classification": (
                    "Raw exact-M120+A8 software logits over 12 source-unique AI-generated pilot clips; "
                    "no labels were read and no accuracy, KV260 timing, power or real-world validity is claimed."
                ),
                "sessionIdentity": identity,
                "sourceManifest": str(manifest_path.relative_to(workspace)).replace("\\", "/"),
                "geometry": str(geometry_path.relative_to(workspace)).replace("\\", "/"),
                "humanLabelsRead": False,
                "filenameHintsRead": False,
                "heldOutLabelsRead": False,
                "model": "microsoft/Mage-VL",
                "backend": "WSL CPU exact reconstructed M120 weights plus 253 A8-G64 hooks",
            }
        )
        atomic_json(args.predictions.resolve(), predictions)
        result = {
            "date": "2026-09-03",
            "gate": "M307-four-baseline-raw-prediction-collection",
            "status": "PASS_RAW_PREDICTIONS_LABEL_BLIND",
            "classification": predictions["classification"],
            "clipCount": len(inventory),
            "baselineCount": len(BASELINE_ORDER),
            "completedPredictionRows": expected_count,
            "modelForwardCount": expected_count * 2,
            "allFinite": True,
            "predictions": str(args.predictions.resolve().relative_to(workspace)).replace("\\", "/"),
            "predictionsSha256": sha256(args.predictions.resolve()),
            "progress": str(args.progress.resolve().relative_to(workspace)).replace("\\", "/"),
            "progressSha256": sha256(args.progress.resolve()),
            "sourceManifestSha256": identity["sourceManifestSha256"],
            "geometrySha256": identity["geometrySha256"],
            "checkpoint": reload_info,
            "a8HookCount": len(hook_names),
            "humanLabelsRead": False,
            "filenameHintsRead": False,
            "heldOutLabelsRead": False,
            "formalAccuracyAllowed": False,
            "boardExecutionRun": False,
            "activeM254M256Changed": False,
            "bootDtbCmaPartitionsChanged": False,
            "stableRollbackPreserved": True,
            "wallMs": (time.perf_counter() - started) * 1000.0,
            "nextGate": (
                "After M304 freezes 12/12 human labels, freeze each knife threshold on calibration only "
                "and run the one-shot held-out M305 evaluator."
            ),
        }
        atomic_json(args.result.resolve(), result)
        print(
            f"M307_RAW_PREDICTIONS_PASS rows={expected_count} "
            f"sha256={result['predictionsSha256']}",
            flush=True,
        )
        return 0
    finally:
        for handle in reversed(handles):
            handle.remove()


if __name__ == "__main__":
    raise SystemExit(main())
