"""Freeze the already tested offline scope; not an executable board package."""
import ast
import json
from m351_workflow import ROOT,BASE,HERE,sha,atomic,encoded,sync

def main():
    out=BASE/'runs/M397-last-layer-tail-preparation-01'
    pkg=BASE/'candidates/M397-last-layer-tail-scope-01'
    if out.exists() or pkg.exists():raise RuntimeError('Immutable preparation already exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    audit=board['latest_m396_last_layer_tail_audit'];a=ROOT/audit['result']
    assert sha(a)==audit['sha256']=='f6ffc560988c79087bd4be8f5200945d89c4af701abdad6e64327505b10be56a'
    assert all(audit['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    sources={n:sha(HERE/n) for n in ('m397_last_layer_tail_scope.py','test_m397_last_layer_tail.py','m397_prepare.py')}
    for n in sources:ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    original=json.loads(a.read_text(encoding='utf-8'))
    for x in original['verified_frozen_files']:
        p=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'/x['path']
        assert sha(p)==x['sha256']
    plan='''# M397 末层最后T32批隔离组件

默认关闭。只有显式enabled=True才能建立scope，固定30/159输入准入；绑定到原M241完整文件SHA，原源码不变。组件只有一处控制注入：最后一层完整Attention结束后，同时选attended和residual的原最后T32批。去掉该注入的AST与原函数严格相同。原RMS、SiLU、三个family、原M238打包/解析/重试、LM head和全部K/V保持。

这是离线组件包，**没有board runner、控制器或上板授权检查，不能直接上传运行**。13项Windows离线检查使用真实冻结函数和真实尺寸合成激活，Linear权重/输出、Attention、MMIO/内存准入明确是替身。没有真实模型数值或性能证据。

## 下一项：末层真实输入参考

1. 先核对原M368参考及后续原完整family哈希、已有板端资产是否包含末层数组；不能从全159哈希推出末31数组。M390只有layer0的gate/up，不够。仅缺失的末层数据才捕获。
2. 若确实缺失，准备一次独立原路径捕获：同固定视频、原输入/量化/原单parser，保存layer35完整Attention后的attended和residual、三处最后31输入/输出、最后hidden、全logits和72KV的原SHA。复用原完整reference校验。分开的捕获不得计为性能测试。完整大数组按明确白名单/字节预算保存在板端，COM3回收所需小结果与文件SHA；避免把全部数组通过UART。
3. 捕获前，runner/导入闭包/收集故意失败检查、实际旧远程根/manifest身份、root/XRT/PYNQ环境等一次通过。仍用已授权COM3；若sudo失效停止并要求续期。失败只回收，不重跑补日志。

## 数值门禁

实际原输入fixture上，先逐一核对layer35三个tail chain的输入打包、权重字节、完整32行原FIFO输出长度/TLAST/寄存器及保留31输出，原scale/重试不变。继承同Build0x4D333537/同SHA硬件47项证据，不改RTL。

再验证单层尾部：完整QKV/RoPE/Attention和全部K/V保持，只三个后投影裁剪；检查最后hidden/完整logits/缓存并安全退出。前层输出不变，末层family输出只与原末31参考比较，绝不和原159整体SHA直接比较。

固定30文本原计划无裁剪，原162逻辑不变。原159视频改为766逻辑；按已有相同输入推导767物理，实际记录每次重试，第6层1次仍保留。始终physical=logical+retry；minimal事务单独算。宏计数和I/O字节按实际逐chain重推，不沿用原778常数。原视频engine proof期望778，须准备隔离范围的计数绑定并测试恢复，原生产expected函数/服务不修改。

七块原DMA驻留后封锁新增DMA；组件不申请DMA、PSslot或额外SiLUworkspace。完整原159预算仍用已验证独立诊断1GiB普通RSS增长预算与64MiB普通可用内存余量，逐视觉/语言/LM head/实际提交观察，不能由减少数组断言真实峰值通过。原生产64MiB CMA准入保持。worker/当前pending未结束或任何硬件/数值异常时保留原进程、scope、所有DMA缓冲；不得timeout kill/free。成功后原输出future全部结束、原DMA完成及safe判据成立，清除scope namespace callback，验证owner释放，再依原逆序释放七DMA并恢复稳定Overlay。

裁剪后不再对已丢弃的末层hidden行做后续finite检查。这是首轮固定输入的显式语义范围，不能把任意异常输入错误检测称为完全等价；其他生产消费者不自动接入。

## 性能与关闭条件

完整视频数值与三份记录同步才解锁轻量ABBABAAB完整请求，保持同输入、并行核、单parser、原SiLU、PS预读关闭。捕获/数组哈希放到原请求计时外，绑定/调度/原剩余计算必须在计时内。记录自然缓存与逐次读盘，不清缓存。沿用原保守净收益判据，不因少12次名义调用而直接PASS。容量/生命周期/数值失败停当前级；两种顺序无稳定净收益就关闭此变体，不扫描尾部长度或继续重复旧对照。
'''
    pkg.mkdir(parents=True)
    atomic(pkg/'m397_last_layer_tail_scope.py',(HERE/'m397_last_layer_tail_scope.py').read_bytes(),immutable=True)
    atomic(pkg/'AUDIT_PREREQUISITE.json',encoded(dict(audit_sha256=audit['sha256'],source_sha256=original['resolved_modules'],board_ready=False)),immutable=True)
    atomic(pkg/'VALIDATION_PLAN.md',plan.encode('utf-8'),immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(pkg.iterdir())]
    atomic(pkg/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'),immutable=True)
    p=pkg/'SHA256SUMS';rows.append(dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)))
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(dict(schema='m397-offline-tail-scope-v1',board_ready=False,files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))),immutable=True)
    assert {p.name for p in pkg.iterdir()}=={x['path'] for x in rows}|{'PACKAGE_MANIFEST.json'}
    for x in rows:assert sha(pkg/x['path'])==x['sha256']
    assert not list(pkg.rglob('*.pyc')) and not list(pkg.rglob('__pycache__'))
    tests='.............\n----------------------------------------------------------------------\nRan 13 tests in 6.360s\n\nOK\n'
    atomic(out/'TEST_OUTPUT.txt',tests.encode('utf-8'),immutable=True)
    result=dict(status='PASS_OFFLINE_LAST_LAYER_TAIL_SCOPE_ONLY',evidence_level='L0_SOURCE_COMPONENT_ONLY',
                audit_sha256=audit['sha256'],build_id='0x4D333537',source_sha256=sources,
                tests_run=13,test_exit_code=0,test_record_source='Recorded stdout/stderr of completed explicit Python invocation in current task; no board test',
                python310_syntax=True,ast_remove_one_injection_equals_original=True,
                real_frozen_functions=['M241.prefill','rms_norm','apply_rope','silu','quantize_t32','pack_chain_input','M236._parse_into_and_check','M236._resolve_pending'],
                explicit_test_fakes=['Weights/Linear outputs','Attention output','DMA/MMIO','Memory admission'],
                real_model_input=False,real_model_numerical_proven=False,scope_default_disabled=True,allowed_fixed_tokens=[30,159],
                original_logical=778,candidate_logical=766,conditional_physical=767,extra_dma_allocations=0,
                candidate_manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),package_files=len(rows),package_bytes=sum(x['bytes'] for x in rows),
                board_ready=False,board_run=False,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
                stable_service_changed=False,production_admission_changed=False,
                rejected_attempts=['Offline retry extraction initially omitted original future annotations, yielding NameError _PendingBlock. Test-only extractor restores original postponed-annotation semantics before 13 final PASS checks. No release/candidate math or board action was changed.'],
                next_step='Read existing original tail tensor availability; prepare only missing same-input last-layer capture and isolated chain gate, without running full video/performance first')
    atomic(out/'RESULT.json',encoded(result),immutable=True);h=sha(out/'RESULT.json')
    report=f'# M397 离线末层裁剪组件\n\n13项离线检查PASS，仅L0；真实冻结M241控制、真实尺寸合成激活、RMS/RoPE/SiLU、packet/scale/parser/retry；Linear/Attention/准入为明确替身，非板端数值或性能PASS。\n\n默认关闭，无新增DMA/PSslot，无生产源码/计数/服务改动。只在最后一层完整Attention后同时选attended/residual末批；删除该注入的AST严格恢复原函数。固定30不裁剪；固定159预期766逻辑，原重试保持时767物理。失败保留owner/callback，不free或kill；成功关闭消除callback，拒绝旧绑定和重复请求。\n\n包manifest `{result["candidate_manifest_sha256"]}`，{len(rows)}载荷/{result["package_bytes"]}B；仅组件和验证计划，未包含上板runner。下一步获取缺失的真实末层切片参考，再逐级数值，不执行完整性能对照。\n\n准备SHA `{h}`；审计SHA `{audit["sha256"]}`。\n'
    atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m397_last_layer_tail_preparation',dict(status=result['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=h,build_id='0x4D333537',manifest_sha256=result['candidate_manifest_sha256'],board_ready=False,board_run=False,numerical_pass=False,performance_pass=False,formal_promotion_allowed=False),
         f'## M397 末层末批隔离组件离线通过（2026-10-04）\n\n准备SHA `{h}`，manifest `{result["candidate_manifest_sha256"]}`；13项实际冻结函数/真实尺寸合成输入检查、原future注解修复后PASS，删除唯一注入的AST恢复原M241。Linear/Attention/内存为明确测试替身，仅L0，未上传/上板或完整模型数值/性能。默认关闭，固定159末层三投影保留31行，计划766逻辑/条件767物理；固定30不裁剪，完整72KV/词表输出保持。无新DMA/slot，失败保留owner，关闭恢复callback，原单parser/原SiLU，PS预读关闭。原生产准入/计数/服务/硬件/稳定回滚不变，原40.81%独立保持。下一步仅核对真实末层数据是否已有，补缺失参考和隔离chain门禁；不会由离线替身结果直接进入视频性能。')
    print(json.dumps(dict(status=result['status'],sha256=h,manifest_sha256=result['candidate_manifest_sha256'],report=str(out/'REPORT.md'))))

if __name__=='__main__':main()
