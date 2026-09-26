# Mage-VL 4B on KV260 (research preview)

This repository is a source-and-evidence snapshot of a PS–PL Mage-VL 4B prototype on AMD Kria KV260. The default is the historically board-tested **M254 / M120 T32** service, Build ID `0x4D395832`. It is not a seconds-level 4B video system. BACT-V2 is an offline budget/evaluation path, not the default Web router. Decode-one Build `0x4F503131` is isolated experimentation and is not promoted.

| Path | What can be reviewed or reproduced without a board | Board status |
| --- | --- | --- |
| Stable M254 | Original Python/HTML/CSS/JS, T32 HLS, historical manifests and gates | Separate v7 first install: fixed-text FPGA E2E and no-frame Web runtime ready; M328 companion: direct fixed-video 4B E2E PASS. Alarm-triggered Web video remains unverified. |
| BACT-V2 | Nine frozen selector candidates, 27 board-cost records, 12-clip retrospective prediction calculation | Existing KV260 cost measurements; not a new model run or independent accuracy win |
| Decode-one | OP01 source and same-session M325 result | Experimental only; FIFO capacity long test stopped, no formal promotion |

The fast channel detects people/actions/knife-related events without waiting for 4B review. The slow 4B path is alarm-triggered and uses PS vision plus T32 PL language linear operations. This is not a claim of certified safety detection. The source contains historical references to knife detection; do not use it for unattended safety decisions.

Start with [quickstart](docs/quickstart.md) and [architecture](docs/architecture.md). `scripts/preflight.py --dry-run` is the no-device release entry; `scripts/run_demo.sh` is a gated board entry, not the old upgrade gate. Run BACT evidence reproduction with `python3 scripts/m321_reproduce_bact_v2_evidence.py --only all` in a Python 3 environment; it needs no weight download. See [model/assets](docs/model_setup.md), [environment](docs/environment.md), [build scope](docs/build.md), [results](docs/results.md), [limits](docs/limitations.md), [provenance](docs/provenance.md), and [release readiness](RELEASE_READINESS.md).

The historical fixed-video same-session M325 comparison reported stable T32 TTFT **228.531 s** and three incremental steps **36.584 / 36.169 / 36.183 s**. The experimental OP01 measured **241.072 s** and **40.777 / 34.763 / 34.666 s**. The second output token was EOS; the last two steps were forced continuation diagnostics, not user-visible sustained throughput. Neither mode meets real-time 4B video analysis. See [source evidence](deployment/mage_vl4b/M325_FULL_SESSION_BOARD_RESULT.json).

For the independent v7 installation, the original four-frame M277 sample was submitted through a separate hash-locked companion and the **direct** 4B path completed: Build `0x4D395832`, 778 logical FPGA calls, output `0`, first Token **230.721 s** excluding initialization. The frozen path uses only the last frame for two visual views, and this is not proof of a Web alarm review or temporal understanding. See [fixed-video reproduction](docs/fixed_video_reproduction.md) and the owner-workspace `deployment/mage_vl4b/M328_RELEASE_VIDEO_BOARD_RESULT.json`.

No model weights or bitstreams are in Git. Their identity and availability are in [external assets](manifests/external_assets.json); the exact stable M125 language and LM Head layouts have been located and rehashed on the owner's WSL host ([provenance](docs/stable_asset_provenance.md)). A separate local, hash-checked v7 prebuilt TAR and M328 video companion have passed the stated owner-board gates, but **neither has a public download URL** or is part of this Git tree. This snapshot is not yet an unrestricted public release: project-source, copied upstream-code and sample-video redistribution need owner review. See [third-party notices](THIRD_PARTY_NOTICES.md) and [release notes](docs/releases/v0.1.0.md). No remote repository, DOI, paper, or author list is asserted.

中文说明：[README.zh-CN.md](README.zh-CN.md).
