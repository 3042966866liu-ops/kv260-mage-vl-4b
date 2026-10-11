"""Preserve one authorization failure and bind a resume-only new log path."""
import json
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync


def main():
    log = ROOT/'tmp/m408/sudo_upload.log'
    text = log.read_text(encoding='utf-8-sig')
    assert 'ubuntu@kria:' in text and '__M408_SUDO_RC_1__' in text and 'a password is required' in text
    assert not (ROOT/'tmp/m408/absence.log').exists() and not list((ROOT/'tmp/m408').glob('upload_*'))
    old = (HERE/'m408_control.ps1').read_text(encoding='utf-8')
    assert old.count('tmp/m408/sudo_upload.log') == 2
    new = old.replace('tmp/m408/sudo_upload.log','tmp/m408/sudo_upload_02.log')
    check = '''$resumeEvidence=$board.latest_m408_local_mlp_authorization_block
if ((Get-FileHash -LiteralPath (Join-Path $workspace $resumeEvidence.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $resumeEvidence.sha256) { throw 'Resume evidence drift' }
$resume=Get-Content -LiteralPath (Join-Path $workspace $resumeEvidence.result) -Raw -Encoding UTF8 | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $resume.resume_control_sha256) { throw 'Resume control drift' }
'''
    anchor = "$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m408_local_mlp_support.result) -Raw -Encoding UTF8 | ConvertFrom-Json\n"
    assert new.count(anchor) == 1
    new = new.replace(anchor,check+anchor)
    assert new.replace(check,'').replace('tmp/m408/sudo_upload_02.log','tmp/m408/sudo_upload.log') == old
    control = HERE/'m408_control02.ps1'; atomic(control,new.encode('utf-8'),immutable=True)
    ps = 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    subprocess.run([ps,'-NoProfile','-File',str(control),'-Mode','SelfTest'],check=True)
    b = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    support = b['latest_m408_local_mlp_support']; assert sha(ROOT/support['result']) == support['sha256']
    r = dict(status='BLOCKED_M408_SAME_TERMINAL_SUDO',shell_confirmed=True,sudo_rc=1,
        log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),source_sha256=sha(HERE/'m408_authorization_closure.py'),
        upload_started=False,visual_forward_calls=0,overlay_loaded=False,dma_allocations=0,fpga_transactions=0,
        resume_control=control.relative_to(ROOT).as_posix(),resume_control_sha256=sha(control),
        narrow_reverse_difference_checked=True,original_package_and_control_support_preserved=True,
        original_support_sha256=support['sha256'],human_renewal_required_before_one_new_probe=True,
        rejected_offline_fixture='First WSL fixture had int32*FP32 promotion to FP64; corrected fixture explicit FP32. No board effect; actual frozen class checks then PASS',
        performance_pass=False)
    out = BASE/'runs/M408-authorization-block-01/RESULT.json'; atomic(out,encoded(r),immutable=True)
    sync('latest_m408_local_mlp_authorization_block',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),resume_control_sha256=sha(control)),
        f'## M408 上传前同终端授权阻塞（2026-10-05）\n\nSHA {sha(out)}；COM3 shell确认，sudo原rc1，需要人工sudo-v。'
        '尚未上传/捕获/模型/Overlay/DMA；原授权日志保留，无新回复不反复探测。control02仅新授权02日志和自身SHA绑定，逆向差分/SelfTest通过，'
        '原包及实际回收/传输支持保持。收到回复后直接一次上传+纯PS局部筛选，不重复画像或语言。')
    report = '''# 仅视觉MLP两个Linear复用现有并行PL核：当前准备结果

视觉画像已结束。候选只针对第12视觉层的fc1/fc2，现有Build0x4D333537和原W4文件不改；固定最后帧两视图、Attention、原GELU、归一化、语言及稳定服务保持。

| 项目 | fc1 | fc2 |
|---|---:|---:|
| 输入/输出 |392×1024→392×4096|392×4096→392×1024|
| 原W4 G64组 |16|64|
| descriptor |2|1|
| T32调用 |13|13|
| 单调用MM2S字节 |40992|163856|
| 单调用S2MM字节 |524288|131072|

完整一个MLP段26逻辑调用/39descriptor执行；重试及最小Build事务另计。两投影权重暂存共4,456,448B，MM2S2,663,024B，S2MM8,519,680B。可复用七块小缓冲，payload3,440,656B，实际分配对齐和安全余量另查。fc1 shard FIFO8192word恰达已有验证边界；同SHA硬件闭包复用。原M222权重恢复与PL record解释的两个矩阵8,388,608元素逐位一致，原32/8行打包/解析通过。仅离线合同，不是视觉PL PASS。

PL不含bias，输出有FP16/FTZ边界，A8激活也改变原视觉FP32计算。已准备默认关闭的PS捕获/A8-QDQ筛选包：一次原完整视觉保持原SHA，仅保存该层六个有界参考张量，然后同输入原MLP逐位回放与两Linear局部A8回放。原GELU不替换；全输出和残差增量记录cosine、relativeL2、逐token最低cosine、RMSE、maxabs。阈值只是局部拒绝筛选；不证明PL数学或识别语义质量，旧全视觉A8语义2/3拒绝结论保持。

真实WSL Torch CPU执行冻结M207类/原量化器：逐位、13个T32批、zero组、五项错误拒绝、异常/重复捕获与钩子恢复通过。实际有界NPY/file/tensor SHA保存、导出器与回收器早期FAIL/完整PASS、22个回收拒绝、全部900B文件回执及缺失拒绝通过；合成fixture不能冒充真实输入。包11载荷60454B。COM3前置sudo需要密码，包尚未上传，未运行捕获或PL。

下一步人工sudo-v后只运行这一次纯PS捕获/局部筛选。通过并同步后，先生成原FTZ数学的同输入完整参考，再按单descriptor/chain顺序核对PL。一个完整MLP段的CPU/PL比较包含权重读/恢复/复制、A8/pack、DMA、wait/retry、parse、bias、GELU和转换；不能用PL纯kernel与CPU完整段比较。固定预热后ABBABAAB八段，精度、完整段净耗时、资源退出及三记录均成立后才扩大24层；失败停止，不追加测试直到通过。
'''
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    print('M408_AUTHORIZATION_PRESERVED',sha(out),sha(control))


if __name__ == '__main__': main()
