# Source map and dependency audit

Most copied files retain their original workspace-relative path and are byte-identical. `manifests/release_files.json` records per-file origin and SHA-256. The following top-level groups explain roles; no original deployment files were edited.

| Released path | Original path | Role/status |
| --- | --- | --- |
| `deployment/mage_vl4b/m254_dual_path_web_candidate/` | same | Stable Web controller/static files |
| `deployment/mage_vl4b/m243_web_prefill_board_candidate/`, `m242_m241_fixed_text_board_candidate/`, `m238_input_prefetch_board_candidate/`, `m241_grouped_gqa_board_candidate/`, `m231_parse_reuse_board_candidate/` | same | Stable Prefill module precedence |
| `deployment/mage_vl4b/m181_m120_video_board_candidate/`, `m175_m120_fixed_text_candidate/`, `m246_knife_binary_board_candidate/`, `m249_ssdlite_board_candidate/` | same | Model adapters/board contracts/fast path; large binaries external |
| `tmp/m218_dual_source/`, `tmp/m223_realtime/`, `tmp/m227_runtime_base/` | same | **Active historical runtime dependencies**, deliberately tracked, not ignored |
| `hls/mage_prefill_m89x_runtime/` | same | Stable T32 HLS source and test Tcl |
| `hls/mage_prefill_m89s_scaleaware/`, `mage_prefill_m89d_t32_microtile/`, `mage_prefill_m89o_shared15/`, `mage_prefill_m89n_t32_w2w4/`, `mage_prefill_m89h_t32_chunkedpacked/`, `mage_prefill_m89e_t32_packedaccum/` and other sibling HLS modules | same | Recursive quoted-include closure, source-level check only |
| `bact/`, `deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/`, `scripts/m321_reproduce_bact_v2_evidence.py` | same | Offline BACT and fixed-video research path, not Web default |
| `deployment/mage_vl4b/optimization_v1/candidates/OP01-decode-one-ab-01/`, `hls/mage_decode_op01_one/`, `scripts/m325*` | same | Unpromoted experimental path |
| `model_tools/m125...`, `m126...`, `m148...`, `m153...` | corresponding parent `scripts/` files | Byte-identical moved copies, partial conversion chain |
| `scripts/preflight.py`, `scripts/run_demo.sh`, `configs/`, release docs/manifests | none | New release-only wrapper and description, not historical board evidence |

M321's frozen JSON references were followed to include `scripts/m313_gate_bact_v2_selector.py`, M297, M306, labels, predictions and paired result. The BACT reproduction actually passes from this directory. Static M254 Python import traversal resolves 31 local modules with no unresolved local names, using the documented precedence and an external-package allowlist. Python imports in the stable service use PYTHONPATH/module override and a delayed `board_runtime` import; static closure and path existence do not prove first-install runtime closure. Historical `PACKAGE_MANIFEST.json` lists binary payloads deliberately excluded from Git. Dynamic filesystem references and board environment variables remain release installation constraints.

The original M254 controller has a `/home/ubuntu/tellme_m120_m89x2_20260901` fallback for predecessor paths; the new wrapper provides release-rooted `M254_M243_RESULT`, `M254_M253_RESULT`, `M254_M249_RESULT`, `M254_M249_CANDIDATE`, and `M200_STATIC_ROOT`, so that fallback should not be used by this entry. The original M223 runtime receives `--candidate`, `--text-candidate`, `--weights-root`, `--board-gate`, `--host`, and `--port` from the wrapper. No original gate was relaxed or rewritten. A path scan found 27 copied historical source/evidence files with `/home/ubuntu`-style board paths; none of the new release entry/config files contain personal absolute paths. These copied historical gate scripts are not promoted to installation commands. A broad board summary containing an ephemeral public-tunnel address was excluded from the release copy; specific M325/M300/M314 evidence remains. No original file was deleted.
