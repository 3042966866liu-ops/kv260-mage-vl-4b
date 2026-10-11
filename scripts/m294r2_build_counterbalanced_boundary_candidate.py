#!/usr/bin/env python3
"""Build M294R2 without overwriting either rejected M294 package."""

from __future__ import annotations

import m294_build_counterbalanced_boundary_candidate as base


base.DEST = base.DEPLOYMENT / "m294r2_counterbalanced_boundary_board_candidate"
base.PARTIAL = base.DEST.with_name(base.DEST.name + ".partial")
base.ARCHIVE = base.DEPLOYMENT / "m294r2_counterbalanced_boundary_board_candidate.tar.gz"
base.BUILD_RESULT = base.DEPLOYMENT / "M294R2_COUNTERBALANCED_BOUNDARY_BUILD_RESULT.json"


if __name__ == "__main__":
    raise SystemExit(base.main())
