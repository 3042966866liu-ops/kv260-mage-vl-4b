"""Collect completed resume02 bootstrap UART bytes; no board entry point."""
import json
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic


def main():
    prep = json.loads((w.BASE/'runs/M443-board-package-preparation-01/RESULT.json').read_bytes())
    directory = w.ROOT/'tmp/m443_board_resume02'
    sudo = (directory/'sudo_bootstrap_renewed02.log').read_text(encoding='utf-8')
    syntax = (directory/'bootstrap_syntax.log').read_text(encoding='utf-8')
    absence = (directory/'bootstrap_absence.log').read_text(encoding='utf-8')
    assert '__M443_BOOT_SUDO_RC_0__' in sudo and 'ubuntu@kria:~$' in sudo
    assert '__M443_BOOT_SYNTAX_RC_0__' in syntax
    assert '__M443_BOOT_ABSENT_RC_0__' in absence
    boot = w.ROOT/prep['bootstrap_path']
    manifest = json.loads((boot/'PACKAGE_MANIFEST.json').read_bytes())
    for name in ['PACKAGE_MANIFEST.json'] + [row['path'] for row in manifest['files']]:
        p = boot/name
        log = (directory/('bootstrap_'+name.replace('.', '_')+'_final.log')).read_text(encoding='utf-8')
        assert 'M212_CHUNKED_FILE_PASS /home/ubuntu/m443_transfer_bootstrap_01/'+name in log
        assert str(p.stat().st_size)+' '+w.sha(p) in log
        assert '__M75C_UART_RC_0__' in log
    old = w.ROOT/'tmp/m443_board/sudo_bootstrap_renewed02.log'
    assert old.read_bytes() == b'\r\n'
    assert w.sha(old) == '7eb70257593da06f682a3ddda54a9d260d4fc514f645237f5ca74b08f8da61a6'
    rows = [dict(path=p.relative_to(w.ROOT).as_posix(), bytes=p.stat().st_size, sha256=w.sha(p))
            for p in sorted(directory.glob('bootstrap_*.log'))]
    rows.append(dict(path=(directory/'sudo_bootstrap_renewed02.log').relative_to(w.ROOT).as_posix(),
                     bytes=(directory/'sudo_bootstrap_renewed02.log').stat().st_size,
                     sha256=w.sha(directory/'sudo_bootstrap_renewed02.log')))
    result = dict(status='PASS_M443_COM3_RESUME_BOOTSTRAP_ONLY02', host_return_code=0,
                  authorization='Human resumed terminal and requested board work; actual sameTTY sudo-n true rc0.',
                  bootstrap_manifest_sha256=prep['bootstrap_manifest_sha256'],
                  transport_manifest_sha256=prep['transport_manifest_sha256'],
                  original_wait_log_sha256=w.sha(old), files=rows,
                  overlay_loaded=False, fpga_transactions=0, configuration_application_accepted=False,
                  configuration_credits_granted=0, promoted=False,
                  next_step='Bounded specific-peer package transfer and original-address restoration, then BuildID only.')
    run = w.BASE/'runs/M443-COM3-resume-bootstrap-02'
    atomic(run/'RESULT.json', w.encoded(result), immutable=True)
    digest = w.sha(run/'RESULT.json')
    w.atomic = atomic
    w.sync('latest_m443_com3_resume_bootstrap02',
           dict(status=result['status'], result=(run/'RESULT.json').relative_to(w.ROOT).as_posix(),
                sha256=digest, overlay_loaded=False, configuration_application_accepted=False),
           '## M443 COM3恢复及启动文件02（2026-10-11）\n\nSHA '+digest+
           '；用户续期并授权上板后，实际正常shell提示符及同TTY sudo-n true rc0，版本02日志保存全部启动文件逐SHA上传与bash语法原rc0。原WAIT证据及两字节日志不改。仅启动文件上传，无Overlay/DMA/新bit配置实证或记账资格。下一步指定peer有界传输及原地址恢复，随后BuildID与新bit同PID/PFN1904页配置申请。')
    print(result['status'], digest, len(rows))


if __name__ == '__main__':
    main()
