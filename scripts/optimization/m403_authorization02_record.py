"""Record renewed same-COM3 authorization from the actual completed precheck."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync


def main():
    log=ROOT/'tmp/m403/sudo_upload_precheck_02.log';text=log.read_text(encoding='utf-8-sig')
    assert 'ubuntu@kria:' in text and '__M403_UPLOAD_SUDO_RC_0__' in text
    value=dict(status='PASS_SAME_COM3_SHELL_SUDO_AUTHORIZATION',log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),sudo_return_code=0,shell_confirmed=True,upload_started=True,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,performance_pass=False)
    out=BASE/'runs/M403-authorization-precheck-02/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_authorization',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h),f'## M403 续期后COM3授权通过（2026-10-04）\n\nSHA {h}；新日志02确认ubuntu@kria shell及同终端sudo rc0，旧无响应日志01/阻塞原字节保持。control03正在manifest-first/900B分块上传，尚未Overlay/模型/FPGA或性能；上传完成逐SHA/三记录后才启动本级轻量ABBABAAB。')
    print(value['status'],h)


if __name__=='__main__':main()
