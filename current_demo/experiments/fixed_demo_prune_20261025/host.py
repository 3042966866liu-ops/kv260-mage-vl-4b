from demo_common import *
import subprocess,os
def main():
    p=verify();folder=R/(PREFIX+'-host-01');assert not folder.exists();folder.mkdir()
    command=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+rel(H/'entry.py')]
    save(folder/'START.json',dict(command=command+['search'],pid=os.getpid(),protocol_sha256=sha(PREP/'RESULT.json')))
    with (folder/'smoke.stdout').open('xb') as out,(folder/'smoke.stderr').open('xb') as err:smoke=subprocess.run(command+['smoke'],stdout=out,stderr=err,timeout=60)
    assert smoke.returncode==0,'No model load until isolated source smoke passes'
    start=time.monotonic()
    with (folder/'stdout.raw.txt').open('xb') as out,(folder/'stderr.raw.txt').open('xb') as err:run=subprocess.run(command+['search'],stdout=out,stderr=err,timeout=p['budgets']['wall_seconds']+300)
    value=dict(status='COMPLETE_FIXED_DEMO_SEARCH_HOST' if run.returncode==0 else 'FAIL_FIXED_DEMO_SEARCH_HOST',original_host_rc=run.returncode,elapsed_s=time.monotonic()-start,stdout_sha256=sha(folder/'stdout.raw.txt'),stderr_sha256=sha(folder/'stderr.raw.txt'),board_commands=0)
    if (OUT/'RESULT.json').exists():value.update(native_result=rel(OUT/'RESULT.json'),native_sha256=sha(OUT/'RESULT.json'),native_original_rc=read(OUT/'RESULT.json')['original_rc'])
    save(folder/'RESULT.json',value)
    from m455456_workflow02 import synchronized
    h=sha(folder/'RESULT.json');synchronized('latest_m523_fixed_demo_host01',dict(status=value['status'],result=rel(folder/'RESULT.json'),sha256=h,board=False),'## M523固定展示答案剪枝搜索原主机执行\n\nRESULT SHA '+h+'；实际host退出'+str(run.returncode)+'，原stdout/stderr/native退出保全，0新板/heldout/参数训练；不据执行完成称实测提速。')
    print(json.dumps(value,ensure_ascii=False),flush=True);return run.returncode
if __name__=='__main__':raise SystemExit(main())
