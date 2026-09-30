# 第三方来源、署名与发布审查

- Mage-VL：官方 [Microsoft Mage 仓库](https://github.com/microsoft/Mage)将 Mage-VL 列为 Apache-2.0，官方 [Hugging Face 模型卡](https://huggingface.co/microsoft/Mage-VL)也将模型标为 Apache-2.0。GitHub 仓库根目录的 [LICENSE](https://github.com/microsoft/Mage/blob/main/LICENSE)对该仓库软件采用 MIT。**本地复制的模型实现／配置文件尚未固定精确上游版本及逐文件来源**，这些公开许可标签不能替代每个复制文件的署名审查。权重不在 Git 源码目录中，但包含在 Release 预构建归档内。
- 复制的模型代码导入 Hugging Face Transformers API；公开分发时须核对依赖许可及实际安装版本。
- 快通道使用 torchvision SSDLite 架构／checkpoint。官方 [torchvision 文档](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.detection.ssdlite320_mobilenet_v3_large.html)标明 `COCO_V1`；[torchvision 仓库](https://github.com/pytorch/vision)对软件采用 BSD-3-Clause。checkpoint 位于 Git 之外、Release 归档之内，须确认精确来源和声明。
- AMD/Xilinx Vitis 与 Vivado 是外部工具依赖。板端 PYNQ/XRT 环境不以完整系统镜像形式提供；Release 归档包含稳定硬件 bitstream/HWH。适用的 AMD/IP 再分发条款仍需核对。

本项目不否认任何第三方权属。所有者为其有权许可的原创内容选择了 Apache-2.0；[许可范围](LICENSE_SCOPE.md)将第三方内容排除在这一授权之外。预构建归档的上游署名及公开再分发审查仍未完成。

## v7 归档内容（已通过 Release 公开）

不可变的 M327 v7 TAR 包含衍生自 Mage-VL 的量化语言权重、视觉权重、tokenizer、torchvision SSDLite checkpoint、稳定 KV260 bitstream/HWH 和 37 个 ARM64 Python wheel。文件身份与首次安装结果见[发布状态](RELEASE_READINESS.md)。基础 TAR 不含视频、静态图像样例或监控录像。

对内嵌 36-wheel 包的离线元数据盘点发现：36 个 wheel 均有许可元数据，其中 35 个带有许可证文件。`tokenizers` 声明 Apache Software License 分类，但没有内嵌许可证文件；再分发该 wheel 时须单独附上声明。额外的 Pillow 12.1.0 wheel 标为 `MIT-CMU`，并包含 `LICENSE` 文件。这些是元数据观察，不等于逐文件权利审查完成。

官方 [Mage-VL 模型卡](https://huggingface.co/microsoft/Mage-VL)将模型标为 Apache-2.0；[Mage 源码仓库](https://github.com/microsoft/Mage)另有 MIT 许可证。[torchvision 源码许可证](https://github.com/pytorch/vision/blob/main/LICENSE)为 BSD-3-Clause。AMD 为 [Vivado 工具及 LogiCORE IP](https://www.amd.com/en/products/adaptive-socs-and-fpgas/intellectual-property/license.html)列出独立协议。归档内每个模型文件、checkpoint、wheel 和 IP 的精确版本及适用条款仍须与保留资产对应核查；模型卡标签或 wheel 元数据字段本身不构成完整声明包。

稳定 overlay 的 HWH 列出所有者自定义 HLS 核及 AMD/Xilinx `axi_dma:7.1`、`proc_sys_reset:5.0`、`smartconnect:1.0` 和 `zynq_ultra_ps_e:3.5`，未出现其他 IP VLNV。此盘点不能替代 Vivado 的 Report IP Status，也不能判定每个核都属于 Included，而非 Purchase/Eval。bitstream 再分发仅面向指定 AMD/Xilinx KV260 器件，仍受适用 AMD 协议约束。

包内 `ssdlite320_mobilenet_v3_large_coco-a79551df.pth` 标识为 torchvision `SSDLite320_MobileNet_V3_Large_Weights.COCO_V1`，不是项目原创。[Torchvision 模型文档](https://docs.pytorch.org/vision/main/models)提醒预训练权重可能受训练数据集相关条款约束；代码仓库的 BSD 许可本身不足以确定该 checkpoint 的许可，不能将其描述为 Apache-2.0。36-wheel 盘点可用 `scripts/audit_wheel_licenses.py` 复现；该 `tokenizers 0.22.1` wheel 有 Apache 许可分类，但没有内嵌许可证文件。公开二进制分发应附上其[上游许可证](https://github.com/huggingface/tokenizers/blob/main/LICENSE)与署名。

独立 M328 四帧摩托车样例经所有者确认为 AI 生成并批准公开分发，不是真实监控视频，也不属于 v7 基础归档。精确 TAR 与张量哈希见[固定视频伴随包清单](manifests/fixed_video_companion_v3.json)。
