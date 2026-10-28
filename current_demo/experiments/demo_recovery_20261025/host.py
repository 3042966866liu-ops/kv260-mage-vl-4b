from common_recovery import *
import subprocess,os
def main():
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'));out=RUNS/(PREFIX+'-teacher-host-01');assert not out.exists();out.mkdir()
    command=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+relative(HERE/'entry.py')]
    save(out/'START.json',dict(pid=os.getpid(),command=command+['capture'],protocol_sha256=sha(RUNS/(PREFIX+'-protocol-01/RESULT.json'))))
    with (out/'smoke.stdout').open('xb') as stdout,(out/'smoke.stderr').open('xb') as stderr:smoke=subprocess.run(command+['smoke'],stdout=stdout,stderr=stderr,timeout=60)
    assert smoke.returncode==0
    with (out/'stdout.raw').open('xb') as stdout,(out/'stderr.raw').open('xb') as stderr:run=subprocess.run(command+['capture'],stdout=stdout,stderr=stderr,timeout=3900)
    result=RUNS/(PREFIX+'-teacher-capture-01/RESULT.json');v=dict(status='COMPLETE_RECOVERY_TEACHER_HOST' if run.returncode==0 else 'FAIL_RECOVERY_TEACHER_HOST',original_host_rc=run.returncode,stdout_sha256=sha(out/'stdout.raw'),stderr_sha256=sha(out/'stderr.raw'),board_actions=0)
    if result.exists():v.update(native_sha256=sha(result),native_rc=read(result)['original_rc'])
    save(out/'RESULT.json',v)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m524_teacher_host01',dict(status=v['status'],result=relative(out/'RESULT.json'),sha256=h,board=False),'## M524教师层间目标原主机执行\n\nRESULT SHA '+h+'；实际host退出'+str(run.returncode)+'，原stdout/stderr与native结果保全。仅为新蒸馏所需中间输入/输出/kwargs/首分布缓存，0参数训练/板动作/heldout，不当恢复已通过。')
    print(json.dumps(v),flush=True);return run.returncode
if __name__=='__main__':raise SystemExit(main())
