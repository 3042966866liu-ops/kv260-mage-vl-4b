"""Bounded versioned WSL stages and immutable original host exit/logs."""
import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_fix import *
def main():
    stage=sys.argv[1];assert stage in ['frames','fit','reload'];p=verify(FRAMEPROTO if stage=='frames' else PROTO)
    out=RUNS/('M542-demo-counterexample-'+stage+'-host-01');out.mkdir(exist_ok=False)
    cmd=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+rel(HERE/(stage+'.py'))]
    save(out/'START.json',dict(command=cmd,protocol_sha256=sha(FRAMEPROTO if stage=='frames' else PROTO)))
    with (out/'stdout.raw').open('xb') as a,(out/'stderr.raw').open('xb') as b:rc=subprocess.run(cmd,stdout=a,stderr=b,timeout=p['budgets'][stage+'_seconds']+120).returncode
    native={'frames':FRAMES,'fit':FIT,'reload':RELOAD}[stage]/'RESULT.json';v=dict(status=('COMPLETE' if rc==0 else 'FAIL')+'_M542_'+stage.upper()+'_HOST',host_rc=rc,native_sha256=sha(native) if native.exists() else None,
        stdout_sha256=sha(out/'stdout.raw'),stderr_sha256=sha(out/'stderr.raw'),board_commands=0)
    save(out/'RESULT.json',v);sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m542_'+stage+'_host01',dict(status=v['status'],result=rel(out/'RESULT.json'),sha256=h,board=False,promoted=False),
        '## M542展示反例全批次回放 '+stage+'原执行\n\nRESULT SHA '+h+'；host '+str(rc)+'，原日志/native保持。先前M541最终18/21与19/21未通过均保全，不改称成功；本轮新协议、固定400步终点与训练反例，0板/heldout，原失败帧已成为演示训练，不称独立泛化。')
    print(v,flush=True);print((out/'stdout.raw').read_text(encoding='utf8',errors='replace')[-4000:],flush=True)
    if rc:print((out/'stderr.raw').read_text(encoding='utf8',errors='replace')[-2000:],flush=True)
    return rc
if __name__=='__main__':raise SystemExit(main())
