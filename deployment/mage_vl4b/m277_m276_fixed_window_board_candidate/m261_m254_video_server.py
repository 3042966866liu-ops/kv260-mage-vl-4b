#!/usr/bin/env python3
"""Isolated M254 entry point with M259 plus M261's bounded exact cache."""

from __future__ import annotations

import m261_video_runtime  # noqa: F401 - installs isolated M261 runtime
import m254_video_server as _m254


if __name__ == "__main__":
    raise SystemExit(_m254._server.main())
