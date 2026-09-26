#!/usr/bin/env python3
"""Memory-bounded high-precision-activation M90 visual runtime for Cortex-A53.

The accepted M63 accuracy route keeps visual activations on the PS and uses
the exact M56 W4 weights without A8 activation quantization.  Packed weights
are decoded one Linear at a time, so the 660 MiB dequantized vision tower is
never resident.  This module intentionally does not use the rejected M62
visual-A8 FPGA path.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import mmap
import sys
import types
from pathlib import Path

import numpy as np

try:
    import torch as _torch
except ImportError:  # The constructor below emits the board-facing error.
    _torch = None


GROUP_SIZE = 64
ROW_BLOCK = 8


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve(root, dotted: str):
    value = root
    for part in dotted.split("."):
        value = getattr(value, part)
    return value


def _parent(root, dotted: str):
    parts = dotted.split(".")
    return _resolve(root, ".".join(parts[:-1])) if len(parts) > 1 else root, parts[-1]


class FourPortW4Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        manifest_path = self.root / "SIXPORT_LAYOUT_MANIFEST.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if self.manifest.get("format") != "tellme-mage-vl-fourport-group-major-v1":
            raise RuntimeError("M90 visual four-port format mismatch")
        if int(self.manifest["parameters"]["shard_count"]) != 4:
            raise RuntimeError("M90 visual layout is not four-port")
        if int(self.manifest["parameters"]["group_size"]) != GROUP_SIZE:
            raise RuntimeError("M90 visual group size mismatch")
        if len(self.manifest.get("modules", [])) != 98:
            raise RuntimeError("M90 visual layout must contain 98 Linears")
        self.entries = {}
        self.handles = []
        self.maps = []
        for item in self.manifest["files"]:
            path = self.root / item["path"]
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M90 visual shard identity failed: {path.name}")
            handle = path.open("rb")
            self.handles.append(handle)
            self.maps.append(mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ))
        for entry in self.manifest["modules"]:
            short = entry["module"][len("model.visual.") :]
            if short in self.entries:
                raise RuntimeError(f"duplicate M90 visual module: {short}")
            if int(entry["bits"]) != 4:
                raise RuntimeError(f"M90 accepted visual route expects W4: {short}")
            self.entries[short] = entry

    @staticmethod
    def _unpack_w4(payload: bytes) -> np.ndarray:
        packed = np.frombuffer(payload, dtype=np.uint8)
        result = np.empty(packed.size * 2, dtype=np.int16)
        result[0::2] = packed & 0x0F
        result[1::2] = packed >> 4
        return result

    def decode(self, name: str) -> np.ndarray:
        entry = self.entries[name]
        rows, columns = map(int, entry["shape"])
        groups = int(entry["input_groups"])
        codes = np.zeros((rows, groups, GROUP_SIZE), dtype=np.int16)
        scales = np.zeros((rows, groups), dtype=np.float32)
        qmins = np.full((rows, groups), -8, dtype=np.int16)
        code_bytes = GROUP_SIZE // 2
        for tile in entry["tiles"]:
            row_start = int(tile["row_start"])
            valid_end = min(rows, row_start + int(tile["valid_rows"]))
            rows_per_shard = int(tile["rows_per_shard"])
            expected = groups * (rows_per_shard // ROW_BLOCK) * 272
            if int(tile["record_bytes_per_shard"]) != expected:
                raise RuntimeError(f"M90 record geometry mismatch: {name}")
            for shard, mapping in enumerate(self.maps):
                cursor = int(tile["shard_offsets"][shard])
                shard_base = row_start + shard * rows_per_shard
                for group in range(groups):
                    for block in range(rows_per_shard // ROW_BLOCK):
                        tagged = np.frombuffer(mapping[cursor:cursor + 16], dtype="<u2").copy()
                        cursor += 16
                        lane_codes = []
                        for _pair in range(4):
                            pair = mapping[cursor:cursor + 2 * code_bytes]
                            cursor += 2 * code_bytes
                            lane_codes.append(self._unpack_w4(pair[:code_bytes]))
                            lane_codes.append(self._unpack_w4(pair[code_bytes:]))
                        for lane in range(ROW_BLOCK):
                            row = shard_base + block * ROW_BLOCK + lane
                            if row >= valid_end or row >= rows:
                                continue
                            scale_bits = np.asarray([tagged[lane] & 0x7FFF], dtype=np.uint16)
                            scales[row, group] = scale_bits.view(np.float16).astype(np.float32)[0]
                            qmins[row, group] = -7 if tagged[lane] & 0x8000 else -8
                            codes[row, group] = lane_codes[lane]
        restored = (codes + qmins[..., None]).astype(np.float32)
        restored *= scales[..., None]
        return restored.reshape(rows, groups * GROUP_SIZE)[:, :columns]

    def close(self) -> None:
        for mapping in self.maps:
            mapping.close()
        for handle in self.handles:
            handle.close()
        self.maps.clear()
        self.handles.clear()


_TorchModule = _torch.nn.Module if _torch is not None else object


class M90LazyW4Linear(_TorchModule):
    """A torch module whose only large tensor exists during one forward call."""

    def __init__(self, torch, store: FourPortW4Store, name: str, in_features: int,
                 out_features: int, has_bias: bool, compute_dtype):
        super().__init__()
        self.store = store
        self.name = name
        self.in_features = int(in_features)
        self.out_features = int(out_features)
        self.compute_dtype = compute_dtype
        if has_bias:
            self.bias = torch.nn.Parameter(torch.empty(out_features, device="meta"), requires_grad=False)
        else:
            self.register_parameter("bias", None)

    def forward(self, values):
        import torch
        weight = torch.from_numpy(self.store.decode(self.name)).to(self.compute_dtype)
        bias = self.bias.to(self.compute_dtype) if self.bias is not None else None
        return torch.nn.functional.linear(values.to(self.compute_dtype), weight, bias)


class M90PSVisionRuntime:
    def __init__(self, model_code_root: Path, layout_root: Path, raw_manifest_path: Path,
                 compute: str = "bf16"):
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("M90 PS vision requires an aarch64 PyTorch installation") from exc
        self.torch = torch
        if compute != "bf16":
            raise ValueError("the accepted M90/M63 visual route is BF16 only")
        self.compute_dtype = torch.bfloat16
        self.store = FourPortW4Store(layout_root)
        code_root = Path(model_code_root).resolve()
        package_name = "tellme_m90_ps_vision"
        package = types.ModuleType(package_name)
        package.__path__ = [str(code_root)]  # type: ignore[attr-defined]
        sys.modules[package_name] = package
        configuration = importlib.import_module(f"{package_name}.configuration_mage_vl")
        modeling = importlib.import_module(f"{package_name}.modeling_mage_vl")
        config = configuration.MageVLConfig.from_pretrained(code_root, local_files_only=True)
        with torch.device("meta"):
            vision = modeling.MageVLVisionPretrainedModel(config.vision_config)
        named = dict(vision.named_modules())
        if set(self.store.entries) - set(named):
            raise RuntimeError("M90 packed visual modules do not match official model code")
        for name, entry in self.store.entries.items():
            old = named[name]
            replacement = M90LazyW4Linear(
                torch, self.store, name, int(entry["shape"][1]), int(entry["shape"][0]),
                getattr(old, "bias", None) is not None, self.compute_dtype,
            )
            parent, leaf = _parent(vision, name)
            setattr(parent, leaf, replacement)
        # Materialize only the remaining raw parameters/buffers; the 98 large
        # Linear weights have already been replaced by lazy modules.
        vision.to_empty(device="cpu")

        raw_manifest_path = Path(raw_manifest_path)
        raw = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
        blob_path = raw_manifest_path.parent / raw["blob"]["path"]
        if raw.get("entry_count") != 199 or blob_path.stat().st_size != int(raw["blob"]["bytes"]):
            raise RuntimeError("M90 raw visual auxiliary geometry mismatch")
        if sha256(blob_path) != raw["blob"]["sha256"]:
            raise RuntimeError("M90 raw visual auxiliary identity failed")
        payload = blob_path.read_bytes()
        loaded = set()
        for item in raw["entries"]:
            short = item["name"][len("model.visual.") :]
            parent, leaf = _parent(vision, short)
            begin, size = int(item["offset"]), int(item["bytes"])
            bits = np.frombuffer(payload[begin:begin + size], dtype="<u2").copy()
            tensor = torch.from_numpy((bits.astype(np.uint32) << 16).view(np.float32).copy())
            tensor = tensor.reshape(tuple(int(v) for v in item["shape"])).to(self.compute_dtype)
            if leaf not in parent._parameters:
                raise RuntimeError(f"M90 raw tensor is not an official parameter: {short}")
            parent._parameters[leaf] = torch.nn.Parameter(tensor, requires_grad=False)
            loaded.add(short)
        if len(loaded) != 199:
            raise RuntimeError("M90 raw visual parameter count mismatch")

        # ``to_empty`` cannot initialize non-persistent rotary buffers.  Restore
        # the deterministic frequencies from the official module attributes.
        for module in vision.modules():
            if all(hasattr(module, name) for name in ("inv_freq_t", "inv_freq_h", "inv_freq_w", "base")):
                module.inv_freq_t = (1.0 / (module.base ** (
                    torch.arange(module.t_size, dtype=torch.float32) / module.t_size))).to(self.compute_dtype)
                module.inv_freq_h = (1.0 / (module.base ** (
                    torch.arange(module.h_size, dtype=torch.float32) / module.h_size))).to(self.compute_dtype)
                module.inv_freq_w = (1.0 / (module.base ** (
                    torch.arange(module.w_size, dtype=torch.float32) / module.w_size))).to(self.compute_dtype)
        meta = [name for name, parameter in vision.named_parameters() if parameter.is_meta]
        if meta:
            raise RuntimeError(f"M90 visual model retains meta parameters: {meta[:4]}")
        self.vision = vision.eval()

    def __call__(self, pixel_values: np.ndarray, image_grid_thw: np.ndarray,
                 patch_positions: np.ndarray) -> np.ndarray:
        torch = self.torch
        pixels = torch.from_numpy(np.asarray(pixel_values, dtype=np.float32)).to(self.compute_dtype)
        grid = torch.from_numpy(np.asarray(image_grid_thw, dtype=np.int64))
        positions = torch.from_numpy(np.asarray(patch_positions, dtype=np.int64))
        with torch.inference_mode():
            output = self.vision(pixels, grid_thw=grid, patch_positions=positions).last_hidden_state
        if list(output.shape) != [784, 2560] or not torch.isfinite(output).all():
            raise RuntimeError(f"M90 PS visual output gate failed: {list(output.shape)}")
        return output.float().cpu().numpy()

    def close(self) -> None:
        self.store.close()
