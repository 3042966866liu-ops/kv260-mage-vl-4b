#!/usr/bin/env python3
"""Small offline contract test for release_parts.py."""

from pathlib import Path
from tempfile import TemporaryDirectory

from release_parts import assemble, split, verify


def main() -> None:
    with TemporaryDirectory(prefix="kv260-release-parts-") as temporary:
        root = Path(temporary)
        source = root / "sample.bin"
        payload = bytes(range(256)) * 4 + b"tail"
        source.write_bytes(payload)
        manifest = split(source, root / "parts", 257)
        checked = verify(manifest)
        assert len(checked["parts"]) == 4
        output = root / "reassembled.bin"
        assemble(manifest, output)
        assert output.read_bytes() == payload
        first = manifest.parent / checked["parts"][0]["file"]
        with first.open("r+b") as stream:
            stream.seek(0)
            stream.write(b"X")
        try:
            verify(manifest)
        except ValueError as error:
            assert "part mismatch" in str(error)
        else:
            raise AssertionError("corrupted part was not rejected")
    print("RELEASE_PARTS_CONTRACT_PASS")


if __name__ == "__main__":
    main()
