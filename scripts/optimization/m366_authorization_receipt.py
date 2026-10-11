"""Preserve the exact failed COM3 precheck while waiting for human renewal."""
import m351_workflow as w


def main():
    source=w.ROOT/'tmp/m366/sudo_Upload.log'
    raw=source.read_bytes()
    assert b'__M366_SUDO_RC_1__' in raw and b'ubuntu@kria:~$' in raw
    out=w.BASE/'runs/M366-authorization-precheck-01'
    w.atomic(out/'UART.log',raw,immutable=True)
    result=dict(status='WAIT_HUMAN_COM3_SUDO_RENEWAL',build_id='0x4D333537',authorization_return_code=1,raw_precheck_sha256=w.sha(out/'UART.log'),package_uploaded=False,overlay_loads=0,model_forward_calls=0,fpga_transactions=0,prior_single_layer_raw_sha256='54261095541d69f53179f410df76640302e1f146714c52dc8e4ed52274c2771a',next_step='After new human confirmation, check same COM3 once then upload; no retries while unchanged.')
    w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m366_authorization_precheck',dict(status=result['status'],sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix()),f'## M366 固定文本上传前等待授权\n\n前级M365独立单层完整数值/安全释放已PASS并同步；固定文本02包与独立准入离线准备完成。COM3 shell确认，sudo-n一次rc1；0上传/Overlay/forward/FPGA，不重复同阻塞。原预检字节独立保留，证据SHA `{digest}`。已请人工续期；新确认后继续首次固定文本，不自动视频。')
    print(result['status'],digest)


if __name__=='__main__':main()
