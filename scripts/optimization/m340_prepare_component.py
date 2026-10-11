"""Freeze component-only candidate, profile attribution and recovery evidence."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path,data):
    import os
    part=path.with_name(path.name+'.m340-part');part.write_bytes(data);os.replace(part,path)


def main():
    package=BASE/'candidates/M340-weight-prefetch-component-01'
    evidence=BASE/'runs/M340-prefetch-offline-01'
    if package.exists() or evidence.exists():raise RuntimeError('Immutable preparation exists')
    recovery={}
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','AGENTS.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        content=(ROOT/name).read_text(encoding='utf-8-sig')
        recovery[name]=dict(sha256=sha(ROOT/name),bytes=(ROOT/name).stat().st_size,lines=len(content.splitlines()))
    profile=BASE/'runs/M339-profile-04-results/PROFILE_SUMMARY.json'
    summary=json.loads(profile.read_text(encoding='utf-8'))
    if summary['status']!='MEASURED_INSTRUMENTED_PREFILL_ONLY' or summary['main_thread_closure_error_ns']!=0:
        raise RuntimeError('Profile attribution failed')
    evidence.mkdir(parents=True)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        shutil.copyfile(ROOT/name,evidence/(Path(name).name+'.before'))
    tests=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_weight_prefetch','test_board_safety'],cwd=HERE,capture_output=True,text=True)
    (evidence/'TEST_OUTPUT.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
    if tests.returncode: raise RuntimeError('Component tests failed; preserved output')
    # Verify that the intended family plan is the actual unchanged M241 order.
    trace=json.loads((profile.parent/'prefill_trace.json').read_text(encoding='utf-8'))
    families=[(row['metadata']['layer'],row['metadata']['family']) for row in trace['trace']['events'] if row['name']=='language_family']
    intended=[]
    for layer in range(36):
        intended.extend((layer,family) for family in (('q','kv') if layer<10 else ('qkv',))+('attention_out','gate_up','mlp_down'))
    if families!=intended or len(families)!=154: raise RuntimeError('Plan differs from real M241 trace')
    package.mkdir(parents=True)
    names=('weight_prefetch.py','board_safety.py','test_weight_prefetch.py','m340_component_probe.py')
    for name in names:
        ast.parse((HERE/name).read_text(encoding='utf-8'));shutil.copyfile(HERE/name,package/name)
    runner='''#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?exact manifest hash required}
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e COMPONENT_RESULT.json ]] || { echo M340_IMMUTABLE_RESULT_EXISTS >&2; exit 2; }
set +e
/usr/local/share/pynq-venv/bin/python3 -B ./m340_component_probe.py "$manifest_sha"
gate_rc=$?
set -e
printf 'M340_CPU_ONLY_DONE gate_rc=%s\\n' "$gate_rc"
exit "$gate_rc"
'''
    (package/'run_m340_component.sh').write_text(runner,encoding='utf-8',newline='\n')
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(package.iterdir())]
    (package/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in rows),encoding='utf-8',newline='\n')
    rows.append(dict(path='SHA256SUMS',bytes=(package/'SHA256SUMS').stat().st_size,sha256=sha(package/'SHA256SUMS')))
    manifest=dict(schema='tellme-m340-component-only-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
                  hardware_changed=False,hardware_gate_allowed=False,performance_pass=False)
    (package/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    result=dict(status='PASS_OFFLINE_WEIGHT_PREFETCH_COMPONENT_ONLY',evidence_level='L0',build_id='0x4D395832',
                recovery_sources=recovery,profile_summary_sha256=sha(profile),tests_passed=13,
                family_plan_matches_measured_trace=True,language_stages=154,expected_head_stages=8,
                extra_cma_bytes=27852800,minimum_reserve_bytes=64<<20,cma_board_snapshot_pending=True,
                package=package.relative_to(ROOT).as_posix(),package_manifest_sha256=sha(package/'PACKAGE_MANIFEST.json'),
                new_hardware=False,model_math_changed=False,performance_pass=False,full_request_numeric_acceptance=False,
                rejection_history=['M339 Windows collector default GBK rejected UTF-8 result; fixed explicit UTF-8 and resumed exact hash-checked bytes without board rerun',
                                   'M339 preflight controller timed out at150s during asset hashing; waited/captured completion, did not rerun gate'],
                next_step='CPU-only PYNQ-Python component tests and idle CMA snapshot; then frozen-source/unchanged RTL evidence closure and Build-ID-only -> descriptor -> chain -> layer -> fixed-text -> fixed159 video numerical and balanced A/B gates')
    atomic(evidence/'RESULT.json',(json.dumps(result,indent=2)+'\n').encode())
    board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board=json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_m339_profile_attribution']=dict(status=summary['status'],summary=profile.relative_to(ROOT).as_posix(),sha256=sha(profile),performance_pass=False)
    board['latest_m340_offline_component']=dict(status=result['status'],result=(evidence/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(evidence/'RESULT.json'),board_run=False,performance_pass=False)
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode())
    note=('## M340 权重双缓冲预取：离线组件完成（2026-10-01）\n\n'
          'M339 固定159-Token画像归因闭合误差0ns：语言Prefill155.896s，主线程设备等待104.691s、文件读取24.830s、CMA复制1.122s、同步0.118s；后台准备/解析不可叠加。'
          '过程I/O read_bytes约376.5MB，并非全2.035GB均读microSD；不能把设备等待当纯PL计算。'
          'FPGA证明778逻辑/781物理调用、3次保护重试，末态AP_CTRL=4、两DMA状态4098，安全释放；首Token202.533s，仅插桩诊断不是性能验收。'
          '归因证据 `'+profile.relative_to(ROOT).as_posix()+'` SHA `'+sha(profile)+'`。'
          '新 `weight_prefetch.py` 仅改变PS调度，第二组四缓冲与原组交替，原复制/同步函数不变；前景使用前等待后台、复用前检查双方DMA/内核空闲、顺序身份错或超时无静默回退、活跃设备/工作线程保留缓冲。'
          '最大额外CMA27,852,800B（26.5625MiB），另需64MiB余量且真实runtime分配后重测；当前尚未验证板端分配。13项组件/安全测试通过（含实际最大窗口、短读、顺序错、部分分配失败、DMA忙及线程超时），仅L0，无FPGA候选数值或提速结论。'
          '证据 `'+(evidence/'RESULT.json').relative_to(ROOT).as_posix()+'` SHA `'+sha(evidence/'RESULT.json')+'`；隔离CPU-only包manifest `'+sha(package/'PACKAGE_MANIFEST.json')+'`。'
          '拒绝记录：M339回收UTF-8被Windows默认GBK误解，显式编码修复后复用板端原始哈希字节，未重跑；150s预检控制器超时只等待回收完成，未重跑模型。'
          '稳定Build/回滚/boot/DTB/CMA配置不变。下一步板端CPU组件测试和只读CMA快照，再按固定门禁序验证候选，完整数值/交错A/B通过前不晋级。\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        path=ROOT/name;heading,rest=path.read_text(encoding='utf-8-sig').split('\n',1)
        atomic(path,(heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(json.dumps(dict(status=result['status'],manifest_sha=result['package_manifest_sha256'],file_count=len(rows),bytes=manifest['total_bytes'])))


if __name__=='__main__':main()
