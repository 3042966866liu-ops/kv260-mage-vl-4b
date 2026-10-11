"""Offline audit of frozen loading sources. Does not import the board runtime."""
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
RUN = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M348-loading-path-audit-01'
PRIOR = 'de66152ad095d677f4d3c605fe9462b785697d51eacc63d76b6d660505360d63'
INSTALL_SHA = 'fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e'
NEXT = ('仅准备隔离且默认关闭的O_DIRECT只读哈希组件和无Overlay小文件门禁；'
        '先核对实际kernel/fs、对齐、空文件、非对齐尾块、短读/错误、文件身份和无静默buffered回退。'
        '候选目标仅发布preflight中的BF16视觉文件及wheel归档，保留35项原检查和全文件SHA；'
        'W4分片、embedding及后续mmap/暂存消费者不改。未证明直接I/O能力则拒绝路线。'
        '不清缓存、不fadvise驱逐、不加载模型/Overlay；真实完整runtime的90.5625MiB门槛仍未通过。')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def atomic(path, data, immutable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        assert path.read_bytes() == data, 'Immutable evidence differs: ' + str(path)
        return
    part = path.with_name(path.name + '.m348-part')
    with part.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(part, path)


def main():
    recovery = {}
    texts = {}
    for name in ('CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        raw = (ROOT / name).read_bytes()
        texts[name] = raw.decode('utf-8-sig')  # Complete authoritative files, explicit encoding.
        recovery[name] = dict(bytes=len(raw), sha256=sha(raw), lines=len(texts[name].splitlines()))
    board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    assert board['latest_m347_asset_memory']['sha256'] == PRIOR
    assert all(PRIOR in texts[name] for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    prior_raw = (ROOT / board['latest_m347_asset_memory']['result']).read_bytes()
    assert sha(prior_raw) == PRIOR
    prior = json.loads(prior_raw)
    assert prior['status'] == 'PASS_ASSET_HASH_MEMORY_DIAGNOSTIC' and len(prior['files']) == 35
    assert not prior['overlay_loaded'] and prior['fpga_transactions'] == prior['model_forward_calls'] == 0
    manifest_bytes = (STAGE / 'INSTALL_PACKAGE_MANIFEST.json').read_bytes()
    assert sha(manifest_bytes) == INSTALL_SHA
    manifest = {row['path']: row for row in json.loads(manifest_bytes)['files']}
    closure_path = ROOT / 'deployment/mage_vl4b/optimization_v1/candidates/M346-load-memory-01/SOURCE_CLOSURE.json'
    closure_raw = closure_path.read_bytes()
    closure = json.loads(closure_raw)
    assert closure['recursive_missing_project'] == []
    rows = list(closure['files'])
    dynamic = ['deployment/mage_vl4b/m181_m120_video_board_candidate/ps_vision_payload/' + name
               for name in ('modeling_mage_vl.py', 'configuration_mage_vl.py')]
    for name in dynamic:
        assert name in manifest
        rows.append(manifest[name])
    sources = {}
    verified = []
    inventory = []
    snippets = []
    watched = {'digest', 'sha256', 'read', 'readinto', 'read_bytes', 'mmap', 'memmap',
               'load_file', 'from_pretrained', 'copy_window_to_buffer', 'verify_layout'}
    selected = {'preflight': {'digest', 'inspect'},
                'video_server': {'offline_preflight', 'make_config'},
                'm243_video_server': {'load'},
                'm261_budgeted_w4_runtime': {'__init__'},
                'm260_cached_w4_runtime': {'__init__'},
                'm258_vectorized_w4_runtime': {'__init__'},
                'm222_vectorized_w4_runtime': {'__init__'},
                'm207_ps_vision_runtime': {'__init__'},
                'ps_vision_runtime': {'sha256', '__init__'},
                'board_runtime': {'sha256', 'verify_layout', 'copy_window_to_buffer', '__init__'},
                'video_language_runtime': {'sha256', '__init__'},
                'modeling_mage_vl': {'MageVLVisionPretrainedModel'}}
    for row in rows:
        rel = row['path']
        path = ROOT / rel
        if not path.is_file():
            path = STAGE / rel
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], rel
        verified.append(dict(path=rel, bytes=len(raw), sha256=sha(raw),
                             local_source=path.relative_to(ROOT).as_posix()))
        if path.suffix != '.py':
            continue
        source = raw.decode('utf-8-sig')
        sources[rel] = source
        tree = ast.parse(source, filename=rel)
        owners = {}
        def visit(node, owner='module'):
            current = owner
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                current = (owner + '.' if owner != 'module' else '') + node.name
            owners[id(node)] = current
            for child in ast.iter_child_nodes(node):
                visit(child, current)
        visit(tree)
        lines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, 'id', getattr(node.func, 'attr', ''))
                if name in watched:
                    inventory.append(dict(path=rel, line=node.lineno, owner=owners[id(node)],
                                          call=ast.get_source_segment(source, node)))
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in selected.get(path.stem, set()):
                snippets.append(dict(path=rel, first_line=node.lineno, last_line=node.end_lineno,
                                     owner=owners[id(node)], source='\n'.join(lines[node.lineno-1:node.end_lineno])))
    # Scan all frozen sources, including unused helpers; pin every matching line.
    mentions = []
    bindings = []
    for rel, source in sources.items():
        for number, line in enumerate(source.splitlines(), 1):
            if any(term in line for term in ('vision_bf16', 'vision_weights', 'runtime_wheel', 'safetensors', 'POSIX_FADV_DONTNEED')):
                mentions.append(dict(path=rel, line=number, source=line))
            if any(term in line for term in ('class M273', 'class M261', 'class M260', 'class M259',
                    'class M258', 'class M222', 'class M207', 'class M90',
                    'M222PSVisionRuntime =', 'M222VectorizedFourPortW4Store =',
                    'FourPortW4Store =', 'M273LatestPSVisionRuntime', 'model_code_root', 'staged-low-cma')):
                bindings.append(dict(path=rel, line=number, source=line))
    modules = closure['modules']
    assert modules['video_server'] == 'tmp/m223_realtime/m223_realtime_delta/video_server.py'
    preflight = sources['scripts/preflight.py']
    assert 'vision_bf16.safetensors' in preflight and 'runtime_wheel_bundle' in preflight
    ps = sources[modules['ps_vision_runtime']]
    assert 'MageVLVisionPretrainedModel(config.vision_config)' in ps
    assert 'mmap.mmap' in ps and 'blob_path.read_bytes()' in ps
    assert 'vision_bf16' not in ps
    server = sources[modules['video_server']]
    assert 'vision_bf16' not in server and 'runtime_wheel' not in server
    model = sources[dynamic[0]]
    model_tree = ast.parse(model)
    vision_class = next(n for n in model_tree.body if isinstance(n, ast.ClassDef) and n.name == 'MageVLVisionPretrainedModel')
    ctor = next(n for n in vision_class.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    ctor_source = ast.get_source_segment(model, ctor)
    assert all(term not in ctor_source for term in ('load_file', 'from_pretrained', 'safetensors'))
    scope = [dict(name='vision_weights', role='Release preflight full-SHA only in selected frozen load path',
                  later_consumer='W4 four-port mmap plus small raw auxiliary; no full BF16 load', eligible_for_small_io_candidate=True),
             dict(name='runtime_wheel_bundle', role='Release preflight full-SHA; installed runtime_site imports',
                  later_consumer='Archive installation is outside the audited serving/load path', eligible_for_small_io_candidate=True),
             dict(name='language/head W4 shards', role='Release hash then runtime verify_layout hash',
                  later_consumer='Original staged-low-cma window reads', eligible_for_small_io_candidate=False),
             dict(name='vision W4 shards', role='Release hash then FourPortW4Store hash',
                  later_consumer='Read-only mmap and vectorized decode', eligible_for_small_io_candidate=False),
             dict(name='embedding/norm/raw auxiliary', role='Release and constructor SHA checks',
                  later_consumer='np.memmap, np.load, raw read_bytes respectively', eligible_for_small_io_candidate=False)]
    scope[0].update(asset=next(r for r in prior['files'] if r['name'] == 'vision_weights'))
    scope[1].update(asset=next(r for r in prior['files'] if r['name'] == 'runtime_wheel_bundle'))
    audit = dict(status='PASS_OFFLINE_LOADING_PATH_AUDIT', evidence_level='L0_SOURCE_AUDIT_ONLY',
                 build_id='0x4D395832', board_run=False, overlay_loaded=False, model_forward_calls=0,
                 fpga_transactions=0, prior_raw_sha256=PRIOR, installed_manifest_sha256=INSTALL_SHA,
                 frozen_source_closure_sha256=sha(closure_raw), verified_source_files=verified,
                 module_resolution=modules, dynamic_model_sources=dynamic, io_call_inventory=inventory,
                 target_literal_mentions=mentions, constructor_bindings=bindings,
                 constructor_evidence=snippets, candidate_scope=scope,
                 gate_plan_sha256=sha((RUN / 'SMALL_COMPONENT_GATE_PLAN.md').read_bytes()),
                 audit_script_sha256=sha(Path(__file__).read_bytes()),
                 source_audit_limit='Selected frozen M276/M273/M238/M241 load path; external libraries are not executed. Not a global absence proof, kernel I/O proof, or file-page ownership proof.',
                 io_candidate_status='PLAN_ONLY_NOT_IMPLEMENTED_OR_BOARD_TESTED',
                 rejected_routes=['Whole-runtime O_DIRECT substitution: later mmap/staging consumers exist.',
                                  'Skip SHA/checks, evict cache, alter stable source or lower CMA reserve.',
                                  'Claim direct mode from O_DIRECT flags alone; filesystem can silently fall back.',
                                  'Claim capacity/performance from offline source audit.'],
                 required_cma_free_bytes=94961664, memory_capacity_proven=False,
                 numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,
                 next_step=NEXT)
    data = encoded(audit)
    atomic(RUN / 'RESULT.json', data, immutable=True)
    audit_sha = sha(data)
    report = ('# M348 冻结加载路径审计\n\n'
              '审计通过，等级L0，仅离线源码证据。稳定Build `0x4D395832`，未访问COM3或加载Overlay。\n\n'
              f'复核{len(verified)}份冻结文件（其中两份动态模型源码从已安装包清单补齐），并逐调用记录哈希和后续读取。\n\n'
              '| 资产 | 当前加载路径 | 候选范围 |\n| --- | --- | --- |\n'
              '| BF16视觉整文件 | 发布preflight全文件SHA；实际视觉创建空模型，使用W4 mmap与小型原始参数 | 可准备隔离哈希组件 |\n'
              '| wheel归档 | 发布preflight全文件SHA；当前依赖从runtime_site导入 | 可准备隔离哈希组件 |\n'
              '| 视觉W4分片 | 哈希后mmap | 保持原路径 |\n'
              '| 语言/LM head W4分片 | 发布及运行时两次校验，后续按窗口暂存 | 保持原路径 |\n'
              '| embedding、norm、视觉原始参数 | 哈希后memmap/load/read_bytes | 保持原路径 |\n\n'
              '最终video_server解析到tmp/m223_realtime/m223_realtime_delta/video_server.py；'
              'M273→M261→M258→M222→M207→M90视觉构造链已核对。动态MageVLVisionPretrainedModel构造函数不调用完整权重from_pretrained。'
              'modeling_mage_vl中的safetensors读取属于未选中的StreamMind条件生成路径，不能混为当前视觉加载。\n\n'
              '以上限定于冻结的当前加载路径，不代表这些资产在安装或其他模型路径永远无人读取。'
              'M347的CMA变化仍只是系统级区间观察，未证明直接I/O可以改善容量。\n\n'
              f'证据RESULT.json SHA `{audit_sha}`；全部源SHA、调用位置、源码摘录和排除理由均在JSON中。\n\n'
              '下一步：' + NEXT + '\n\n'
              '组件门禁准备规格见SMALL_COMPONENT_GATE_PLAN.md。该规格没有执行记录；O_DIRECT代码尚未实现。\n')
    atomic(RUN / 'REPORT.md', report.encode('utf-8'), immutable=True)
    # Source audit is an offline update; preserve every historical board gate and all promotion flags.
    board['latest_m348_loading_path_audit'] = dict(status=audit['status'], evidence_level=audit['evidence_level'],
        build_id=audit['build_id'], result=(RUN / 'RESULT.json').relative_to(ROOT).as_posix(), sha256=audit_sha,
        verified_files=len(verified), board_run=False, memory_capacity_proven=False, performance_pass=False,
        candidate_state='SUSPENDED_AT_VIDEO_CMA_FAILURE', next_step=NEXT)
    atomic(board_path, encoded(board))
    note = ('## M348 加载路径审计：哈希候选限定到两项校验专用资产（2026-10-01）\n\n'
            f'稳定Build `0x4D395832`，{len(verified)}份冻结文件同SHA（含两份补齐的动态模型源码），'
            '仅L0源码审计，无COM3/Overlay/模型forward/FPGA事务。当前视觉加载使用W4分片mmap和小型原始参数，'
            '完整BF16视觉文件及wheel归档在所选冻结加载路径中用于发布preflight全文件SHA。'
            'W4分片、embedding等有后续mmap/暂存消费者，不纳入直接I/O候选；原35项检查及全文件SHA保持。'
            'O_DIRECT仍为未实现、未上板且默认关闭的方案；只准备小文件门禁规格，不证明容量或提速。'
            '拒绝整路径替换、skip hash、清缓存及仅凭flags宣称无回退。'
            '原90.5625MiB门槛/64MiB余量、稳定源码/服务/回滚/boot/DTB/CMA保持，双bank候选停视频CMA失败级。'
            f'证据 `{(RUN / "RESULT.json").relative_to(ROOT).as_posix()}` SHA `{audit_sha}`。下一步：{NEXT}\n\n')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        old = (ROOT / name).read_text(encoding='utf-8-sig')
        if audit_sha not in old:
            heading, rest = old.split('\n', 1)
            atomic(ROOT / name, (heading + '\n\n' + note + rest.lstrip('\n')).encode('utf-8'))
    assert sha((RUN / 'RESULT.json').read_bytes()) == audit_sha
    assert json.loads(board_path.read_text(encoding='utf-8'))['latest_m348_loading_path_audit']['sha256'] == audit_sha
    assert all(audit_sha in (ROOT / name).read_text(encoding='utf-8') for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    if not (RUN / 'RECOVERY_READ_BEFORE.json').exists():
        atomic(RUN / 'RECOVERY_READ_BEFORE.json', encoded(recovery), immutable=True)
    print(json.dumps(dict(status='M348_OFFLINE_AUDIT_SYNCHRONIZED', result_sha256=audit_sha,
                          verified_files=len(verified), io_calls=len(inventory), board_run=False)))


if __name__ == '__main__':
    main()
