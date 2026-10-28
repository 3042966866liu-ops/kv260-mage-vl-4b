from common_joint import *
import subprocess
def main():
    out=RUNS/(PREFIX+'-host-02');assert not out.exists();out.mkdir()
    command=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+relative(HERE/'entry02.py')]
    save(out/'START.json',dict(command=command+['train'],protocol_sha256=sha(RUNS/(PREFIX+'-protocol-02/RESULT.json'))))
    with (out/'smoke.stdout').open('xb') as stdout,(out/'smoke.stderr').open('xb') as stderr:r=subprocess.run(command+['smoke'],stdout=stdout,stderr=stderr,timeout=60)
    assert r.returncode==0
    with (out/'stdout.raw').open('xb') as stdout,(out/'stderr.raw').open('xb') as stderr:r=subprocess.run(command+['train'],stdout=stdout,stderr=stderr,timeout=7500)
    file=RUNS/(PREFIX+'-training-02/RESULT.json');v=dict(status='COMPLETE_JOINT_AUGMENTED_STUDENT_HOST' if r.returncode==0 else 'FAIL_JOINT_AUGMENTED_STUDENT_HOST',original_host_rc=r.returncode,native_sha256=sha(file) if file.exists() else None,stdout_sha256=sha(out/'stdout.raw'),stderr_sha256=sha(out/'stderr.raw'),board_actions=0)
    save(out/'RESULT.json',v)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m525_joint_host02',dict(status=v['status'],result=relative(out/'RESULT.json'),sha256=h,board=False),'## M525完整学生渐进增强对照原主机执行\n\nRESULT SHA '+h+'；实际host退出'+str(r.returncode)+'，原stdout/stderr/native保全，0新板/heldout；训练执行完成不当导出或板端质量通过。')
    print(json.dumps(v),flush=True);return r.returncode
if __name__=='__main__':raise SystemExit(main())
