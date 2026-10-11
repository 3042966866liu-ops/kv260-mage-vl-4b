#!/usr/bin/env python3
"""Host-only proof for the M19 anonymous tied-embedding residency gate."""

from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment/qwen25_3b_directddr_chain/runtime"))
sys.path.insert(0, str(ROOT / "deployment/qwen25_3b_no_final_forward/runtime"))

import resident_chain_runtime as runtime_module  # noqa: E402
from resident_chain_runtime import EMBEDDING_NAME, QwenResidentRuntime  # noqa: E402


class FakeMapping:
    def __init__(self) -> None:
        self.advice: list[int] = []
        self.closed = False

    def madvise(self, advice: int) -> None:
        self.advice.append(advice)

    def close(self) -> None:
        self.closed = True


class FakeEmbedding:
    def __init__(self, values: np.ndarray, mapping: FakeMapping) -> None:
        self.values = values
        self._mmap = mapping
        self.shape = values.shape
        self.dtype = values.dtype
        self.nbytes = values.nbytes

    def __array__(self, dtype=None, copy=None) -> np.ndarray:
        array = np.asarray(self.values, dtype=dtype)
        return array.copy() if copy else array


def make_runtime(root: Path, *, expected_sha: str, cma_after: int, mem_after: int):
    values = np.arange(48, dtype=np.dtype("<f2")).reshape(12, 4)
    blob = root / "aux.bin"
    blob.write_bytes(values.tobytes())
    mapping = FakeMapping()
    source = FakeEmbedding(values, mapping)
    runtime = QwenResidentRuntime.__new__(QwenResidentRuntime)
    runtime.aux_blob = blob
    runtime.index = {
        "aux_tensors": [
            {
                "name": EMBEDDING_NAME,
                "offset": 0,
                "bytes": int(values.nbytes),
                "shape": list(values.shape),
                "sha256": expected_sha,
            }
        ]
    }
    runtime.embedding = source
    runtime.aux = {EMBEDDING_NAME: source}
    meminfo = {
        "CmaFree": iter((700_000, cma_after)),
        "Cached": iter((800_000, 100_000)),
        "MemAvailable": iter((1_500_000, mem_after)),
    }
    runtime._meminfo_kib = lambda name: next(meminfo[name])
    return runtime, values, mapping


def main() -> int:
    runtime_module.os.POSIX_FADV_DONTNEED = 4
    runtime_module.os.posix_fadvise = lambda *_args: None
    runtime_module.mmap.MADV_DONTNEED = 4

    with tempfile.TemporaryDirectory(prefix="tellme-m19-embedding-") as raw:
        root = Path(raw)
        expected = np.arange(48, dtype=np.dtype("<f2")).reshape(12, 4)
        expected_sha = hashlib.sha256(expected.tobytes()).hexdigest()

        runtime, values, mapping = make_runtime(
            root, expected_sha=expected_sha, cma_after=600_000, mem_after=900_000
        )
        result = runtime._materialize_tied_embedding()
        assert result["status"] == "PASS"
        assert result["actual_sha256"] == expected_sha
        assert result["actual_sha256"] == result["expected_sha256"]
        assert result["file_backed"] is False
        assert result["owns_memory"] is True
        assert result["c_contiguous"] is True
        assert runtime.embedding is runtime.aux[EMBEDDING_NAME]
        assert isinstance(runtime.embedding, np.ndarray)
        assert not isinstance(runtime.embedding, np.memmap)
        assert np.array_equal(runtime.embedding, values)
        assert mapping.advice and mapping.closed

        bad_root = root / "bad-sha"
        bad_root.mkdir()
        failed, _, failed_mapping = make_runtime(
            bad_root, expected_sha="0" * 64, cma_after=600_000, mem_after=900_000
        )
        try:
            failed._materialize_tied_embedding()
        except RuntimeError as exc:
            assert "SHA mismatch" in str(exc)
        else:
            raise AssertionError("corrupt resident embedding was accepted")
        assert failed_mapping.closed is False

        low_root = root / "low-memory"
        low_root.mkdir()
        low, _, low_mapping = make_runtime(
            low_root, expected_sha=expected_sha, cma_after=127_000, mem_after=900_000
        )
        try:
            low._materialize_tied_embedding()
        except RuntimeError as exc:
            assert "insufficient memory" in str(exc)
        else:
            raise AssertionError("embedding residency accepted less than 128 MiB CMA")
        assert low_mapping.closed is True

    print("QWEN_RESIDENT_TIED_EMBEDDING_UNIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
