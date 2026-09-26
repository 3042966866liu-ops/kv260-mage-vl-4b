# Dependency scopes

- `offline-evidence.txt` uses Python 3 standard library only for M321 and release checks. No Python package install required.
- Static traversal of the historical KV260 runtime finds external imports `PIL`, `cv2`, `numpy`, `packaging`, `pynq`, `requests`, `safetensors`, `scipy`, `tokenizers`, `torch`, `torchvision`, `tqdm`, `transformers`, and `typing_extensions`; XRT is also required. Evidence identifies CPU Torch `2.12.1+cpu`, torchvision `0.27.1+cpu`, NumPy `1.26.4`, XRT `2.13.0` on the tested image. Versions of the other imports were not verified here. These are **observed**, not a portable lock file or public wheel download guarantee.
- HLS/Vivado are separate build-host tools. No `pip` requirement installs them.

Because the exact aarch64 wheel source, transformers/tokenizers revisions and image provisioning recipe are not established in this snapshot, no speculative install command is supplied. The [readiness report](../RELEASE_READINESS.md) marks prebuilt installation incomplete.
