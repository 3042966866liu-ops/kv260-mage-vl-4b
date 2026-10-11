"""Record this exact blocked shell precheck; never talks to COM3."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync


def main():
    log=ROOT/'tmp/m403/sudo_upload_precheck_01.log'
    assert not log.read_text(encoding='utf-8-sig').strip()
    value=dict(status='STOP_COM3_SHELL_UNCONFIRMED',log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),controller_return_code=1,shell_confirmed=False,sudo_command_sent=False,sudo_return_code=None,uploaded_files=0,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,new_board_resources=False,performance_pass=False,next_step='Await operator shell confirmation and same COM3 sudo-v; no repeated probe')
    out=BASE/'runs/M403-authorization-precheck-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_authorization',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h),f'## M403 COM3 shell前置阻塞（2026-10-04）\n\nSHA {h}；控制器rc1，COM3五秒内未返回可确认shell，原日志只有空行；shellguard未发sudo/上传/硬件命令，不能推断登录状态或sudo是否过期。39载荷与支持02准备通过，0新资源/模型/FPGA/性能。已请用户确认同COM3 shell并sudo-v续期，等待人工恢复，不重复探测。下一步只control02一次轻量性能。')
    print(value['status'],h)


if __name__=='__main__':main()
