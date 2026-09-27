# Mage-VL 4B on KV260

English · [简体中文](README.md)

This is a multimodal inference research prototype for AMD Kria KV260. It asks how a 4B model can run with limited memory and a fixed T32 FPGA execution granularity, while keeping PS–PL execution and its costs measurable.

The project includes mixed-precision weight adaptation, a PS vision tower with PL language Linear operations, an independently installed fixed-video example, and an isolated Web manual-review path. It also records experiments that did not improve the final request: a faster local parser, a T64 design that missed timing, and a generic fast detector that responded weakly to visible kitchen knives.

The default board path uses stable T32 Build `0x4D395832`. Source and experimental evidence can be reviewed here. Model weights and bitstreams are excluded from Git; the verified prebuilt package has no public download link yet.

## Why hardware cost is not linear in token count

![The AMD Kria KV260 board used in this project](docs/assets/kv260-board.jpg)

The project owner supplied this photograph and approved its publication. UI screenshots and original monitoring videos are not included in the repository.

![Logical language FPGA calls at the fixed T32 batch boundary](docs/assets/t32_batch_boundary.svg)

The plot shows **logical calls**, not full-request latency; see the [architecture](docs/architecture.md) and [experiment index](experiments/README.md) for the implementation and measurements.

## Main contributions

1. **Fit the model to board constraints.** Choose W2/W3/W4 and selected higher-precision components by sensitivity, then lock packed weights and layouts by hash. [Engineering journey](docs/optimization_journey.md)
2. **Build verifiable PS–PL inference.** PS handles vision, attention, normalization, and KV cache; the T32 PL kernel runs language Linear/LM Head work. Fixed-input gates check Build ID, FPGA calls, output, and CPU Linear fallback. [Architecture](docs/architecture.md) · [Source map](docs/source_map.md)
3. **Accept optimizations by full-request measurements.** Vectorized visual W4 decoding, weight staging, and output parsing helped components; T64, Decode-one, and a parser candidate remained experimental after timing or end-to-end comparisons. [Performance analysis](docs/performance_attribution_history.md)
4. **Align input budgets to hardware batches.** BACT-V2 studies view and prompt budgets around T32 boundaries. Moving from 164 to 159 tokens crossed the 160-token boundary and reduced logical language calls from 932 to 778. [BACT and prompt study](docs/bact_v2.md)

## Representative results

| Experiment | Result and scope |
| --- | --- |
| Independently installed fixed video | Four frames submitted in order, but only two views of the last frame used by the model; 159 input tokens, 778 logical language FPGA calls, output `0`; **230.721 s** first token excluding initialization. [Public result](experiments/fixed_video/RESULT.json) |
| Paired CPU/PL chain | Ten interleaved pairs for each of two fixed double-descriptor shapes. A53 CPU/PL medians: W2 **5.891/2.244 ms**, W4 **5.871/2.525 ms**, about **2.63×/2.33×**. These are not whole-model speedups. [Protocol](docs/cpu_pl_benchmark.md) |
| T32 batch boundary | For the fixed Prefill contract, 164 tokens need 6 batches/932 calls; 159 need 5 batches/778 calls. The staircase is supported by 27 board records. [Method and evidence](docs/bact_v2.md) |
| Web manual review | An isolated version returned two real video-window Web→4B/FPGA→SSE reviews; first-token times **196.286/174.653 s**. This was not an automatic alarm trigger. [Experiment](experiments/m335_manual_web_review/REPORT.md) |

Minutes-scale 4B first-token latency is not seconds-level video semantic updating. The constrained path only uses two last-frame views. The fast channel can keep accepting frames and discard stale work, but reliable automatic knife triggering has not been established. See [results](docs/results.md) and [limits](docs/limitations.md) for conditions.

## Getting started

Without a board, use the [environment guide](docs/environment.md) and reproduce the frozen BACT selector, cost, and quality records. This does not download weights or perform new model inference:

```bash
python3 scripts/m321_reproduce_bact_v2_evidence.py --only all
```

For KV260, read the [installation guide](docs/quickstart.md), [model and hardware assets](docs/model_setup.md), and [fixed-video reproduction](docs/fixed_video_reproduction.md). The no-device preflight is:

```bash
python3 scripts/preflight.py --dry-run --config configs/deployment.example.json
```

The local v7 prebuilt package and fixed-video companion passed an independent-directory install on the owner's KV260, but neither has a public download link. **Cloning this repository alone is insufficient to reproduce that board install.** See the [build scope](docs/build.md).

## Where to read next

| Question | Entry points |
| --- | --- |
| How is work split across PS and PL? | [Architecture](docs/architecture.md) · [Source map](docs/source_map.md) |
| Why was this implementation selected? | [Engineering journey](docs/optimization_journey.md) · [BACT/prompt](docs/bact_v2.md) |
| How can I inspect the numbers? | [Results](docs/results.md) · [Experiment index](experiments/README.md) |
| How can I install or build it? | [Quickstart](docs/quickstart.md) · [Asset manifest](manifests/external_assets.json) · [Build guide](docs/build.md) |
| What are the release and attribution terms? | [Provenance](docs/provenance.md) · [Third-party notices](THIRD_PARTY_NOTICES.md) · [Release readiness](RELEASE_READINESS.md) |

This repository is a research preview, not a certified safety-monitoring product. Licensing of original code and redistribution terms for some upstream files, models, and examples require separate review; see [release readiness](RELEASE_READINESS.md).
