#!/usr/bin/env python3
"""Regression test for the M294 stage destination-prefix contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "deployment/mage_vl4b/m294_counterbalanced_boundary_source/m294_stage_archive.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("m294_stage_archive", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load stage module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    accepted = {
        "m294_counterbalanced_boundary_candidate",
        "m294r1_counterbalanced_boundary_candidate",
        "m294r2_counterbalanced_boundary_candidate",
        "m294r29_counterbalanced_boundary_candidate",
    }
    for prefix in accepted:
        destination = module.FIXED_PARENT / f"{prefix}_03"
        argv = [
            "m294_stage_archive.py",
            "--archive",
            "/does/not/matter",
            "--archive-sha256",
            "0" * 64,
            "--destination",
            str(destination),
            "--destination-prefix",
            prefix,
            "--manifest-sha256",
            "0" * 64,
        ]
        with mock.patch("sys.argv", argv), mock.patch.object(
            module, "sha256", side_effect=RuntimeError("PREFIX_ACCEPTED")
        ):
            try:
                module.main()
            except RuntimeError as exc:
                if str(exc) != "PREFIX_ACCEPTED":
                    raise
            else:
                raise RuntimeError(f"prefix was not exercised: {prefix}")
    rejected = module.FIXED_PARENT / "unexpected_candidate_03"
    argv = [
        "m294_stage_archive.py",
        "--archive",
        "/does/not/matter",
        "--archive-sha256",
        "0" * 64,
        "--destination",
        str(rejected),
        "--destination-prefix",
        "unexpected_candidate",
        "--manifest-sha256",
        "0" * 64,
    ]
    with mock.patch("sys.argv", argv):
        try:
            module.main()
        except RuntimeError as exc:
            if "destination/prefix mismatch" not in str(exc):
                raise
        else:
            raise RuntimeError("unapproved prefix was accepted")
    print("M294R2_STAGE_PREFIX_CONTRACT_PASS accepted=4 rejected=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
