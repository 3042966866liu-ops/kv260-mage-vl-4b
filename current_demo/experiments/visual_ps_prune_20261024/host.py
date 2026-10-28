"""One explicit offline WSL stage, raw stdout and original exit preserved."""
import os,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def main():
    assert len(sys.argv)==2 and sys.argv[1] in ('fit','features','quality')
    stage=sys.argv[1];p=verify();folder=R/(PREFIX+'-'+stage+'-host-01');assert not folder.exists();folder.mkdir()
    target=H/(stage+'.py');native='/mnt/c/'+relative(target)
    # relative(ROOT) deliberately not used: drive-root path is explicit.
    native='/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+relative(target)
    cmd=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B',native]
    save(folder/'START.json',dict(command=cmd,pid=os.getpid(),source_sha256=sha(target),protocol_sha256=sha(PREP/'RESULT.json')))
    start=time.monotonic()
    with (folder/'stdout.raw.txt').open('xb') as stdout,(folder/'stderr.raw.txt').open('xb') as stderr:
        run=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=p['budgets'][{'fit':'fit_seconds','features':'feature_seconds','quality':'quality_seconds'}[stage]]+300)
    value=dict(status='COMPLETE_OFFLINE_HOST_STAGE' if run.returncode==0 else 'FAIL_OFFLINE_HOST_STAGE',original_host_rc=run.returncode,
        stage=stage,elapsed_s=time.monotonic()-start,stdout_sha256=sha(folder/'stdout.raw.txt'),stderr_sha256=sha(folder/'stderr.raw.txt'),board_commands=0)
    result={'fit':FIT,'features':FEATURES,'quality':QUALITY}[stage]/'RESULT.json'
    if result.exists():value.update(native_result=relative(result),native_result_sha256=sha(result),native_original_rc=read(result)['original_rc'])
    save(folder/'RESULT.json',value)
    from m455456_workflow02 import synchronized
    h=sha(folder/'RESULT.json');synchronized('latest_m523_PS_V236_3072_'+stage+'_host01',dict(status=value['status'],result=relative(folder/'RESULT.json'),sha256=h,board=False),
        '## M523视觉PS V2/V3/V6 3072 '+stage+'原执行\n\nRESULT SHA '+h+'；原host退出'+str(run.returncode)+'，原stdout/stderr及native结果按SHA保全。仅离线PS剪枝研究，0板命令/信号/heldout，不据本级执行完成称整机质量或提速。')
    print(json.dumps(value,ensure_ascii=False),flush=True)
    return run.returncode
if __name__=='__main__':raise SystemExit(main())
