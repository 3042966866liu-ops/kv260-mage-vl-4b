# Stable M120/T32 layout asset provenance (2026-09-26)

Scope: read-only identity audit for the conservative M254/M120/T32 Build ID `0x4D395832`. No board connection, service stop, overlay load, model inference, weight rewrite, or bitstream build was performed. This is **not** a fresh-board installation test.

## Required identity and its origin

The stable video runtime (`deployment/mage_vl4b/m181_m120_video_board_candidate/video_server.py`) and M126 runtime contracts lock the following `SIXPORT_LAYOUT_MANIFEST.json` hashes. M125's exact-layout build result (`deployment/mage_vl4b/M125_EXACT_FOURPORT_LAYOUT_RESULT.json`) names the original WSL source directories and eight shard hashes. The historical KV260 G00 inventory (`deployment/mage_vl4b/optimization_v1/gates/G00-model-inventory/attempt_01/board_raw.json`) independently recorded these layout hashes and shard byte counts on the board. That G00 result was overall FAIL due to a later missing Python dependency; its successful layout identity check must not be relabeled as a complete gate PASS.

| Asset | Expected and observed manifest SHA-256 | Original local source | Payload |
| --- | --- | --- | ---: |
| Language | `12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d` | `/home/lyy/artifacts/tellme-mage-vl/m125-m120-fourport-layouts-v1/language_fourport/` | 4 × 457,209,856 bytes |
| LM Head | `a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef` | `/home/lyy/artifacts/tellme-mage-vl/m125-m120-fourport-layouts-v1/lmhead_fourport/` | 4 × 51,658,240 bytes |

On 2026-09-26, `sha256sum` of both WSL manifests and all eight WSL shards matched M125's recorded values; see the per-file hashes and separate installation destinations in [`external_assets.json`](../manifests/external_assets.json). Their frozen source checkpoint is `/home/lyy/artifacts/tellme-mage-vl/m120-text4b-mixed-w3e-w4h-w4mlpkv-v2/`: its `CHECKPOINT_MANIFEST.json` SHA-256 is `5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0`, and `weights.bin` SHA-256 is `9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d`. Both source files were also rehashed on this date and matched M125's provenance.

## Why nearby older files were rejected

The read-only [`compare_layout_manifests.py`](../scripts/compare_layout_manifests.py) comparison found:

| Compared with M125 | Manifest SHA-256 | Structural observation | Decision |
| --- | --- | --- | --- |
| M89Y language | `b7cafc930326179091aa32d666395331f27d5518d01758ef01e71b31ed70ac26` | Same 252 module names and 648 tiles, but 42 module bit-width changes, 251 tile/offset-record changes, and every shard has a different size and hash; M89Y derives from M56 rather than the frozen M120 checkpoint. | Different actual layout and payload; cannot substitute. |
| M89Z LM Head | `0fbaaebc102c4deece9945c98d1dc719a4102929ca4db79077175af32a571b28` | LM Head bit-width, tile data, shard sizes and hashes differ. | Different layout and payload; cannot substitute. |
| M89Z2 W4 LM Head | `3a028f5d5f579142e5003243d6200de2e447a8acb2ef97f30ab7809d2f29e253` | Same module shape, bit-width and tile fields as M125, but all four equal-sized shard hashes differ; provenance is the older M89Z/M56 branch. | Not merely JSON formatting; payload identity differs, so cannot substitute. |

The shared layout-format parameters (`shard_count=4`, `group_size=64`, row block and alignment) do not establish weight equivalence. A differing SHA-256 alone would not establish the reason for the difference; the structural and shard comparison above does.

## Release boundary

Correct M125 assets are now located on the owner's WSL host, so the previous claim “not found locally” is closed. They remain **external** to this Git/source snapshot. No large weight or bitstream was copied into Git, no public download URL or redistribution right was inferred, and the new first-install wrapper has not been tried on a clean KV260. To install separately, the owner must provision these exact two directories at `external_assets/weights/{language_fourport,lmhead_fourport}/`, verify the manifest and every shard against `external_assets.json`, then provision the other listed assets and run the documented fail-closed preflight. Never rename M89Y/M89Z or relax the expected hashes to get a PASS.

The source-only preview can be completed after license/attribution review without claiming `PREBUILT_READY` or a clean full-shell source rebuild. No historical board PASS/FAIL was altered by this audit.
