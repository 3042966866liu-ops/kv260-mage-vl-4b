"""Record completed renewed authorization/assembly from saved COM3 bytes."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync


def main():
    paths=[ROOT/'tmp/m403'/n for n in ('sudo_assembly_precheck_03.log','assembly02_uart.log','root_syntax02_uart.log')]
    wanted=('__M403_RESUME_SUDO_RC_0__','__M403_ASSEMBLY_RC_0__','__M403_SYNTAX_RC_0__')
    for p,marker in zip(paths,wanted):assert marker in p.read_text(encoding='utf-8-sig')
    value=dict(status='PASS_SAME_COM3_ASSEMBLY_AUTHORIZATION',logs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in paths],sudo_return_code=0,assembly_return_code=0,syntax_return_code=0,old_failure_logs_preserved=True,uploaded_files_repeated=0,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,performance_pass=False)
    out=BASE/'runs/M403-assembly-authorization-02/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_authorization',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h),f'## M403 续期后只组装授权完成（2026-10-04）\n\nSHA {h}；同COM3 sudo/现有39载荷完整SHA组装/root bash-n均rc0，原失败日志保持、重传0。传输闭合1cecf0e4c9dd4b0d386378a72b0ec88011ff5076a2ea3e2cf5866527132f2d25已三记录同步；当前尚无Overlay/模型/FPGA或新性能。下一步control03 Run一次轻量ABBABAAB，原run/result存在只收集。')
    print(value['status'],h)


if __name__=='__main__':main()
