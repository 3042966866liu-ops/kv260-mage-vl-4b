"""Preserve one failed COM3 authorization check without running a board gate."""
import m351_workflow as w


def main():
    log = w.ROOT / 'tmp/m365/sudo_Upload.log'
    text = log.read_text(encoding='utf-8-sig')
    assert '__M365_SUDO_RC_1__' in text
    assert 'ubuntu@kria:~$' in text
    result = dict(
        status='WAIT_HUMAN_COM3_SUDO_RENEWAL',
        build_id='0x4D333537',
        authorization_return_code=1,
        log=log.relative_to(w.ROOT).as_posix(),
        log_sha256=w.sha(log),
        manifest_sha256='2b0b5c51f1b28dd83628a8b15adfafe229d6a2536ecb60f9ba4eb2c782b4190a',
        package_uploaded=False,
        overlay_loads=0,
        model_forward_calls=0,
        fpga_transactions=0,
        numerical_pass=False,
        performance_pass=False,
        production_policy_changed=False,
        next_step='After a new human recovery confirmation, check same COM3 sudo once and upload; do not retry the current block.',
    )
    out = w.BASE / 'runs/M365-authorization-precheck-02/RESULT.json'
    w.atomic(out, w.encoded(result), immutable=True)
    digest = w.sha(out)
    w.sync('latest_m365_authorization_precheck', dict(
        status=result['status'], result=out.relative_to(w.ROOT).as_posix(), sha256=digest,
        board_gate_executed=False,
    ), f'## M365 上传前授权检查暂停\n\nCOM3 shell已确认；收到人工续期确认后的一次sudo-n检查仍rc1，未上传/加载Overlay/执行单层或FPGA。独立规则与冻结02包保留，生产64MiB不改。证据SHA `{digest}`。已请人工同COM3续期；新确认前不重复检查，之后只继续上传及首次单层诊断。')
    print(result['status'], digest)


if __name__ == '__main__':
    main()
