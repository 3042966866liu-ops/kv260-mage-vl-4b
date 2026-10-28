"""Export historical pruning/recovery sources, without touching the board or live app."""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OPT = ROOT / 'deployment/mage_vl4b/optimization_v1'
NAME = 'MAGE_VL4B_Pruning_Distillation_Source_20261028_v2'
STAGE = ROOT / 'outputs' / NAME
ARCHIVE = ROOT / 'outputs' / (NAME + '.zip')
CODE = {'.py', '.c', '.h', '.cpp'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.open('x', encoding='utf-8').write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    assert not STAGE.exists() and not ARCHIVE.exists(), 'Never overwrite an earlier export'
    chosen = {}
    omitted = {}
    def add(path, reason, expected=None):
        path = Path(path).resolve()
        key = rel(path)
        assert path.is_file() and not path.is_symlink(), key
        assert '__pycache__' not in path.parts and path.suffix != '.pyc'
        if expected:
            assert sha(path) == expected, ('Source identity mismatch', key)
        chosen.setdefault(key, set()).add(reason)

    protocols = [
        'M523-fixed-demo-pruning-128-protocol-01',
        'M524-demo-layer-distillation-128-protocol-01',
        'M525-joint-augmented-student-128-protocol-02',
        'M536-V4-3584-recovery-protocol-01',
        'M542-demo-counterexample-protocol-01',
    ]
    for name in protocols:
        file = OPT / 'runs' / name / 'RESULT.json'
        add(file, 'original_frozen_protocol')
        for key, digest in read(file).get('frozen', {}).items():
            path = ROOT / key
            if path.suffix in CODE:
                add(path, 'frozen_source:' + name, digest)
            else:
                omitted[key] = dict(sha256=digest, included=False,
                    reason='External historical model/data/cache/config dependency; not executable source')

    # Explicit entry points and runtime adapters that generate/apply the adopted recipe.
    groups = {
        'fixed_demo_prune_20261025': ['demo_common.py','runtime_demo.py','search.py','search_continue02.py','prepare.py','board_subset.py','board_visual_subset.py'],
        'whole_layer_20261025': ['common.py','runtime.py','search.py','prepare.py'],
        'demo_recovery_20261025': ['common_recovery.py','speed_candidates.py','augmentation_contract.py','build_augmentation_preview.py','capture_teacher.py','train_local.py','prepare_training.py','evaluate_student04.py'],
        'augmented_student_20261025': ['common_joint.py','train_joint.py','train_joint02.py','joint_runtime.py','joint_runtime02.py','target_head.py','target_reload.py','prepare_target_head.py','learned_head.py','learned_head02.py','freeze_target_export.py','prepare_balanced02.py'],
        'demo_adapt_20261026': ['common_adapt.py','common03.py','capture03.py','prepare_direct03.py','make_frames.py'],
        'demo_counterexample_20261026': ['common_fix.py','prepare.py','frames.py','fit.py','reload.py','audit.py'],
        'v4_recovery_20261025': ['common_v4.py','prepare.py','fit.py','quality.py','quality02.py','audit_local.py','v4_recovery_native.py'],
        'v4_ablation_20261025': ['common_ablation.py','prepare.py','reuse_and_variants.py','evaluate.py','audit.py','finalize.py'],
        'visual_ps_prune_20261024': ['common.py','prepare02.py','fit02.py','features02.py','quality02.py','PS_crop_native.py','late_oracle.py'],
        'speed_target_30s_20261020': ['generate_flap522.py'],
        'pruning_plan_20261020': ['M455_combination_visual52301.py','M455_twentytwo_visual_scope523290.py'],
    }
    for folder, files in groups.items():
        for filename in files:
            add(ROOT / 'experiments' / folder / filename, 'algorithm_or_recovery_entry')

    # Copy the exact adopted learned components; omit the multi-GB base checkpoint.
    component_names = ['M536-V4-3584-recovery-01','M542-demo-head-harder_student-01']
    for name in component_names:
        folder = OPT / 'candidates' / name
        manifest = read(folder / 'PACKAGE_MANIFEST.json')
        for row in manifest['files']:
            add(folder / row['path'], 'adopted_learned_component', row['sha256'])
        add(folder / 'PACKAGE_MANIFEST.json', 'component_manifest')

    for name in ['M523-M455-twentytwo-layer-R1-research-240/TWENTYTWO_LAYER_PLAN.json',
                 'M523-PS3072-ttft01/PS_NATIVE_PLAN.json',
                 'M543-repaired-campus-fixed-board-02/DEMO_BOARD_PLAN.json']:
        add(OPT / 'candidates' / name, 'recipe_trace_not_current_boot_control')
    cache_source = OPT/'candidates/M534-visual-profile-board-02/visual_cache_profiler.py'
    add(cache_source, 'actual_V4_runtime_cache_dependency')

    # Actual frozen deployment runtime closure: preserve release-relative source paths.
    closure = OPT / 'candidates/M523-PS3072-ttft01/SOURCE_CLOSURE.json'
    add(closure, 'runtime_source_closure')
    release = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    module_paths = {}
    for module, path in read(closure)['modules'].items():
        source = release / path
        if source.is_file() and source.suffix in CODE:
            add(source, 'frozen_runtime_dependency')
            module_paths[module] = source

    evidence_names = protocols + [
        'M524-demo-layer-distillation-128-speed-candidates-01',
        'M536-V4-3584-recovery-fit-01','M536-V4-3584-recovery-local-audit-01',
        'M536-V4-fixed-demo-board-audit-02',
        'M542-demo-counterexample-fit-01','M542-demo-counterexample-final-audit-01',
        'M543-repaired-campus-board-audit-02','M544-six-hour-demo-restored-07',
    ]
    for name in evidence_names:
        folder = OPT / 'runs' / name
        add(folder / 'RESULT.json', 'saved_result_no_new_model_run')
        if (folder / 'REPORT.md').is_file():
            add(folder / 'REPORT.md', 'original_report_scope_and_limits')

    # Resolve normal local imports recursively, without importing or executing code.
    search_dirs = list(dict.fromkeys([ROOT, ROOT/'scripts/optimization', ROOT/'deployment/mage_vl4b/scripts']
                      + [ROOT / p for p in ['experiments/adaptive_exec_error', 'experiments/speed_target_30s_20261020']]
                      + [ROOT / 'experiments' / d for d in groups]
                      + [cache_source.parent]
                      + [p.parent for p in module_paths.values()]))
    scanned = set()
    local_edges = []
    other_imports = set()
    while True:
        todo = [ROOT/key for key in chosen if key.endswith('.py') and key not in scanned]
        if not todo:
            break
        for source in todo:
            scanned.add(rel(source))
            tree = ast.parse(source.read_text(encoding='utf-8-sig'), filename=rel(source))
            compile(tree, rel(source), 'exec')
            for node in ast.walk(tree):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
                for name in names:
                    if name.split('.')[0] in sys.stdlib_module_names:
                        continue
                    target = None
                    # The containing folder wins for historical generic common/runtime imports.
                    for directory in [source.parent] + search_dirs:
                        p = directory.joinpath(*name.split('.')).with_suffix('.py')
                        if p.is_file():
                            target = p
                            break
                    if target is None:
                        target = module_paths.get(name)
                    if target:
                        add(target, 'recursive_local_import')
                        local_edges.append(dict(source=rel(source), module=name, target=rel(target)))
                    else:
                        other_imports.add(name)

    STAGE.mkdir(parents=True, exist_ok=False)
    for key in sorted(chosen):
        source, destination = ROOT/key, STAGE/key
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        assert sha(source) == sha(destination)

    head = OPT/'candidates/M542-demo-head-harder_student-01'
    live = OPT/'candidates/M544-campus-live-worker-07'
    for name in ['A.npy','B.npy','learned_head.py']:
        assert sha(head/name) == sha(live/name), ('Live head mismatch', name)
    v4 = OPT/'candidates/M536-V4-3584-recovery-01'
    assert sha(v4/'V4_3584_weights.npz') == sha(live/'V4_3584_weights.npz')

    dump(STAGE/'SOURCE_INDEX.json', {key: sorted(value) for key,value in sorted(chosen.items())})
    external_roots = {'PIL','cv2','huggingface_hub','numpy','pynq','safetensors','tokenizers','torch','torchvision','transformers'}
    optional = {'streammind_gate': 'Optional relative gate in upstream modeling_mage_vl.py; not invoked by adopted pruning/student path. Requires original base-model source if used.'}
    assert all(n.split('.')[0] in external_roots or n in optional for n in other_imports), sorted(other_imports)
    dump(STAGE/'DEPENDENCY_CLOSURE.json', dict(local_import_edges=local_edges,
        normal_import_closure=True, local_missing_imports=[],
        external_or_dynamic_import_names=sorted(other_imports),
        optional_unused_upstream_modules_not_included=optional,
        original_protocol_noncode_dependencies=omitted,
        historical_paths_required=True, binary_model_data_not_self_contained=True,
        closure_note='Normal local imports resolved recursively. Dynamic loaders also use copied frozen source/closure maps. No promise of standalone training without omitted model/data/captures.'))
    plan = read(OPT/'candidates/M543-repaired-campus-fixed-board-02/DEMO_BOARD_PLAN.json')
    dump(STAGE/'CURRENT_RECIPE.json', dict(retained_vision=plan['retained_vision'],retained_language=plan['retained_language'],
        original_vision_blocks=24,original_language_blocks=36,
        input_tokens=128,visual_tokens=98,views=2,T32_batches=4,
        PS_V2_V3_V6_width=3072,PS_V4_width=3584,
        source_mask_generator='experiments/demo_recovery_20261025/speed_candidates.py',
        whole_layer_runtime='experiments/fixed_demo_prune_20261025/runtime_demo.py',
        V4_selected_method=read(OPT/'runs/M536-V4-3584-recovery-fit-01/RESULT.json')['selected_local_method'],
        learned_head_rank=8,learned_head_arm='harder_student',
        exact_head_and_V4_match_live_package=True,live_package_manifest_sha256=sha(live/'PACKAGE_MANIFEST.json'),
        current_body_all_weights_not_included=True,
        research_joint_LoRA_not_deployed=True,source_archive_only=True,board_commands=0))

    (STAGE/'README_先看这里.md').write_text(README, encoding='utf-8')
    (STAGE/'verify_archive.py').write_text(VERIFY, encoding='utf-8')
    rows = [dict(path=p.relative_to(STAGE).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
            for p in sorted(STAGE.rglob('*')) if p.is_file()]
    manifest = dict(format='source-handoff-v1',file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
        source_file_count=sum(key.endswith('.py') for key in chosen),
        files=rows,scope='Actual pruning plus adopted recovery and explicitly marked research alternatives',
        no_board_access=True,no_live_server_change=True,no_training_launched=True)
    dump(STAGE/'MANIFEST.json', manifest)
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(STAGE.rglob('*')):
            if p.is_file():
                z.write(p, NAME+'/'+p.relative_to(STAGE).as_posix())
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(rows)+1
        for row in rows:
            assert hashlib.sha256(z.read(NAME+'/'+row['path'])).hexdigest()==row['sha256']
    result = dict(status='VERIFIED_PRUNING_DISTILLATION_SOURCE_EXPORT',archive=rel(ARCHIVE),
        archive_sha256=sha(ARCHIVE),archive_bytes=ARCHIVE.stat().st_size,
        manifest_sha256=sha(STAGE/'MANIFEST.json'),file_count_with_manifest=len(rows)+1,
        uncompressed_bytes_with_manifest=sum(r['bytes'] for r in rows)+(STAGE/'MANIFEST.json').stat().st_size,
        Python_compile_count=len(scanned),all_copied_original_bytes=True,
        current_head_and_V4_bytes_match_live=True,board_commands=0,model_forwards=0)
    dump(ROOT/'outputs'/(NAME+'_RECEIPT.json'), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))

README = r'''# 当前演示版本：剪枝、蒸馏与恢复训练源码

本包是截至2026-10-28的源码交付包，保留原项目相对路径与原文件字节。先看 CURRENT_RECIPE.json、下方代码索引，再看原协议与报告。当前采用的 V4 权重、rank8 头参数一并提供，并与网页07工作器实际加载的文件逐字节核对。

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

1. 先运行本包根目录 `verify_archive.py`；它只检查所有文件SHA、字节数和Python语法，不导入模型、不训练、不访问COM3。
2. 阅读 CURRENT_RECIPE.json，再依次看 speed_candidates.py、runtime_demo.py、V4 fit.py、M542 fit.py。
3. 原协议/RESULT/REPORT在原 `deployment/.../runs/` 路径，保留最初的软件/板端证据层级和失败记录；原报告里的“当时未上板”是历史事实，后续M543实板和M544网页证据另列，不能覆盖旧记录。
4. 要重新训练，需恢复原项目的基座模型、packed checkpoint、训练视频/帧及捕获的教师/学生特征；参考 DEPENDENCY_CLOSURE.json 中被省略的路径和SHA。依赖包括NumPy、PyTorch（训练需CUDA）、Transformers、Pillow等，使用原项目环境和协议中的版本；本包未重新安装或运行训练。
5. 历史脚本采用固定路径、冻结SHA及“输出已存在则拒绝覆盖”。不可直接在有原结果的工作区盲跑；复现实验需独立工作区/版本化输出协议，避免覆盖原证据。源码未为方便打包而改写路径或去掉门限。

本包不是自带完整4B基座和视频数据的一键训练/烧板安装包。仅附当前V4恢复权重与rank8头参数，未附数GB基座、全量分片、视频、人像帧、训练特征缓存、UART日志、网页会话密钥或硬件控制恢复脚本集合。训练/板端运行仍需原有依赖、权限及分级门禁。

## 四、验收证据范围

M536保存V4恢复与局部/整请求观察；旧正式计数门禁失败不改成通过。M542保存25条软件重载检查；M543保存修复头六固定帧及两条热重复实板检查；M544保存本次视频7采样图的新真实识别与红色报警。它们均不能推出任意视频持续监控或泛化质量保证。

当前输入仍为双视图、98视觉token、128总token、4个T32批次；没有采用95-token方案。此交付只复制与校验文件，不改变正在运行的演示、权重或板卡。
'''

VERIFY = r'''"""Read-only archive verification; stdlib only, no model/board imports."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
m=json.loads((root/'MANIFEST.json').read_bytes())
assert len(m['files'])==m['file_count']
total=0;compiled=0
for r in m['files']:
    p=root/r['path'];assert p.resolve().is_relative_to(root)
    b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
    total+=len(b)
    if p.suffix=='.py':compile(b,str(p),'exec');compiled+=1
assert total==m['total_bytes']
print('PASS',len(m['files']),'hashed files;',compiled,'Python sources compiled; no model or board execution.')
'''

if __name__ == '__main__':
    main()
