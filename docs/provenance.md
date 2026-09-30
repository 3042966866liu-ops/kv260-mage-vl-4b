# 代码来源与权利核验

本地项目快照包含项目专用的 T32/HLS、PS/PYNQ 运行时、BACT 研究代码和 Web 代码，也包含看起来衍生自 Mage-VL/Transformers 的 `ps_vision_payload/modeling_mage_vl.py`、`configuration_mage_vl.py` 与模型 `config.json`。官方 [Mage 仓库](https://github.com/microsoft/Mage)和[模型卡](https://huggingface.co/microsoft/Mage-VL)将 Mage-VL 标为 Apache-2.0；仓库根目录的[软件许可证](https://github.com/microsoft/Mage/blob/main/LICENSE)为 MIT。本地源码清单**尚未明确**这些文件的精确上游提交、逐文件来源、本地修改及署名义务；不能把复制文件描述为完全原创，也不能猜测其许可证。板端证据中的模型标识是 `microsoft/Mage-VL`，但该标识和模型卡许可不能证明每个复制文件都与特定上游版本逐字节一致。

SSDLite checkpoint 来自 torchvision 模型权重，不包含在 Git 中。预构建包还包含哈希锁定的 M189 ARM64 Python wheel 包、匹配的 torchvision wheel 和历史 M193 Pillow wheel，使首次安装无需依赖所有者原有稳定目录。这些 wheel 保留第三方许可证，不属于项目原创；即使已通过 Release 公开，其精确上游 URL、声明和再分发条款仍需逐包核对。量化语言分片、视觉 safetensors、embedding/tokenizer 和 bitstream 也不进入 Git，而是包含在预构建归档中。精确稳定 M125 语言／LM Head 布局已在所有者 WSL 主机定位并重算哈希；[来源核验](stable_asset_provenance.md)区分资产身份与再分发权限。`model_tools/` 脚本为工作区历史准备脚本的逐字节副本，原始作者身份及模型输入权利仍需所有者确认。

## 许可范围与待完成的再分发审查

源码快照已在 GitHub 公开。所有者为其拥有且有权许可的原创内容选择 Apache-2.0，见[许可范围](../LICENSE_SCOPE.md)。这不建立第三方再分发权；共同创作内容仍需相关权利人的许可。复制的 Mage-VL/Transformers 文件还需记录精确上游版本及修改。Microsoft 模型／代码、torchvision 资产、AMD 工具和其他第三方组件保留各自许可证与声明。预构建归档在这些审查完成前已上传，公开发布不能被描述为权利审查已通过。应优先完成逐文件审查，并修正或撤下不允许再分发的资产。

原始相对路径和哈希见[发布文件清单](../manifests/release_files.json)。清单区分逐字节快照与新发布文件；哈希是文件身份，不是许可证据。`THIRD_PARTY_NOTICES.md` 记录第三方署名和未解决事项，项目 `LICENSE` 不会重新许可这些内容。
