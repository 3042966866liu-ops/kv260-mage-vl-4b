# Prebuilt KV260 release assets

The stable installation is the hash-locked M327 v7 archive for Build
`0x4D395832`. It was independently installed and exercised on the owner's
KV260. The Git repository alone does not contain its model weights or
bitstream. The owner reports that the eight 500 MB release parts below were
uploaded to [GitHub Releases](https://github.com/3042966866liu-ops/kv260-mage-vl-4b/releases).
The old two-part `RELEASE_PARTS.json` attachment is incompatible and must be
replaced before this Release is usable. Do not substitute similarly named
older v2–v6 archives or mix the 2 GB and 500 MB splits.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part01` | 500,000,000 | `60d7d3c1e7045ee36bb8a452b8c01474cacbdc29199b01ecd1a186efb040be10` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part02` | 500,000,000 | `b7de4ff4f0a71df41397b5737890072f16966ddab86912113c84a53daf7aa0e0` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part03` | 500,000,000 | `61e1c948b652ed570d8f58147212515f9ab4bdd6c9d596e81ffab501b8c32dc1` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part04` | 500,000,000 | `5e5cca1d2edd6af941810aa16ffb97105edc9fc9fe748900414c45aea5bf16ad` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part05` | 500,000,000 | `d94e19be5142b0e9174b99d5109a430c0020068add7dfee9d41287419aa26547` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part06` | 500,000,000 | `35cbc6b16a5f3bacdbe4b0c9a7c96abc1c0eb8238fa59851bb36c1aa5195cfc6` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part07` | 500,000,000 | `fc9b9a1742df21d00a94943406e8f9b346265a67a02b50b53e1bad7cea719651` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part08` | 409,191,680 | `1ecb792ea63f92fd565111c2e8b3528dcede774ed2c4f78d7c9eb70b7beb6a20` |
| Reassembled v7 TAR | 3,909,191,680 | `c487e16bcc18698808d7c48822e355c8b6cf291633b00d661f372f7280d41145` |

GitHub Releases require each individual asset to be under 2 GiB. The first
2 GB split was below that limit but failed in the browser, so the archive was
re-split into smaller upload parts without altering the original TAR. The exact machine
manifest is [`release_parts_v7.json`](../manifests/release_parts_v7.json).
The upload source is the owner's local `release_staging/distribution_v7_500mb/`
directory; it is not a reader download path. The owner's report of uploaded
assets is not a download-and-reassembly check of the GitHub copies.

Download all eight parts into one host directory. The Release's existing
two-part `RELEASE_PARTS.json` is stale: **do not use it**. Until its attachment
is replaced, copy this repository's [corrected eight-part manifest](../manifests/release_parts_v7.json)
into the download directory as `RELEASE_PARTS.json`. After replacement, the
Release copy is usable only if it lists eight parts and `part_bytes_limit` is
`500000000`. Verify every part and the combined stream before assembling.
The verifier refuses a missing, altered, or repeated part. It does not
contact a board or run a model.

```sh
# Run from the cloned repository root; keep all eight downloaded parts together.
cp manifests/release_parts_v7.json /path/to/downloads/RELEASE_PARTS.json
python3 scripts/release_parts.py verify /path/to/downloads/RELEASE_PARTS.json
python3 scripts/release_parts.py assemble /path/to/downloads/RELEASE_PARTS.json /path/to/kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar
```

Once the Release attachment has been replaced and checked, its corrected
`RELEASE_PARTS.json` can be used in place of the copied repository manifest:

```sh
python3 scripts/release_parts.py verify /path/to/RELEASE_PARTS.json
python3 scripts/release_parts.py assemble /path/to/RELEASE_PARTS.json /path/to/kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar
```

The Release must provide the corrected `RELEASE_PARTS.json` alongside all eight
parts; the same manifest is versioned in this repository. The `assemble`
command refuses to overwrite an existing output and checks the complete TAR
SHA-256 before finalizing it. It requires roughly another 3.9 GB of host disk
space. Do not assemble on a nearly full KV260 microSD.

The v7 TAR contains no video, still image fixture, or monitoring footage. The
historical M328 fixed-video entry needs a separate four-frame companion. The
owner confirmed these four motorcycle frames are AI-generated and approved
their publication. The companion is prepared locally as
`m328_release_video_addon_20260926_v3.tar` (2,437,120 bytes, SHA-256
`254587ec1f776a01dc12ef98b900a558e4c3087c90a8630a59be51ef12df8b93`),
with its [machine manifest](../manifests/fixed_video_companion_v3.json). It
was also reported uploaded to the Release. No real monitoring video is part of this
distribution. The v7 TAR by itself supports the fixed-text and runtime-start
checks, **not** recreation of the recorded fixed-video result. See
[fixed-video reproduction](fixed_video_reproduction.md).

After extraction into a new board directory, follow [quickstart](quickstart.md)
for exact package-file verification, isolated wheel installation, environment
preflight and the staged FPGA gates. The validated first-install archive
is tied to the recorded PYNQ/XRT/Ubuntu environment; a clean generic KV260 OS
image has not been proven equivalent. The stable deployment and rollback must
remain untouched.

Public availability does not resolve the file-level third-party attribution and
redistribution checks described in [provenance](provenance.md). A successful
SHA-256 check or owner permission to publish project files does not grant
rights over third-party components.
