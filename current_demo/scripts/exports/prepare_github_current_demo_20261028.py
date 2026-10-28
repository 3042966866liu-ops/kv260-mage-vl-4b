"""Build a source-only, non-destructive GitHub snapshot. Never access hardware."""
from pathlib import Path
import ast, hashlib, json, re, shutil, sys

ROOT=Path(__file__).resolve().parents[2]
OPT=ROOT/'deployment/mage_vl4b/optimization_v1'
OUT=ROOT/'deliverables/github_current_demo_20261028_v2'
DEST=OUT/'current_demo'
SOURCE_EXPORT=ROOT/'outputs/MAGE_VL4B_Pruning_Distillation_Source_20261028_v2'
SUFFIXES={'.py','.c','.cpp','.h','.hpp','.tcl','.sh','.ps1','.cmd','.cjs','.js','.css','.html','.svg','.json','.md','.diff'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def main():
    assert not OUT.exists(), 'Preserve prior staging'
    selected={}
    def add(p,reason):
        p=Path(p).resolve();key=p.relative_to(ROOT).as_posix()
        assert p.is_file() and not p.is_symlink() and p.suffix in SUFFIXES,key
        assert not any(x in p.parts for x in ['.git','__pycache__','node_modules','var']),key
        selected.setdefault(key,set()).add(reason)
    # Algorithm handoff already verified, including recursive Python/runtime dependencies.
    prior=read(SOURCE_EXPORT/'SOURCE_INDEX.json')
    for key in prior:
        if Path(key).suffix in SUFFIXES:
            add(ROOT/key,'pruning_distillation_and_runtime_dependency')
    app=ROOT/'apps/campus_guard'
    for p in app.iterdir():
        if p.is_file() and p.suffix in SUFFIXES:
            add(p,'campus_web_and_host_bridge')
    for p in (app/'static').iterdir():
        if p.is_file() and p.suffix in SUFFIXES:
            add(p,'campus_frontend')
    catalog=read(app/'catalog.json')
    evidence=ROOT/catalog['evidence_file'];assert sha(evidence)==catalog['evidence_sha256']
    add(evidence,'historical_catalog_identity_required_by_software_tests')
    dependency_files=[ROOT/'experiments/visual_early_pl_20261024/V12_visual.py',
        ROOT/'experiments/visual_early_pl_20261024/ttft_control02.py',
        OPT/'candidates/M523-V12-ttft-20261024-02/V12_borrowed.py',
        OPT/'candidates/M523-M455-request-import-02/sources/frozen_bootstrap_0/frozen_video_identity.py']
    for p in dependency_files:add(p,'current_or_historical_adapter_import_closure')
    packages=['M544-campus-live-worker-07','M544-campus-live-control-07',
              'M544-freshboot-runtime-05','M544-freshboot-runtime-capsule-05',
              'M544-freshboot-current22-capsule-05','M544-freshboot-lower-05',
              'M544-freshboot-lower-capsule-05','M544-freshboot-shared335-capsule-05']
    external=[]
    for name in packages:
        folder=OPT/'candidates'/name
        for p in folder.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:
                continue
            if p.suffix in SUFFIXES:
                add(p,'current_board_package:'+name)
            else:
                external.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    # Exact M455 kernel/header closure; do not substitute the mutable root HLS entry.
    hls=OPT/'candidates/M455-dense_output-02'
    for row in read(hls/'PACKAGE_MANIFEST.json')['files']:
        p=hls/row['path']
        if p.suffix in SUFFIXES:
            assert sha(p)==row['sha256']
            add(p,'frozen_M455_HLS_source')
    add(hls/'PACKAGE_MANIFEST.json','original_HLS_manifest_includes_external_fixtures')
    for name in ['m455_build_shell.tcl','m455456_workflow02.py','m455_dense_output.py']:
        add(ROOT/'scripts/optimization'/name,'M455_build_and_host_ABI')
    # Current host preparation source, not historical retained-PID recovery workflows.
    for name in ['prepare_live_worker.py','prepare_live_lifetime06.py','fix_live_component_path07.py',
                 'live_worker_control_boot07.py','save_live_fixed_warmup03.py']:
        p=ROOT/'experiments/demo_counterexample_20261026'/name
        if p.is_file():add(p,'live_worker_preparation')
    add(ROOT/'scripts/exports/package_pruning_distillation_20261028.py','source_export_builder')
    add(Path(__file__),'GitHub_snapshot_builder')
    # Resolve normal local Python imports, preferring sibling modules and current package trees.
    roots=[ROOT,ROOT/'scripts/optimization',ROOT/'deployment/mage_vl4b/scripts',
           ROOT/'experiments/pruning_plan_20261020',ROOT/'experiments/adaptive_exec_error']
    roots += [OPT/'candidates'/name for name in packages]
    roots += [p.parent for p in dependency_files]
    roots += list(dict.fromkeys((ROOT/key).parent for key in selected if key.endswith('.py')))
    scanned=set();edges=[];unresolved=set()
    while True:
        todo=[ROOT/k for k in selected if k.endswith('.py') and k not in scanned]
        if not todo:break
        for p in todo:
            key=p.relative_to(ROOT).as_posix();scanned.add(key)
            tree=ast.parse(p.read_text(encoding='utf-8-sig'),filename=key);compile(tree,key,'exec')
            for n in ast.walk(tree):
                names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module] if isinstance(n,ast.ImportFrom) and n.module else []
                for name in names:
                    if name.split('.')[0] in sys.stdlib_module_names:continue
                    paths=[d.joinpath(*name.split('.')).with_suffix('.py') for d in [p.parent]+roots]
                    match=next((q for q in paths if q.is_file()),None)
                    if match:
                        add(match,'recursive_Python_import')
                        edges.append(dict(source=key,module=name,target=match.relative_to(ROOT).as_posix()))
                    else:unresolved.add(name)
    OUT.mkdir(parents=True,exist_ok=False)
    credential=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{20,})')
    rows=[]
    for key in sorted(selected):
        p=ROOT/key;data=p.read_bytes();assert not credential.search(data),('Credential pattern',key)
        q=DEST/key;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
        assert sha(q)==sha(p)
        rows.append(dict(path=key,bytes=len(data),sha256=sha(p),reason=sorted(selected[key])))
    def save(name,value):
        q=DEST/name;q.parent.mkdir(parents=True,exist_ok=True)
        q.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save('SOURCE_MANIFEST.json',dict(schema='current-demo-source-v1',files=rows,file_count=len(rows),
        total_bytes=sum(r['bytes'] for r in rows),source_root='original TeLLMe_FPGA_2026 workspace',
        original_source_bytes_preserved=True,binaries_datasets_credentials_excluded=True))
    save('docs/DEPENDENCIES.json',dict(local_import_edges=edges,external_or_dynamic_imports=sorted(unresolved),
        omitted_current_package_binary_assets=external,
        historical_training_external_dependencies=read(SOURCE_EXPORT/'DEPENDENCY_CLOSURE.json')['original_protocol_noncode_dependencies']))
    save('docs/CURRENT_RECIPE.json',read(SOURCE_EXPORT/'CURRENT_RECIPE.json'))
    (DEST/'README.md').write_text(README,encoding='utf-8')
    (DEST/'docs/OPERATIONS.md').write_text(OPERATIONS,encoding='utf-8')
    (DEST/'docs/PRUNING_DISTILLATION.md').write_bytes((SOURCE_EXPORT/'README_先看这里.md').read_bytes())
    (DEST/'docs/PRUNING_DISTILLATION.md').write_text((DEST/'docs/PRUNING_DISTILLATION.md').read_text(encoding='utf-8').replace('verify_archive.py','tools/verify_sources.py').replace('MANIFEST.json','SOURCE_MANIFEST.json').replace('CURRENT_RECIPE.json','docs/CURRENT_RECIPE.json').replace('DEPENDENCY_CLOSURE.json','docs/DEPENDENCIES.json'),encoding='utf-8')
    (DEST/'tools').mkdir(exist_ok=True)
    (DEST/'tools/verify_sources.py').write_text(VERIFY,encoding='utf-8')
    (OUT/'SNAPSHOT_RECEIPT.json').write_text(json.dumps(dict(status='PREPARED_CURRENT_DEMO_SOURCE_ONLY',source_files=len(rows),
        original_source_bytes=sum(r['bytes'] for r in rows),Python_compile_count=len(scanned),
        manifest_sha256=sha(DEST/'SOURCE_MANIFEST.json'),model_runs=0,board_commands=0,
        destination='https://github.com/3042966866liu-ops/kv260-mage-vl-4b',
        credentials_or_media_included=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print((OUT/'SNAPSHOT_RECEIPT.json').read_text(encoding='utf-8'))

README='''# 当前校园刀具演示源码（2026-10-28）

这里集中保存当前演示链路实际依赖的网页、Windows串口桥、KV260/A53运行时、M455 FPGA内核，以及剪枝和教师学生恢复代码。原文件保留项目相对路径与SHA；根目录旧版本、旧Release和失败历史不因此改写。

## 当前版本

| 项目 | 当前采用 |
|---|---|
| FPGA | M455，Build `0x4D343535`，T32 |
| 结构 | 24视觉块/36语言块 → 10视觉块/18语言块 |
| 输入 | 一张选定采样帧的全局＋中心细节双视图；98视觉token、128总token、4批T32 |
| PS视觉压缩 | V2/V3/V6为3072；V4贡献选组＋恢复至3584 |
| 学习恢复 | V4 fc2重构并导回W4；M542 rank8全词表残差头 |
| 网页 | `apps/campus_guard/live_server.py`，本机8766，实际播放触发新板端请求 |
| 报警 | 新真实Yes显示红色警告；No不显示判断/报警；错误保留未知状态；页面不显示TTFT |

当前任务是“是否可见刀具”的演示研究。每次播放只推理一张明确采样帧，**不是全片逐帧或持续刀具跟踪**。4B模型可用于语义复核；其他问题（如手持关系）未完成本版验收，不能作为已支持功能展示。

## 源码导航

| 内容 | 入口 |
|---|---|
| 网页与上传/任务队列 | [live_server.py](apps/campus_guard/live_server.py)、[server.py](apps/campus_guard/server.py)、[前端](apps/campus_guard/static/playback_live.js) |
| 当前启动与COM3桥 | [start_demo.ps1](apps/campus_guard/start_demo.ps1)、[run_live_worker07.py](apps/campus_guard/run_live_worker07.py)、[live_uart07.ps1](apps/campus_guard/live_uart07.ps1) |
| 实际板端工作器 | [07包](deployment/mage_vl4b/optimization_v1/candidates/M544-campus-live-worker-07/)；`native.py`、`live_protocol.py` |
| PS–PL运行时、权重预取与解析 | [当前运行时](deployment/mage_vl4b/optimization_v1/candidates/M544-freshboot-runtime-05/)及07包中的C解析/语言解析代码 |
| FPGA内核与递归头文件 | [冻结M455 HLS源码](deployment/mage_vl4b/optimization_v1/candidates/M455-dense_output-02/hls/) |
| 当前10V18L结构生成 | [speed_candidates.py](experiments/demo_recovery_20261025/speed_candidates.py) |
| 整层删除与KV索引收缩 | [runtime_demo.py](experiments/fixed_demo_prune_20261025/runtime_demo.py) |
| V4贡献选组、R1、W4恢复 | [fit.py](experiments/v4_recovery_20261025/fit.py) |
| 清晰教师／较难学生与反例回放 | [M542 fit.py](experiments/demo_counterexample_20261026/fit.py) |
| 早期联合蒸馏/LoRA研究 | [train_joint02.py](experiments/augmented_student_20261025/train_joint02.py)，与已部署方法分开 |

详见[剪枝与蒸馏说明](docs/PRUNING_DISTILLATION.md)、[当前精确结构](docs/CURRENT_RECIPE.json)、[操作约束](docs/OPERATIONS.md)。早期文件名中的旧版本是依赖追溯，不代表当前同时执行所有旧方案。

## 无板卡校验

```text
cd current_demo
<你的Python解释器> -B tools/verify_sources.py
```

该命令仅核查原源码SHA、字节数和Python语法，不导入模型、不连接板卡、不发起推理。原代码含Windows/WSL/板端环境固定路径、冻结清单、旧boot身份和不可覆盖输出；它是可审阅的当前源码快照，**并非仅克隆即可执行的一键板端安装包**。

训练需原模型、mixed-bit checkpoint、数据/特征缓存及CUDA环境；A53运行需对应bit/hwh、权重分片、PYNQ/XRT环境和逐级门禁。二进制资产、视频、采样图、人像、SQLite、串口日志、worker token均不上传。外部依赖路径和SHA见[DEPENDENCIES.json](docs/DEPENDENCIES.json)。原包清单包含未随Git上传的资产，缺资产时必须停止，不能删除检查绕过。

## 保存的结果及边界

- M543：六固定采样帧及两条热重复实板通过；热态两次27.633822/27.584494秒，均值27.609158秒；首次请求49.188272秒单列，不含模型加载。它不是与旧版的同场配对提速证据。
- M544：2026-10-28实际视频7采样图的新请求返回Yes、TTFT28.007205秒，网页红警可见；不复用旧结果，不按文件名/播放时间报警。依据各自runs目录原RESULT；模型首次加载、预热和UART准备画面在播放前完成，不计作TTFT。
- 当前07会话配置6小时接受窗口、最多12新任务；CPU/A53过期边界检查通过，未做6小时持续运行验证。
- 固定视频与同源增强用于演示适配，不是独立泛化准确率；旧漏判/误报及被拒方案不改写为成功。

第三方基座、Transformers及FPGA工具的源码/授权范围沿用仓库既有LICENSE_SCOPE、THIRD_PARTY_NOTICES和原文件标注；本快照不重新声明第三方代码或模型权重的许可证。
'''

OPERATIONS='''# 当前源码的运行约束

本次GitHub整理不访问COM3、不加载Overlay、不重新训练或测速，也不改变正在运行的网页或板端进程。

上板顺序固定为Build-ID→单descriptor→单chain→单layer→固定文本E2E→任意输入/Web。任一层失败只在该层排查；保留原返回码和日志，不重跑完整模型来修报告。

控制与授权使用COM3；不使用SSH。Ethernet只用于特定peer的有界哈希校验传输，并恢复临时地址；不得修改原路由、boot、DTB、CMA或稳定回滚。Overlay前须在同一终端确认root、XILINX_XRT=/usr、TMPDIR=/dev/shm、PYNQ-venv的xclbinutil优先、xclProbe()==1、单一PYNQ设备和清单SHA。不用/usr/bin/xclbinutil。

存在未知或失败保留进程时，不自动发信号、free、reset或重载Overlay。07工作器拥有七个缓冲区和COM3时，不能启动第二个桥或串口终端；按正常停止协议完成七owner逆序释放及稳定Overlay/四时钟恢复，再声称退出闭合。

发布配置包含历史boot与SHA，只提供源码身份，不把它当成另一台机器或重启后可沿用的授权。历史故障恢复脚本不是普通启动流程。

Windows本项目原环境无裸python命令，原源码显式使用固定Python与PowerShell路径。WSL应指定Ubuntu-24.04及绝对venv。移植环境应新建版本化合同并按门禁验证，不能静默移除身份/数值/权限检查。
'''

VERIFY='''"""Verify exported source identity only; never import project/hardware modules."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'SOURCE_MANIFEST.json').read_bytes());count=0;total=0
for row in m['files']:
    p=root/row['path'];assert p.resolve().is_relative_to(root)
    b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['path']
    total+=len(b)
    if p.suffix=='.py':compile(b,str(p),'exec');count+=1
assert len(m['files'])==m['file_count'] and total==m['total_bytes']
print('PASS',m['file_count'],'original files;',count,'Python sources compiled; no board/model execution.')
'''
if __name__=='__main__':main()
