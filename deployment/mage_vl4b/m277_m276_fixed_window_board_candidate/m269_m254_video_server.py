#!/usr/bin/env python3
"""Isolated M254 entry point with M269 multiscale binary 4B review."""

from __future__ import annotations

import m269_video_runtime  # noqa: F401 - installs isolated M269 runtime
import m254_video_server as _m254


if __name__ == "__main__":
    raise SystemExit(_m254._server.main())
