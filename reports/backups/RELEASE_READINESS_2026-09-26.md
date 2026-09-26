# Local release readiness — 2026-09-26

This is a **local research-preview staging directory**, not a published GitHub repository. The user's conservative stable board route is the default: M254/M120/T32 Build `0x4D395832`. OP01 Decode-one remains visibly experimental and is not selected by `scripts/run_demo.sh`.

## M0–M4 status

| Milestone | Done in this staging run | Remaining boundary |
| --- | --- | --- |
| M0 inventory | Traced M254→M243/M223 and M181/M175/M249, BACT M321 JSON references, OP01/M325; identified large binaries and module precedence | Dynamic board imports, exact upstream revision/license and complete Vivado assembly are unresolved |
| M1 independent snapshot | Copied original `.py/.sh/.cpp/.hpp/.tcl/.js/.html/.css` and small JSON/contracts without weights or bitstreams; retained active historical `tmp/` dependency paths in Git; relative HLS include closure `missing=0` | Model/hardware assets are external; there is no verified public acquisition procedure |
| M2 first-install adapter/docs | Added root-relative wrapper/config, no-device dry run, hash identity checks, docs, source/asset manifests | New wrapper has not been tested on KV260 and deliberately requires explicit operator acknowledgment |
| M3 lightweight checks | Python syntax + JSON + links + per-file hash scan passed (419 manifested files after this audit); HLS quoted includes `missing=0`; static M254 Python imports resolve 31 local modules with no unresolved names; M321 selector/cost/quality historical recomputation passed from release root with empty `PYTHONPATH`; preflight help/dry-run and expected missing-asset failure checked; Git ignore behavior checked; `bash -n scripts/run_demo.sh` passed in WSL | Actual board module import, full software reference and hardware checks NOT_RUN |
| M4 local delivery | Release notes, GitHub instructions, no-board CI definition and this readiness audit prepared | No remote created, no push, no Release, no board command |

## Capability levels

- `SOURCE_REVIEWABLE`: **YES, with attribution caveat**. Original sources and evidence are inspectable. It does not establish redistribution rights or complete first-install closure.
- `OFFLINE_REPRODUCED`: **YES, narrow scope** for M321 frozen BACT selector, 27 existing board-cost records and 12 historically seen predictions. No new model forward or independent quality test.
- `PREBUILT_READY`: **NO** for a clean user install. The exact M125 language/LM Head layouts and all eight shards were found and rehashed on the owner's WSL host; they match the stable runtime's M120 identities. They are still external to Git, and the other weights/tokenizer/detector/bit/hwh have not been assembled into a rights-cleared first-install bundle. The release launcher remains untested on a clean KV260. See [stable asset provenance](docs/stable_asset_provenance.md).
- `SOURCE_BUILD_VERIFIED`: **NOT_RUN**. HLS source/IP export script exists, but clean full-shell Vivado BD/IP/DMA/clock/address/constraint/package closure has not been established.

## Blocking decisions before **public** GitHub publication

1. Owner must decide and document a project-source license and confirm rights/attribution for derived Mage-VL model code, project-specific code and the small copied evidence/dataset metadata. No `LICENSE` was invented.
2. If claiming prebuilt reproducibility, owner must supply or specify lawful acquisition of **all** exact hash-locked model/hardware assets, including the now-located M125 layouts, and permit a new-board first-install validation. A source-only research preview can be published after rights clearance **without** claiming prebuilt readiness.

Non-blocking for a clearly labeled source-only preview: no new board rerun, no full Vivado rebuild, no independent quality gain, no video binaries, and no performance superiority claim. These remain disclosed, not hidden.

## Rejected or incomplete paths retained honestly

- Decode-one FIFO capacity long test: `STOPPED_BY_USER_NOT_PASS`; OP01 did not outperform stable M254 in M325 same-session comparison; not promoted.
- M321 historical quality: BACT-159 and count-144 did not establish an independent quality advantage; old 12 clips not reused as new test set.
- Prompt rewrites and time-paired views: no net adopted benefit; P0/V0 retained.
- No board root, overlay, boot, DTB, CMA, partitions, stable rollback, or running service were changed by this release staging.

## Next concrete checks

From this release directory: `python3 scripts/check_release.py`, `python3 scripts/m321_reproduce_bact_v2_evidence.py --only all`, and `python3 scripts/preflight.py --dry-run`. After rights/assets are resolved, validate a **separate** clean KV260 install with the fixed same-terminal root/XRT/PYNQ preflight and the project's historical gate order; preserve existing stable rollback. Run `bash -n scripts/run_demo.sh` where Bash is available. Do not treat M321 or syntax checks as board deployment PASS.
