"""Preserve revision03 sudo failure; resume only with new authorization log."""
import json
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    log=ROOT/'tmp/m40803/sudo_upload.log';text=log.read_text(encoding='utf-8-sig')
    assert 'ubuntu@kria:' in text and '__M408_SUDO_RC_1__' in text and 'a password is required' in text
    assert not (ROOT/'tmp/m40803/absence.log').exists() and not list((ROOT/'tmp/m40803').glob('upload_*'))
    old=(HERE/'m408_control04.ps1').read_text(encoding='utf-8')
    assert old.count('tmp/m40803/sudo_upload.log')==2
    new=old.replace('tmp/m40803/sudo_upload.log','tmp/m40803/sudo_upload_02.log')
    check='''$resumeEvidence=$board.latest_m408_authorization03
if ((Get-FileHash -LiteralPath (Join-Path $workspace $resumeEvidence.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $resumeEvidence.sha256) { throw 'Resume evidence drift' }
$resume=Get-Content -LiteralPath (Join-Path $workspace $resumeEvidence.result) -Raw -Encoding UTF8 | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $resume.resume_control_sha256) { throw 'Resume control drift' }
'''
    anchor="$support=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m408_local_mlp_support03.result) -Raw -Encoding UTF8 | ConvertFrom-Json\n"
    assert new.count(anchor)==1;new=new.replace(anchor,check+anchor)
    assert new.replace(check,'').replace('tmp/m40803/sudo_upload_02.log','tmp/m40803/sudo_upload.log')==old
    control=HERE/'m408_control05.ps1';atomic(control,new.encode('utf-8'),immutable=True)
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    subprocess.run([ps,'-NoProfile','-File',str(control),'-Mode','SelfTest'],check=True)
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());support=b['latest_m408_local_mlp_support03']
    assert sha(ROOT/support['result'])==support['sha256']
    r=dict(status='BLOCKED_M408_REVISION03_SAME_TERMINAL_SUDO',shell_confirmed=True,sudo_rc=1,
        log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),upload_started=False,
        model_forward_calls=0,overlay_loaded=False,dma_allocations=0,fpga_transactions=0,
        resume_control=control.relative_to(ROOT).as_posix(),resume_control_sha256=sha(control),
        narrow_reverse_difference_checked=True,original_control_package_support_preserved=True,
        original_support_sha256=support['sha256'],human_renewal_required_before_one_new_probe=True,
        source_sha256=sha(HERE/'m408_authorization03.py'),performance_pass=False)
    p=BASE/'runs/M408-authorization-block-03/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m408_authorization03',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),resume_control_sha256=sha(control)),
        f'## M408 修正版03同终端授权阻塞（2026-10-05）\n\nSHA {sha(p)}；shell已确认，sudo原rc1，需要人工续期。'
        '03未上传/模型/Overlay/DMA，原日志保留，不无新回复反复探测。control05只换授权02日志并绑定自身SHA，逆向差分和失败SelfTest通过；'
        '已通过的实际构造、四拒绝及22回收/全部传输配套检查保持。收到人工续期后直接上传一次纯PS捕获/A8局部筛选，无语言或新画像。')
    report='''# 视觉 MLP 隔离候选：本次进度

原矩阵/事务合同保持：第12层 fc1 392×1024→392×4096、fc2 392×4096→392×1024，每项13个T32批，共26逻辑调用；PL数值与速度尚未测试。

前两次捕获均在视觉前向前被插桩准入检查拒绝。第一次未解开原M196精度包装，第二次误要求包装输出FP32。实际冻结构造器已在WSL CPU运行并保存九份源码SHA、两个原矩阵及bias身份、FP32内部/BF16输出关系，0模型forward，对象释放通过；同时纠正CPU store短名称检查。原计算、BF16边界、GELU、Attention、输入、缓存、线程和语言保持。

修正版03已冻结；实际源码包装夹具四种错误拒绝、22项回收负例、有界NPY保存、原字节SHA、结果路径/BOARD键及全部manifest-first/900B回执检查通过。合成夹具和WSL元数据不能证明真实板端质量。

上传前同COM3 sudo已过期，03未上传或运行。人工续期后使用control05直接上传、显式Run一次PS真实输入捕获与局部A8筛选。失败仅留在此级；通过才准备精确FP16/FTZ参考及单descriptor/chain硬件门禁。质量与一个完整MLP段含搬运的净收益均通过才扩大24层。
'''
    atomic(p.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    print('M408_AUTHORIZATION03_PRESERVED',sha(p),sha(control))

if __name__=='__main__':main()
