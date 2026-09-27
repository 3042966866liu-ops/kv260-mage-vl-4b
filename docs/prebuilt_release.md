# Prebuilt KV260 release assets

The stable installation is the hash-locked M327 v7 archive for Build
`0x4D395832`. It was independently installed and exercised on the owner's
KV260. The Git repository alone does not contain its model weights or
bitstream. The two release parts below are **prepared locally, not yet
published**. Do not substitute similarly named older v2–v6 archives.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part01` | 2,000,000,000 | `dd112211cefbe2972ad952581a902b17f3b9b648b4acd83e3973f6dd2e23276a` |
| `kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar.part02` | 1,909,191,680 | `279b7f26b279e3a54777541a66922b72a52beb5af33c486f863c056a79607b63` |
| Reassembled v7 TAR | 3,909,191,680 | `c487e16bcc18698808d7c48822e355c8b6cf291633b00d661f372f7280d41145` |

GitHub Releases require each individual asset to be under 2 GiB, so the
archive was split without altering the original TAR. The exact machine
manifest is [`release_parts_v7.json`](../manifests/release_parts_v7.json).
The prepared parts are in the owner's local
`release_staging/distribution_v7/` directory; this path is **not** a public
download URL. Once a Release is actually uploaded and checked, replace this
paragraph with its real tag and links.

Download both parts into one directory. Verify every part and the combined
stream before assembling. The verifier refuses a missing, altered, or repeated
part. It does not contact a board or run a model.

```sh
python3 scripts/release_parts.py verify /path/to/RELEASE_PARTS.json
python3 scripts/release_parts.py assemble /path/to/RELEASE_PARTS.json /path/to/kv260-mage-vl-4b-prebuilt-install-20260926-v7.tar
```

The published Release must provide `RELEASE_PARTS.json` alongside the two
parts; the same manifest is versioned in this repository. The `assemble`
command refuses to overwrite an existing output and checks the complete TAR
SHA-256 before finalizing it. It requires roughly another 3.9 GB of host disk
space. Do not assemble on a nearly full KV260 microSD.

The v7 TAR contains no video, still image fixture, or monitoring footage. The
historical M328 fixed-video entry needs a separate four-frame companion. Its
input rights and publication status are tracked independently; the v7 TAR by
itself supports the fixed-text and runtime-start checks, **not** recreation
of the recorded fixed-video result. See [fixed-video reproduction](fixed_video_reproduction.md).

After extraction into a new board directory, follow [quickstart](quickstart.md)
for exact package-file verification, isolated wheel installation, environment
preflight and the staged FPGA gates. The validated first-install archive
is tied to the recorded PYNQ/XRT/Ubuntu environment; a clean generic KV260 OS
image has not been proven equivalent. The stable deployment and rollback must
remain untouched.

Public upload still requires file-level third-party attribution and
redistribution checks described in [provenance](provenance.md). A successful
SHA-256 check or owner permission to publish project files does not grant
rights over third-party components.
