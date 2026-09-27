"""Inspect license metadata in the release's nested offline wheel bundle.

This is a metadata inventory, not a legal conclusion. It does not extract wheels.
"""

from __future__ import annotations

import argparse
import email
import io
import json
import tarfile
import zipfile
from pathlib import Path


def inspect(bundle: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with tarfile.open(bundle, "r:") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith(".whl"):
                continue
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"missing wheel member: {member.name}")
            with zipfile.ZipFile(io.BytesIO(source.read())) as wheel:
                members = wheel.namelist()
                metadata_path = next(
                    (name for name in members if name.endswith(".dist-info/METADATA")),
                    None,
                )
                if metadata_path is None:
                    raise RuntimeError(f"missing METADATA: {member.name}")
                metadata = email.message_from_bytes(wheel.read(metadata_path))
                license_files = [
                    name
                    for name in members
                    if "/licenses/" in name.lower()
                    or name.lower().endswith(
                        ("license", "license.txt", "license.md", "copying")
                    )
                ]
                rows.append(
                    {
                        "wheel": Path(member.name).name,
                        "name": metadata.get("Name"),
                        "version": metadata.get("Version"),
                        "license_expression": metadata.get("License-Expression"),
                        "license": metadata.get("License"),
                        "license_classifiers": [
                            value
                            for value in metadata.get_all("Classifier", [])
                            if value.startswith("License ::")
                        ],
                        "license_files": license_files,
                    }
                )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    rows = inspect(args.bundle)
    if args.summary:
        rows = [
            {
                "name": row["name"],
                "version": row["version"],
                "license_expression": row["license_expression"],
                "license": (str(row["license"] or "").splitlines() or [""])[0][:120],
                "license_classifiers": row["license_classifiers"],
                "license_file_count": len(row["license_files"]),
            }
            for row in rows
        ]
    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
