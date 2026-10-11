#!/usr/bin/env python3
"""Read-only verifier for embedded-data U-Boot FIT images.

The script validates the FDT container, enumerates FIT images/configurations,
and recomputes every supported hash subnode without extracting or modifying the
source file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import struct
import sys
import zlib
from pathlib import Path


FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


def align4(value: int) -> int:
    return (value + 3) & ~3


def c_string(blob: mmap.mmap, offset: int, limit: int) -> str:
    end = blob.find(b"\0", offset, limit)
    if end < 0:
        raise ValueError(f"unterminated string at offset {offset}")
    return blob[offset:end].decode("ascii", errors="strict")


def decode_text(value: bytes) -> str:
    return value.rstrip(b"\0").decode("utf-8", errors="replace")


def digest_range(blob: mmap.mmap, offset: int, length: int, algorithm: str) -> bytes:
    algorithm = algorithm.lower()
    if algorithm in {"sha1", "sha256", "sha384", "sha512", "md5"}:
        digest = hashlib.new(algorithm)
        end = offset + length
        for start in range(offset, end, 4 * 1024 * 1024):
            digest.update(blob[start : min(start + 4 * 1024 * 1024, end)])
        return digest.digest()
    if algorithm == "crc32":
        crc = 0
        end = offset + length
        for start in range(offset, end, 4 * 1024 * 1024):
            crc = zlib.crc32(blob[start : min(start + 4 * 1024 * 1024, end)], crc)
        return (crc & 0xFFFFFFFF).to_bytes(4, "big")
    raise ValueError(f"unsupported FIT hash algorithm: {algorithm}")


def verify_fit(path: Path) -> dict[str, object]:
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as blob:
        if len(blob) < 40:
            raise ValueError("file is shorter than the FDT header")
        header = struct.unpack_from(">10I", blob, 0)
        (
            magic,
            total_size,
            struct_offset,
            strings_offset,
            reserve_offset,
            version,
            last_compatible_version,
            boot_cpu,
            strings_size,
            struct_size,
        ) = header
        if magic != FDT_MAGIC:
            raise ValueError(f"bad FDT magic 0x{magic:08x}")
        if total_size != len(blob):
            raise ValueError(f"FDT total size {total_size} != file size {len(blob)}")
        for name, offset, size in (
            ("structure", struct_offset, struct_size),
            ("strings", strings_offset, strings_size),
        ):
            if offset > total_size or size > total_size - offset:
                raise ValueError(f"{name} block is out of bounds")
        if reserve_offset >= total_size:
            raise ValueError("reserve map offset is out of bounds")

        structure_end = struct_offset + struct_size
        strings_end = strings_offset + strings_size
        cursor = struct_offset
        stack: list[str] = []
        properties: dict[str, dict[str, tuple[int, int]]] = {}
        saw_end = False

        while cursor + 4 <= structure_end:
            token = struct.unpack_from(">I", blob, cursor)[0]
            cursor += 4
            if token == FDT_BEGIN_NODE:
                name = c_string(blob, cursor, structure_end)
                cursor = align4(cursor + len(name.encode("ascii")) + 1)
                stack.append(name)
            elif token == FDT_END_NODE:
                if not stack:
                    raise ValueError("unbalanced FDT_END_NODE")
                stack.pop()
            elif token == FDT_PROP:
                if cursor + 8 > structure_end:
                    raise ValueError("truncated FDT property header")
                length, name_offset = struct.unpack_from(">II", blob, cursor)
                cursor += 8
                if name_offset >= strings_size:
                    raise ValueError("FDT property name offset is out of bounds")
                name = c_string(blob, strings_offset + name_offset, strings_end)
                if length > structure_end - cursor:
                    raise ValueError(f"property {name} is out of bounds")
                node_path = "/" + "/".join(part for part in stack if part)
                properties.setdefault(node_path, {})[name] = (cursor, length)
                cursor = align4(cursor + length)
            elif token == FDT_NOP:
                continue
            elif token == FDT_END:
                saw_end = True
                break
            else:
                raise ValueError(f"unknown FDT token 0x{token:08x} at 0x{cursor - 4:x}")

        if not saw_end:
            raise ValueError("missing FDT_END token")
        if stack:
            raise ValueError("unterminated FDT node stack")

        def prop_bytes(node: str, name: str) -> bytes | None:
            record = properties.get(node, {}).get(name)
            if record is None:
                return None
            offset, length = record
            return blob[offset : offset + length]

        image_nodes = sorted(
            node for node in properties if node.startswith("/images/") and node.count("/") == 2
        )
        hash_nodes = sorted(
            node
            for node in properties
            if node.startswith("/images/")
            and node.count("/") == 3
            and node.rsplit("/", 1)[1].startswith("hash")
        )
        images: list[dict[str, object]] = []
        image_by_path: dict[str, dict[str, object]] = {}
        for node in image_nodes:
            data_record = properties[node].get("data")
            item: dict[str, object] = {
                "name": node.rsplit("/", 1)[1],
                "description": decode_text(prop_bytes(node, "description") or b""),
                "type": decode_text(prop_bytes(node, "type") or b""),
                "arch": decode_text(prop_bytes(node, "arch") or b""),
                "os": decode_text(prop_bytes(node, "os") or b""),
                "compression": decode_text(prop_bytes(node, "compression") or b""),
                "embedded_data": data_record is not None,
                "data_size": data_record[1] if data_record else None,
                "hashes": [],
            }
            images.append(item)
            image_by_path[node] = item

        hash_failures: list[str] = []
        supported_hashes = 0
        for node in hash_nodes:
            parent = node.rsplit("/", 1)[0]
            image = image_by_path.get(parent)
            if image is None:
                hash_failures.append(f"hash node without image parent: {node}")
                continue
            algorithm = decode_text(prop_bytes(node, "algo") or b"")
            expected = prop_bytes(node, "value")
            data_record = properties[parent].get("data")
            record: dict[str, object] = {
                "node": node.rsplit("/", 1)[1],
                "algorithm": algorithm,
                "expected": expected.hex() if expected is not None else None,
                "actual": None,
                "verified": False,
            }
            if data_record is None:
                hash_failures.append(f"external or missing data is unsupported: {parent}")
            elif expected is None:
                hash_failures.append(f"missing expected hash value: {node}")
            else:
                try:
                    actual = digest_range(blob, data_record[0], data_record[1], algorithm)
                    record["actual"] = actual.hex()
                    record["verified"] = actual == expected
                    supported_hashes += 1
                    if actual != expected:
                        hash_failures.append(f"hash mismatch: {node}")
                except ValueError as exc:
                    hash_failures.append(f"{node}: {exc}")
            image["hashes"].append(record)

        configurations: list[dict[str, object]] = []
        configuration_names = {node.rsplit("/", 1)[1] for node in properties if node.startswith("/configurations/") and node.count("/") == 2}
        image_names = {str(item["name"]) for item in images}
        bad_references: list[str] = []
        for name in sorted(configuration_names):
            node = f"/configurations/{name}"
            references: dict[str, str] = {}
            for key in ("kernel", "fdt", "ramdisk", "firmware", "loadables"):
                value = prop_bytes(node, key)
                if value:
                    decoded = decode_text(value).split("\0")[0]
                    references[key] = decoded
                    if decoded and decoded not in image_names:
                        bad_references.append(f"{name}:{key}->{decoded}")
            configurations.append(
                {
                    "name": name,
                    "description": decode_text(prop_bytes(node, "description") or b""),
                    "references": references,
                }
            )

        default_config = decode_text(prop_bytes("/configurations", "default") or b"")
        if default_config and default_config not in configuration_names:
            bad_references.append(f"default->{default_config}")

        verified_hashes = sum(
            1 for image in images for item in image["hashes"] if item.get("verified") is True
        )
        status = "PASS" if images and supported_hashes and not hash_failures and not bad_references else "FAIL"
        return {
            "gate": "uboot-fit-embedded-hash-verification",
            "status": status,
            "path": str(path),
            "file_size": len(blob),
            "container": {
                "magic": f"0x{magic:08x}",
                "version": version,
                "last_compatible_version": last_compatible_version,
                "boot_cpu": boot_cpu,
                "structure_size": struct_size,
                "strings_size": strings_size,
                "end_token_present": saw_end,
            },
            "image_count": len(images),
            "configuration_count": len(configurations),
            "default_configuration": default_config,
            "verified_hash_count": verified_hashes,
            "hash_failures": hash_failures,
            "bad_references": bad_references,
            "images": images,
            "configurations": configurations,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fit", type=Path)
    args = parser.parse_args()
    try:
        result = verify_fit(args.fit)
    except Exception as exc:  # fail closed and keep the error machine-readable
        result = {
            "gate": "uboot-fit-embedded-hash-verification",
            "status": "FAIL",
            "path": str(args.fit),
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
