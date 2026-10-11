"""Save a failed precheck, without another UART command."""
import m351_workflow as w


def main():
    raw=(w.ROOT/'tmp/m36603/sudo_Upload.log').read_bytes()
    assert b'__M366_SUDO_RC_1__' in raw and b'ubuntu@kria:~$' in raw
    out=w.BASE/'runs/M366-authorization-precheck-02'
    w.atomic(out/'UART.log',raw,immutable=True)
    result=dict(status='WAIT_HUMAN_COM3_SUDO_RENEWAL',build_id='0x4D333537',authorization_return_code=1,raw_precheck_sha256=w.sha(out/'UART.log'),package_uploaded=False,overlay_loads=0,model_forward_calls=0,fpga_transactions=0,prior_text_failure_sha256='70c31ca1b1f3e0f80e20e29b94f4d5a201fc43c9597fcac6768cf0ac95d025d1',next_step='After new human confirmation check same COM3 once, upload03 then retry only fixed-text accounting level; no video.')
    w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m366_authorization_precheck',dict(status=result['status'],sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix()),f'## M366 固定文本03等待sudo续期\n\n首次固定文本数值SHA一致但8个head物理观察遗漏而FAIL；03实际冻结执行器14项检查通过，原证据与生产规则保持。上传前COM3 shell确认、sudo-n一次rc1；03尚未上传/执行，0新增Overlay/forward/FPGA。原预检字节保存SHA `{digest}`。已请续期，不重复同阻塞。')
    print(result['status'],digest)


if __name__=='__main__':main()
