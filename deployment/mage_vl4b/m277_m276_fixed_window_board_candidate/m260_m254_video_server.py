#!/usr/bin/env python3
"""Isolated M254 entry point with M259 plus M260 exact repeated-window cache."""

from __future__ import annotations

import m260_video_runtime  # noqa: F401 - installs isolated M260 runtime
import m254_video_server as _m254


if __name__ == "__main__":
    raise SystemExit(_m254._server.main())
