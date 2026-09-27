# Fixed-video reproduction with the prebuilt KV260 release

The conservative release is the v7 prebuilt TAR (`0x4D395832`) plus a small, separately hash-locked four-frame companion archive. The owner confirmed that this motorcycle example was AI-generated and approved its publication; it is not real monitoring footage. The companion uses the original M277 input and frozen gate already exercised on this Build; it does not change weights, bitstream, image preprocessing, frame order, prompt, quantization or output contract. The original v7 TAR remains byte-for-byte immutable. The owner reports both assets uploaded to [GitHub Releases](https://github.com/3042966866liu-ops/kv260-mage-vl-4b/releases), but the base archive's attached manifest must be corrected and the public copies have not yet been rehashed. See the [companion manifest](../manifests/fixed_video_companion_v3.json) for its exact identity.

## Exact inputs and expected result

The companion archive contains the four original `uint8` RGB448 NumPy frames in this order:

1. `frame_00_0068_rgb448.npy`
2. `frame_01_0102_rgb448.npy`
3. `frame_02_0137_rgb448.npy`
4. `frame_03_0171_rgb448.npy`

Their stacked tensor has shape `(4, 448, 448, 3)` and SHA-256 `5911485955780036ac4c8990bcaa248667f2e86bd1fd6f9b0783002553b4adff`. The entry is the published M277 `M276ShortPromptBinaryRuntime.stream` via the companion `run_fixed_video.py`; it submits the complete ordered tensor using the frozen `M276_KNIFE_PROMPT`, `max_new_tokens=1`. The old stable board result expects 159 prompt tokens, selected frame index `[3]`, constrained output text `0`/token ID `15`, knife verdict `ABSENT`, stable Build-ID, 778 logical FPGA language calls and no language CPU Linear fallback. It emits explicit preprocess, vision, prefill, token, knife observation and complete events.

This is a **direct 4B video inference entry**, not an M254 fast-path alarm session. It must never be represented as an alarm-triggered Web semantic review. The four frames are submitted in order, but this historical runtime selects the latest frame for its global/detail views; success does not prove four-frame temporal reasoning. The old M277 result is a reference for the fixed input, not evidence that this independent installation has passed.

## Local owner-board procedure

The first-install v7 tree must be at `/home/ubuntu/tellme_release_install_20260926` with its exact package manifest, isolated wheels installed and no other service using FPGA/port 8001. Install the companion archive into `/home/ubuntu/tellme_release_video_addon_20260926_v3` using the bounded hash-checking receiver, not by overwriting the stable deployment. Check the companion TAR SHA-256 and its `PACKAGE_MANIFEST.json` SHA-256 against `deployment/mage_vl4b/M328_VIDEO_ADDON_BUILD_RESULT_V3.json` in the owner workspace. After `sudo -v` in the same COM3 login and closure/preflight checks, execute:

```sh
sudo -n /usr/local/share/pynq-venv/bin/python3 /home/ubuntu/tellme_release_video_addon_20260926_v3/run_fixed_video.py
```

The entry first checks release identity, root/XRT/PYNQ, M277 runtime source hashes and imports, all four fixture hashes and their ordered tensor hash. Only then does it call the unchanged M277 video runtime. It writes `results/environment.json`, `results/video_forward.log`, `results/m277_fixed_video.json` and an atomic `results/result.json` in the companion directory. A 900-second bounded timeout prevents indefinite FPGA waiting. The gate does not stop or replace a stable service; it refuses if port 8001 is occupied. On any failure, preserve the first exception and complete log and rerun only the failed level.

Publication status is governed by the latest `deployment/mage_vl4b/BOARD_GATE_RESULT.json` in the owner workspace. Do not claim video E2E solely from the v7 no-frame Web readiness test or the historical M277 result.

## Owner-board first-install result (M328, 2026-09-26)

The separately distributed v3 companion archive (SHA-256 `254587ec1f776a01dc12ef98b900a558e4c3087c90a8630a59be51ef12df8b93`) was installed in the independent v7 tree's companion directory and its five payload files passed board-side hashes. The above exact direct entry accepted all four frames in the stated order, completed all 24 vision layers, then ran the stable `0x4D395832` T32 language path for 159 prompt tokens. It emitted 778 expected logical FPGA calls, no language CPU Linear fallback, output text `0` / token ID `15`, and `ABSENT`. First-token latency was `230.721 s` excluding startup; the whole validation runner took `511.854 s` including startup and checks. The output score is uncalibrated. Full authoritative result is `deployment/mage_vl4b/M328_RELEASE_VIDEO_BOARD_RESULT.json` in the owner workspace; raw COM3 log is `tmp/m328_video_gate_uart.log`.

This upgrades **the direct fixed-video 4B first-install gate** from unverified to PASS. It does not change the immutable v7 base archive, prove the Web alarm route, sustained Decode throughput, independent task accuracy or real-time performance. Only the last submitted frame is used for global/detail visual views. The AI-generated companion and base archive were reported uploaded; their public copies have not been independently downloaded and checked. The base archive's third-party attribution and redistribution checks remain separate from the owner's permission for these four frames.
