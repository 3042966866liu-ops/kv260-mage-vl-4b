#!/usr/bin/env python3
"""Re-use the completed M325 fixed-text gate after a video-only callback fix."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def load(path: Path):
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.result.exists():
        raise RuntimeError("refuse overwrite")
    stable, stable_sha = load(args.prior / "text_stable.json")
    candidate, candidate_sha = load(args.prior / "text_candidate.json")
    if stable["status"] != "PASS_REFERENCE" or stable["build_id"] != "0x4D395832":
        raise RuntimeError("prior stable text gate not valid")
    if (candidate["status"] != "PASS_EXPERIMENTAL" or
            candidate["build_id"] != "0x4F503131" or
            candidate["stable_reference_exact"] is not True):
        raise RuntimeError("prior candidate text gate not valid")
    for key in ("prompt_tokens", "generated_tokens", "token_ids", "logits_sha256",
                "final_kv_sha256", "logical_fpga_calls"):
        if stable[key] != candidate[key]:
            raise RuntimeError("prior text gate mismatch: " + key)
    if stable["prompt_tokens"] != 10 or stable["generated_tokens"] != 1:
        raise RuntimeError("prior text geometry changed")
    result = {"gate": "M325-reused-fixed-text", "status": "PASS_REUSED",
              "stable_result_sha256": stable_sha, "candidate_result_sha256": candidate_sha,
              "source": str(args.prior), "reason": "only M273 progress callback changed"}
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("M325_REUSED_FIXED_TEXT_PASS " + json.dumps(result, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
