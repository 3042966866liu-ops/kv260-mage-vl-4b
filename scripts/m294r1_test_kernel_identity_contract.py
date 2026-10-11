#!/usr/bin/env python3
"""Regression for the M294R1 loaded-overlay kernel identity contract."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m294_counterbalanced_boundary_source"
sys.path.insert(0, str(SOURCE))

from m294_kernel_identity import require_loaded_kernel


class FakeOverlay:
    def __init__(self, names):
        self.ip_dict = {name: {} for name in names}


class FakeBoard:
    def __init__(self, names, *, has_kernel=True):
        self.overlay = FakeOverlay(names)
        if has_kernel:
            self.kernel = object()


def require_failure(board) -> None:
    try:
        require_loaded_kernel(board, "mage_m120_m89x2_0")
    except RuntimeError:
        return
    raise RuntimeError("M294R1 kernel identity negative branch did not fail")


def main() -> int:
    exact = require_loaded_kernel(
        FakeBoard(["mage_m120_m89x2_0", "axi_dma_prefill"]), "mage_m120_m89x2_0"
    )
    if exact != "mage_m120_m89x2_0":
        raise RuntimeError("M294R1 exact kernel identity mismatch")
    hierarchical = require_loaded_kernel(
        FakeBoard(["design/mage_m120_m89x2_0"]), "mage_m120_m89x2_0"
    )
    if hierarchical != "design/mage_m120_m89x2_0":
        raise RuntimeError("M294R1 hierarchical kernel identity mismatch")
    require_failure(FakeBoard(["wrong_kernel"]))
    require_failure(FakeBoard(["mage_m120_m89x2_0", "design/mage_m120_m89x2_0"]))
    require_failure(FakeBoard(["mage_m120_m89x2_0"], has_kernel=False))
    print("M294R1_KERNEL_IDENTITY_CONTRACT_PASS exact=true hierarchical=true fail_closed=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
