#!/usr/bin/env python3
"""Isolated M254 entry point with M259 two-keyframe semantic review."""

from __future__ import annotations

import m259_video_runtime  # noqa: F401 - installs isolated M259 runtime
import m254_video_server as _m254


if __name__ == "__main__":
    raise SystemExit(_m254._server.main())
