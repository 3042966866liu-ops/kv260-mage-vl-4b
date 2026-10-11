#!/usr/bin/env python3
"""Build M294R1 without overwriting the rejected M294 attempt-01 package."""

from __future__ import annotations

import m294_build_counterbalanced_boundary_candidate as base


base.DEST = base.DEPLOYMENT / "m294r1_counterbalanced_boundary_board_candidate"
base.PARTIAL = base.DEST.with_name(base.DEST.name + ".partial")
base.ARCHIVE = base.DEPLOYMENT / "m294r1_counterbalanced_boundary_board_candidate.tar.gz"
base.BUILD_RESULT = base.DEPLOYMENT / "M294R1_COUNTERBALANCED_BOUNDARY_BUILD_RESULT.json"


if __name__ == "__main__":
    raise SystemExit(base.main())
