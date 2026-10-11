#!/usr/bin/env python3
"""Compare one real M89-X1 fixed-text run with all 144 quantized CPU sketches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


LAYERS = 36
FAMILIES = ("qkv", "attention_out", "gate_up", "mlp_down")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def compare_sketch(values: np.ndarray, golden: dict) -> dict[str, object]:
    observed = np.asarray(values, dtype=np.float32)
    if list(observed.shape) != golden["shape"]:
        raise RuntimeError(f"family input shape mismatch {observed.shape} != {golden['shape']}")
    if not np.isfinite(observed).all():
        raise FloatingPointError("non-finite family input")
    flat = observed.reshape(-1)
    indices = np.asarray(golden["sample_indices"], dtype=np.int64)
    reference = np.asarray(golden["sample_values"], dtype=np.float64)
    sampled = flat[indices].astype(np.float64)
    delta = sampled - reference
    ref_norm = max(float(np.linalg.norm(reference)), 1.0e-12)
    obs_norm = max(float(np.linalg.norm(sampled)), 1.0e-12)
    full64 = flat.astype(np.float64)
    return {
        "shape": list(observed.shape),
        "finite": True,
        "sample_count": int(indices.size),
        "sample_max_abs": float(np.max(np.abs(delta))),
        "sample_mean_abs": float(np.mean(np.abs(delta))),
        "sample_rmse": float(np.sqrt(np.mean(delta * delta))),
        "sample_relative_l2": float(np.linalg.norm(delta) / ref_norm),
        "sample_cosine": float(np.vdot(sampled, reference) / (obs_norm * ref_norm)),
        "observed_minimum": float(np.min(flat)),
        "observed_maximum": float(np.max(flat)),
        "observed_mean": float(np.mean(full64)),
        "observed_rms": float(np.sqrt(np.mean(full64 * full64))),
        "observed_l2": float(np.linalg.norm(full64)),
        "golden_minimum": float(golden["minimum"]),
        "golden_maximum": float(golden["maximum"]),
        "golden_mean": float(golden["mean"]),
        "golden_rms": float(golden["rms"]),
        "golden_l2": float(golden["l2"]),
    }


class SketchingRuntime:
    def __init__(self, delegate, golden: dict[str, dict]):
        self.delegate = delegate
        self.golden = golden
        self.metrics: dict[str, dict[str, object]] = {}

    def language_family(self, layer: int, family: str, values: np.ndarray):
        logical = f"layer{int(layer):02d}_{family}"
        if logical in self.metrics:
            raise RuntimeError(f"duplicate family dispatch: {logical}")
        if logical not in self.golden:
            raise RuntimeError(f"missing quantized CPU sketch: {logical}")
        self.metrics[logical] = compare_sketch(values, self.golden[logical])
        return self.delegate.language_family(layer, family, values)

    def lm_head(self, values: np.ndarray):
        return self.delegate.lm_head(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-package-manifest-sha256", required=True)
    parser.add_argument("--golden-sketch", type=Path, required=True)
    parser.add_argument("--expected-golden-sketch-sha256", required=True)
    parser.add_argument("--quantized-reference", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    root = args.candidate.resolve()
    sys.path.insert(0, str(root / "runtime"))
    from board_runtime import BUILD_ID, M89XBoardRuntime
    from text_e2e_gate import FixedTextModel

    began = time.monotonic()
    result: dict[str, object] = {
        "gate": "M89-X1-fixed-text-all-layer-quantized-CPU-differential",
        "status": "FAIL",
        "classification": "same-level fixed-text board diagnostic; not an acceptance threshold or Web gate",
    }
    runtime = None
    auxiliary_npz = None
    try:
        manifest_path = root / "PACKAGE_MANIFEST.json"
        if sha256(manifest_path) != args.expected_package_manifest_sha256:
            raise RuntimeError("candidate package manifest hash mismatch")
        if sha256(args.golden_sketch) != args.expected_golden_sketch_sha256:
            raise RuntimeError("all-layer golden sketch hash mismatch")
        sketch = json.loads(args.golden_sketch.read_text(encoding="utf-8"))
        if sketch.get("status") != "PASS" or int(sketch.get("tensor_count", -1)) != 144:
            raise RuntimeError("all-layer golden sketch identity failed")
        quantized_reference = json.loads(args.quantized_reference.read_text(encoding="utf-8"))
        if quantized_reference.get("status") != "MEASURED":
            raise RuntimeError("quantized CPU reference is not MEASURED")
        expected_token = int(quantized_reference["quantized_cpu_token_id"])

        aux_manifest_path = root / "auxiliary/M77_TEXT_AUX_MANIFEST.json"
        auxiliary_path = root / "auxiliary/m77_text_aux_fp16.npz"
        official_path = root / "auxiliary/official_cpu_text_1token.json"
        aux_manifest = json.loads(aux_manifest_path.read_text(encoding="utf-8"))
        if aux_manifest.get("result") != "PASS" or sha256(auxiliary_path) != aux_manifest.get("payload_sha256"):
            raise RuntimeError("candidate auxiliary identity failed")
        official = json.loads(official_path.read_text(encoding="utf-8"))
        token_ids = [int(value) for value in official["prompt_token_ids"]]
        if len(token_ids) != 30:
            raise RuntimeError("fixed prompt geometry changed")

        auxiliary_npz = np.load(auxiliary_path, allow_pickle=False)
        auxiliary = {name: auxiliary_npz[name] for name in auxiliary_npz.files}
        language_root = Path("/home/ubuntu/tellme_m89x_upload/m89y_language_fourport")
        head_root = Path("/home/ubuntu/tellme_m89x_upload/m89z2_lmhead_w4_fourport")
        runtime = M89XBoardRuntime(
            root / "overlay/m89x_t32.bit",
            language_root,
            head_root,
            root / "contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json",
            root / "contracts/M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
            "staged-low-cma",
        )
        tracing = SketchingRuntime(runtime, sketch["tensors"])
        model = FixedTextModel(
            tracing,
            auxiliary,
            [int(value) for value in aux_manifest["selected_embedding_ids"]],
        )
        generated, logits, layer_ms = model.run(token_ids)
        expected_keys = {
            f"layer{layer:02d}_{family}" for layer in range(LAYERS) for family in FAMILIES
        }
        if set(tracing.metrics) != expected_keys:
            raise RuntimeError("board all-layer family trace is incomplete")

        evidence = runtime.evidence()
        expected_calls = 152
        expected_macros = (
            runtime.language_contract.payload["contract"]["total_expected_macros"]
            + runtime.head_contract.payload["total_expected_macros"]
        )
        hardware_identity = (
            evidence.get("build_id") == f"0x{BUILD_ID:08x}"
            and int(evidence.get("logical_calls", -1)) == expected_calls
            and int(evidence.get("logical_expected_macros", -1)) == expected_macros
        )
        result.update(
            status="MEASURED",
            generated_token_id=generated,
            quantized_cpu_expected_token_id=expected_token,
            quantized_token_match=generated == expected_token,
            official_bf16_token_id=int(official["generated_token_ids"][0]),
            family_count=len(tracing.metrics),
            expected_family_count=144,
            all_family_inputs_finite=all(item["finite"] for item in tracing.metrics.values()),
            family_input_metrics=tracing.metrics,
            evidence=evidence,
            hardware_identity_pass=hardware_identity,
            expected_calls=expected_calls,
            expected_macros=expected_macros,
            timing={
                "layer_ms": layer_ms,
                "language_ms": float(sum(layer_ms)),
                "total_ms": (time.monotonic() - began) * 1000.0,
                "argmax_logit": float(logits[generated]),
            },
            acceptance_note=(
                "No threshold is inferred here. Review the complete 144-family sampled metrics, "
                "then freeze one global family-aware threshold set before rerunning an acceptance gate."
            ),
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if runtime is not None:
            runtime.close()
        if auxiliary_npz is not None:
            auxiliary_npz.close()
        result["total_ms"] = (time.monotonic() - began) * 1000.0
        args.result.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.result.with_suffix(args.result.suffix + ".tmp")
        temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, args.result)
        print(json.dumps(result, indent=2), flush=True)
    marker = (
        "M89X1_ALL_LAYER_QUANTIZED_DIAGNOSTIC_MEASURED"
        if result["status"] == "MEASURED"
        else "M89X1_ALL_LAYER_QUANTIZED_DIAGNOSTIC_FAIL"
    )
    print(marker, flush=True)
    return 0 if result["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
