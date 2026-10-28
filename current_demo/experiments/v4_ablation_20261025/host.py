"""Bounded explicit WSL stage and original host/native result preservation."""
import subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_ablation import *
def main():
    stage=sys.argv[1];assert stage in ('reuse','evaluate');p=verify()
    out=RUNS/('M537-V4-'+stage+'-host-01');out.mkdir(exist_ok=False)
    script=HERE/('reuse_and_variants.py' if stage=='reuse' else 'evaluate.py')
    cmd=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+rel(script)]
    save(out/'START.json',dict(command=cmd,source_sha256=sha(script),protocol_sha256=sha(PROTO)))
    with (out/'stdout.raw').open('xb') as a,(out/'stderr.raw').open('xb') as b:
        rc=subprocess.run(cmd,stdout=a,stderr=b,timeout=p['budgets'][stage+'_seconds']+120).returncode
    native=(REUSE if stage=='reuse' else OUT)/'RESULT.json'
    v=dict(status=('COMPLETE' if rc==0 else 'FAIL')+'_M537_'+stage.upper()+'_HOST',host_rc=rc,
        native_sha256=sha(native) if native.exists() else None,stdout_sha256=sha(out/'stdout.raw'),stderr_sha256=sha(out/'stderr.raw'),board_commands=0)
    save(out/'RESULT.json',v)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m537_v4_'+stage+'_host01',dict(status=v['status'],result=rel(out/'RESULT.json'),sha256=h,board=False,promoted=False),
        '## M537 V4匹配消融 '+stage+' 原执行\n\nRESULT SHA '+h+'；实际host '+str(rc)+'，完整stdout/stderr/native保存；0新训练/板命令/heldout。不将本级完成当成板端质量或TTFT通过，M536原正式门禁FAIL保持。')
    print(v,flush=True)
    if rc:print((out/'stdout.raw').read_text(encoding='utf8',errors='replace')[-9000:],(out/'stderr.raw').read_text(encoding='utf8',errors='replace')[-3000:],flush=True)
    return rc
if __name__=='__main__':raise SystemExit(main())
