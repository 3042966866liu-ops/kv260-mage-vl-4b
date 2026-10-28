#!/usr/bin/env python3
"""M230 language loop selecting family-many scheduling when available."""

from __future__ import annotations

import numpy as np

from video_language_runtime import M120VideoLanguageModel


class M230VideoLanguageModel(M120VideoLanguageModel):
    """Keep the accepted model math; change only the runtime submission granularity."""

    def _family(self, layer: int, family: str,
                values: np.ndarray) -> dict[str, np.ndarray]:
        if hasattr(self.runtime, "language_family_many"):
            return self.runtime.language_family_many(layer, family, values)
        return super()._family(layer, family, values)

