"""Single explicit WSL stage; preserve primary exit and complete raw logs."""
import subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_v4 import *
def main():
    stage=sys.argv[1];assert stage in ('fit','quality');p=verify()
    out=RUNS/('M536-V4-3584-recovery-'+stage+'-host-01');out.mkdir(exist_ok=False)
    script=HERE/(stage+'.py');cmd=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B',
        '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+rel(script)]
    save(out/'START.json',dict(command=cmd,source_sha256=sha(script),protocol_sha256=sha(PROTOCOL)))
    with (out/'stdout.raw').open('xb') as a,(out/'stderr.raw').open('xb') as b:
        rc=subprocess.run(cmd,stdout=a,stderr=b,timeout=p['budgets'][stage+'_seconds']+120).returncode
    native=(FIT if stage=='fit' else RUNS/'M536-V4-3584-recovery-quality-01')/'RESULT.json'
    v=dict(status='COMPLETE_M536_'+stage.upper()+'_HOST' if rc==0 else 'FAIL_M536_'+stage.upper()+'_HOST',host_rc=rc,
        native_sha256=sha(native) if native.exists() else None,stdout_sha256=sha(out/'stdout.raw'),stderr_sha256=sha(out/'stderr.raw'),board_commands=0)
    save(out/'RESULT.json',v)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m536_v4_'+stage+'_host01',dict(status=v['status'],result=rel(out/'RESULT.json'),sha256=h,board=False,promoted=False),
        '## M536视觉V4 3584 '+stage+'原执行\n\nRESULT SHA '+h+'；实际host '+str(rc)+'，原stdout/stderr/native按SHA保持。仅当前V4恢复，0板命令/heldout；不以训练损失或本级完成当整机质量/TTFT通过。')
    print(v,flush=True)
    if rc:print((out/'stdout.raw').read_text(encoding='utf8',errors='replace')[-6500:],flush=True)
    return rc
if __name__=='__main__':raise SystemExit(main())
