# Quickstart

## No board (checked release path)

From the repository root, use Python 3.10+:

```sh
python3 scripts/preflight.py --help
python3 scripts/preflight.py --dry-run --config configs/deployment.example.json
python3 scripts/m321_reproduce_bact_v2_evidence.py --only all
python3 scripts/check_release.py
```

The dry run reports missing model/hardware assets and does not import PYNQ, read weights, bind a port, or touch a board. The M321 command rechecks frozen selector identity, 27 existing board records, and historical 12-video predictions; it does **not** rerun inference. A `--check` with missing assets exits nonzero. On Windows in the original development machine, use the explicitly installed Python executable recorded in the parent project rather than assuming `python` is on PATH.

## KV260 prebuilt path (local package; board result separately recorded)

Prerequisites: supported KV260 Ubuntu image, matching PYNQ/XRT, exact model/bitstream assets, and a separate stable rollback. The owner's **local prebuilt TAR** includes the exact hash-locked assets listed in [asset manifest](../manifests/external_assets.json); the Git source tree does not. There is no public download URL yet. Its prepared two-part distribution, hashes and host-side reassembly are documented in [prebuilt release assets](prebuilt_release.md). A recipient must obtain the TAR lawfully and compare its SHA-256 before extraction. Do not use a similarly named upstream checkpoint as a substitute.

The board needs about 3.9 GB for extracted files, additional headroom for an isolated Python runtime, and roughly 200 MB of temporary RAM during wheel installation. Stream the archive from an authenticated transfer peer to a new directory rather than keeping both a full TAR and extracted copy on a space-constrained microSD. Never remove the stable M254 install to make room. The one-time local installation record is `INSTALL_BOARD_RESULT.json` in the extracted directory; it is not a model-result PASS.

```sh
/usr/local/share/pynq-venv/bin/python3 scripts/verify_prebuilt_package.py
/usr/local/share/pynq-venv/bin/python3 scripts/preflight.py --check --config configs/deployment.example.json
sudo -n true
sudo -n /usr/local/share/pynq-venv/bin/python3 scripts/install_runtime_wheels.py
sudo -n env TELLME_RELEASE_BOARD_LAUNCH_UNVERIFIED=ACKNOWLEDGED bash scripts/run_demo.sh
```

The wheel installer verifies the bundled M189 ARM64 wheel manifest, torchvision wheel and historical M193 Pillow wheel, installs into this release's `runtime_site`, checks Torch 2.12.1+cpu / torchvision 0.27.1+cpu, Pillow 12.1.0 `Image.Resampling` and the native NMS operator, and writes `RUNTIME_SITE_READY.json`. It never uses the historical stable runtime directory; if it fails, do not launch. The `ACKNOWLEDGED` value is an explicit operator opt-in, **not evidence that the installation passed**. A real launch requires root and same-terminal `sudo -n true`; `run_demo.sh` selects the observed PYNQ Python and XRT environment, then invokes the fixed root/XRT/PYNQ/package-manifest preflight before service start. The original historical `run_m254_board_gate.sh` is an upgrade gate requiring predecessor state, not a fresh installation guide. Do not run it as a first-start command. If the port is occupied, the wrapper exits without killing another service. Model initialization may take minutes; a `live/start` request synchronously loads the fast detector before it returns HTTP 202, so a short client timeout is not a safe readiness check. Poll the live status endpoint after a bounded start request and distinguish `runtime-loading`, `ready`, and `worker-failed`. Follow the fixed Build-ID → descriptor → chain → layer → fixed sample → Web gate order before claiming a full deployment. The v7 local first-install evidence reaches fixed-text E2E and no-frame Web runtime-ready; the separate M328 companion later passed the direct fixed-video window, **not** the alarm-triggered Web route.

For the frozen four-frame Mage-VL test, use the separately hash-locked companion and direct 4B entry described in [fixed-video reproduction](fixed_video_reproduction.md). This avoids treating an M254 fast-path result with no alarm as 4B video inference.
