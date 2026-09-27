# Third-party notices and release review

- Mage-VL: the official [Microsoft Mage repository](https://github.com/microsoft/Mage) lists Mage-VL under Apache-2.0, and the official [Hugging Face model card](https://huggingface.co/microsoft/Mage-VL) marks the model Apache-2.0. The GitHub repository's root [LICENSE](https://github.com/microsoft/Mage/blob/main/LICENSE) is MIT for that repository's software. **The exact upstream revision and file-by-file origin of the copied local modeling/configuration files are not yet pinned**, so these public license labels are not a completed attribution review for every copied file. No model weights are distributed here.
- Hugging Face Transformers APIs are imported by the copied model code; dependency license and exact installed version should be checked before publication.
- torchvision SSDLite architecture/checkpoint is used by the fast path. The official [torchvision documentation](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.detection.ssdlite320_mobilenet_v3_large.html) identifies `COCO_V1`; the [torchvision repository](https://github.com/pytorch/vision) identifies BSD-3-Clause for its software. The checkpoint remains external; confirm the exact checkpoint's source and notices before redistributing it.
- AMD/Xilinx Vitis, Vivado, PYNQ and XRT are tool/runtime dependencies and are not distributed here. Hardware bitstream is excluded.

No third-party ownership is disclaimed. The owner selected Apache-2.0 for original work they have the right to license; [`LICENSE_SCOPE.md`](LICENSE_SCOPE.md) excludes third-party material from that grant. The upstream attribution and public redistribution review is still incomplete for the prebuilt archive.

## Prepared v7 archive inventory (not yet published)

The immutable M327 v7 prebuilt TAR contains the Mage-VL-derived quantized
language weights, vision weights, tokenizer, a torchvision SSDLite checkpoint,
the stable KV260 bitstream/HWH, and 37 ARM64 Python wheels. Its file identity
and first-install result are recorded in [`RELEASE_READINESS.md`](RELEASE_READINESS.md).
The base TAR contains no video, still-image fixture, or monitoring footage.

An offline metadata inventory of the nested 36-wheel bundle found license
metadata in all 36 wheels and embedded license files in 35. `tokenizers`
reported an Apache Software License classifier but no embedded license file;
its notice must be supplied separately if that wheel is redistributed. The
additional Pillow 12.1.0 wheel reports `MIT-CMU` and includes a `LICENSE`
file. These are metadata observations, not a file-by-file legal clearance.

The official [Mage-VL model card](https://huggingface.co/microsoft/Mage-VL)
labels the model Apache-2.0; the [Mage source repository](https://github.com/microsoft/Mage)
has its own MIT license. The [torchvision source license](https://github.com/pytorch/vision/blob/main/LICENSE)
is BSD-3-Clause. AMD lists separate agreements for [Vivado tools and LogiCORE
IP](https://www.amd.com/en/products/adaptive-socs-and-fpgas/intellectual-property/license.html).
The exact versions and applicable terms for each copied model file, checkpoint,
wheel and IP in this archive still need to be matched to the preserved assets
before public upload. A model-card tag or wheel metadata field alone is not a
complete notice bundle.
