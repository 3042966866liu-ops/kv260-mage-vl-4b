# 当前演示版本：剪枝、蒸馏与恢复训练源码

本包是截至2026-10-28的源码交付包，保留原项目相对路径与原文件字节。先看 docs/CURRENT_RECIPE.json、下方代码索引，再看原协议与报告。GitHub源码版只提供当前V4与rank8头的参数清单、结构及SHA；实际权重参数已随此前离线ZIP交付，并与网页07工作器加载文件逐字节核对，不重复上传到公开Git仓库。

## 一、实际采用的剪枝方法

1. 整层结构剪枝：24视觉块/36语言块缩到10视觉块/18语言块。根据训练输入统计的层残差相对大小与估计耗时之比排序，结合有限候选组合及真实质量/板端耗时选择；这是启发式搜索，未证明全局最优。
   - 当前10V18L掩码的直接生成入口：`experiments/demo_recovery_20261025/speed_candidates.py`。
   - 早期候选搜索：`experiments/fixed_demo_prune_20261025/search.py`。
   - 真正收缩ModuleList、压紧语言层索引及KV配置：`experiments/fixed_demo_prune_20261025/runtime_demo.py` 与 `experiments/whole_layer_20261025/runtime.py`。
2. 通道结构剪枝：以G64为组联动裁剪MLP的上/下投影，旧主体使用原整数码/scale切片与R1均值残差补偿。视觉V2/V3/V6在原PS执行路径从4096缩至3072。
   - 原码读取：`experiments/speed_target_30s_20261020/generate_flap522.py`。
   - PS三层精确裁剪与R1：`experiments/visual_ps_prune_20261024/fit02.py`、`PS_crop_native.py`。
   - 二十二层原主体的组号、R1身份：`deployment/mage_vl4b/optimization_v1/candidates/M523-M455-twentytwo-layer-R1-research-240/TWENTYTWO_LAYER_PLAN.json`。之后删除的层不再执行，不能把旧22层都算为最终保留。
3. V4是后续的独立恢复模块：4096→3584；用post-GELU各G64组对fc2输出的贡献Gram矩阵，考虑组间交叉项，贪心删除8组。它与最初纯权重energy选组不同。
   - `experiments/v4_recovery_20261025/fit.py`：真实学生前缀输入→贡献选组→R1→条件触发fc2恢复→W4导出。
   - 当前V4删除组：[45,31,7,48,15,11,42,55]；其余保持原顺序。

不是把权重置零来冒充加速；保留模块的形状、层调用和权重读取均按实际执行结构处理。早期DP/直接搜索的其他脚本不是当前10V18L掩码的直接生成器，不能混称为本版算法。

## 二、实际采用的教师学生恢复

### A. V4模块恢复：已用于当前演示

入口：`experiments/v4_recovery_20261025/fit.py`，协议：`M536-V4-3584-recovery-protocol-01/RESULT.json`。

教师是当前4096宽V4在清晰训练输入上的输出；学生使用对应清晰或较难画面经自己前缀传播后的激活。先拟合平均残差R1；局部门限不过再只训练fc2，fc1冻结。clean与paired_harder_student各128步，后64步采用W4的STE量化前向，最终按实际W4/G64/FP16 scale导出后再评价。采用paired_harder_student，R1合入fc2偏置；推理没有额外教师网络。

当前导出：`candidates/M536-V4-3584-recovery-01/`（保留其完整项目路径）。这是局部特征重构/量化感知恢复，不是全模型蒸馏。

### B. 清晰教师／较难学生＋反例回放：当前M542输出头

入口：`experiments/demo_counterexample_20261026/fit.py`；增强与采集辅助：`experiments/demo_adapt_20261026/`、`experiments/augmented_student_20261025/target_head.py`。

仅更新rank8全词表残差头A/B，模型主体冻结。形式是 logits = base_logits + B(Ah)。clean/harder两臂相同初始化、每臂400步，前64步保持相同清晰轨迹；随后harder臂同时回放清晰与困难画面。困难输入使用亮度、gamma、JPEG和轻噪声等光度变化，保护几何关系及标签可见证据。

损失包含标签CE与适用样本上的教师KL（温度2）：已有较深低比特教师8条清晰输出用于对应16条清晰/困难学生行；4条旧fit为旧分布回放；另外17条仅标签CE。不能把37条全称为教师蒸馏，也不能把低比特教师称为原始未量化教师。只取固定400步终点，不按新增检查集挑epoch。

当前采用：`candidates/M542-demo-head-harder_student-01/`。A/B及learned_head.py与当前网页07包完全相同。原37条明确作为演示fit；新增时点仍为同视频来源，不代表独立泛化准确率，也未证明增强普遍优于清晰训练。

### C. 完整联合蒸馏/LoRA：历史研究，对照保留

`experiments/demo_recovery_20261025/train_local.py`：早期分层局部蒸馏。
`experiments/augmented_student_20261025/train_joint02.py`、`joint_runtime02.py`：答案CE、教师logits KL、视觉/中间特征监督及LoRA等联合恢复研究。
`augmentation_contract.py`：清晰教师/较难学生的配对增强策略。

这些研究源码不表示整套联合LoRA主体已经成功部署。当前部署贡献应分别写为“结构剪枝＋V4模块恢复＋目标部署数值上的低秩头恢复”，不要写成DINO网络已部署。

## 三、如何阅读和复现

1. 先运行本包根目录 `tools/verify_sources.py`；它只检查所有文件SHA、字节数和Python语法，不导入模型、不训练、不访问COM3。
2. 阅读 docs/CURRENT_RECIPE.json，再依次看 speed_candidates.py、runtime_demo.py、V4 fit.py、M542 fit.py。
3. 原协议/RESULT/REPORT在原 `deployment/.../runs/` 路径，保留最初的软件/板端证据层级和失败记录；原报告里的“当时未上板”是历史事实，后续M543实板和M544网页证据另列，不能覆盖旧记录。
4. 要重新训练，需恢复原项目的基座模型、packed checkpoint、训练视频/帧及捕获的教师/学生特征；参考 docs/DEPENDENCIES.json 中被省略的路径和SHA。依赖包括NumPy、PyTorch（训练需CUDA）、Transformers、Pillow等，使用原项目环境和协议中的版本；本包未重新安装或运行训练。
5. 历史脚本采用固定路径、冻结SHA及“输出已存在则拒绝覆盖”。不可直接在有原结果的工作区盲跑；复现实验需独立工作区/版本化输出协议，避免覆盖原证据。源码未为方便打包而改写路径或去掉门限。

本包不是自带完整4B基座和视频数据的一键训练/烧板安装包。此前离线ZIP附有当前V4恢复权重与rank8头参数；本GitHub源码版仅保留对应清单和代码，不附这些参数或数GB基座、全量分片、视频、人像帧、训练特征缓存、UART日志、网页会话密钥或硬件控制恢复脚本集合。训练/板端运行仍需原有依赖、权限及分级门禁。

## 四、验收证据范围

M536保存V4恢复与局部/整请求观察；旧正式计数门禁失败不改成通过。M542保存25条软件重载检查；M543保存修复头六固定帧及两条热重复实板检查；M544保存本次视频7采样图的新真实识别与红色报警。它们均不能推出任意视频持续监控或泛化质量保证。

当前输入仍为双视图、98视觉token、128总token、4个T32批次；没有采用95-token方案。此交付只复制与校验文件，不改变正在运行的演示、权重或板卡。
