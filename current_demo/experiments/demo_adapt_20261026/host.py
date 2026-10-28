"""Explicit bounded WSL stages, original rc/log preservation and Windows sync."""
import subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_adapt import *
def main():
    stage=sys.argv[1];assert stage in ['frames','capture','fit','reload']
    p=verify(SOURCE if stage=='frames' else PROTO);out=RUNS/('M541-demo-adaptation-'+stage+'-host-01');out.mkdir(exist_ok=False)
    script=HERE/('make_frames.py' if stage=='frames' else stage+'.py')
    cmd=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+rel(script)]
    save(out/'START.json',dict(command=cmd,source_sha256=sha(script),protocol_sha256=sha(SOURCE if stage=='frames' else PROTO)))
    with (out/'stdout.raw').open('xb') as a,(out/'stderr.raw').open('xb') as b:rc=subprocess.run(cmd,stdout=a,stderr=b,timeout=p['budgets'][stage+'_seconds']+120).returncode
    native={'frames':FRAMES,'capture':CAP,'fit':FIT,'reload':RELOAD}[stage]/'RESULT.json'
    v=dict(status=('COMPLETE' if rc==0 else 'FAIL')+'_M541_'+stage.upper()+'_HOST',host_rc=rc,native_sha256=sha(native) if native.exists() else None,
        stdout_sha256=sha(out/'stdout.raw'),stderr_sha256=sha(out/'stderr.raw'),board_commands=0)
    save(out/'RESULT.json',v)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m541_'+stage+'_host01',dict(status=v['status'],result=rel(out/'RESULT.json'),sha256=h,board=False,promoted=False),
        '## M541展示域恢复 '+stage+' 原执行\n\nRESULT SHA '+h+'；实际host '+str(rc)+'，native/stdout/stderr保全。仅注册展示域训练与开发，不冒充独立泛化/板端通过；M540漏判与M536正式FAIL保持，0板命令/heldout。')
    print(v,flush=True);print((out/'stdout.raw').read_text(encoding='utf8',errors='replace')[-4500:],flush=True)
    if rc:print((out/'stderr.raw').read_text(encoding='utf8',errors='replace')[-2000:],flush=True)
    return rc
if __name__=='__main__':raise SystemExit(main())
