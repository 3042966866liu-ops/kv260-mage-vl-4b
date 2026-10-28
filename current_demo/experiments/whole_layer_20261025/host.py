"""Explicit single offline stage; raw exit/stdout preserved and synchronized."""
from common import *
import os,subprocess
def main():
    stage=sys.argv[1];assert stage in ('search','quality');p=verify()
    folder=R/(PREFIX+'-'+stage+'-host-01');assert not folder.exists();folder.mkdir()
    source=H/(stage+'.py');command=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+rel(source)]
    save(folder/'START.json',dict(command=command,source_sha256=sha(source),protocol_sha256=sha(PREP/'RESULT.json'),pid=os.getpid()))
    t=time.monotonic()
    with (folder/'stdout.raw.txt').open('xb') as out,(folder/'stderr.raw.txt').open('xb') as err:run=subprocess.run(command,stdout=out,stderr=err,timeout=15000 if stage=='search' else 7500)
    native=(SEARCH if stage=='search' else QUALITY)/'RESULT.json'
    v=dict(status='COMPLETE_WHOLE_LAYER_OFFLINE_HOST' if run.returncode==0 else 'FAIL_WHOLE_LAYER_OFFLINE_HOST',original_host_rc=run.returncode,stage=stage,elapsed_s=time.monotonic()-t,stdout_sha256=sha(folder/'stdout.raw.txt'),stderr_sha256=sha(folder/'stderr.raw.txt'),board_commands=0)
    if native.exists():v.update(native_result=rel(native),native_sha256=sha(native),native_original_rc=read(native)['original_rc'])
    save(folder/'RESULT.json',v)
    from m455456_workflow02 import synchronized
    h=sha(folder/'RESULT.json');synchronized('latest_m523_whole_layer_'+stage+'01',dict(status=v['status'],result=rel(folder/'RESULT.json'),sha256=h,board=False),'## M523联合整层删除离线'+stage+'原执行\n\nRESULT SHA '+h+'；原host退出'+str(run.returncode)+'，原stdout/stderr及native退出保全；0板/heldout/参数训练，不据执行完成称质量或30秒通过。')
    print(json.dumps(v,ensure_ascii=False),flush=True);return run.returncode
if __name__=='__main__':raise SystemExit(main())
