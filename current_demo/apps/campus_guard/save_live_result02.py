"""Save exact M544 UART proof and synchronize before letting the web display it."""
import base64,hashlib,json,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/optimization'))
from m455456_workflow02 import synchronized
def main():
    packet=Path(sys.argv[1]);marker,h,encoded=packet.read_text(encoding='utf-8-sig').strip().split(' ',2);assert marker=='M544_RESULT'
    d=zlib.decompressobj();raw=d.decompress(base64.b64decode(encoded,validate=True),32769);assert d.eof and not d.unused_data and not d.unconsumed_tail and len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==h
    v=json.loads(raw);binding=json.loads((ROOT/'apps/campus_guard/LIVE_BINDING.json').read_bytes())
    assert v['primary_rc']==0 and v['completed_request'] and v['argmax_verified'] and v['actual_full_vocab']==151936 and v['physical_calls']>=324
    assert v['owner_released'] is False and v['stable_restored'] is False and v['package_manifest_sha256']==binding['package_manifest_sha256'] and v['base_model_manifest_sha256']==binding['model_reference_manifest_sha256']
    assert v['decision'] in ['Yes','No'] and len(v['ui_job_id'])==32 and all(c in '0123456789abcdef' for c in v['ui_job_id']) and v['full_logits_sha256']==v['logits_sha256']
    out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-live-board-results'/v['session']/v['ui_job_id'];out.mkdir(parents=True,exist_ok=False);result=out/'RESULT.json';result.open('xb').write(raw)
    rel=result.relative_to(ROOT).as_posix()
    synchronized('latest_m544_live_completed_request',dict(status=v['status'],result=rel,sha256=h,board=True,hardware=True,owner_still_live=True,promoted=False),'## M544网页本次真实板端请求完成（七owner仍在）\n\nRESULT SHA '+h+'；任务'+v['ui_job_id']+'，输入SHA '+v['frame_sha256']+'，实际首词'+v['decision']+'，首判断'+str(v['TTFT_s'])+'秒。完整151936词表argmax/物理调用/新会话与任务/帧SHA绑定；只称本请求完成，原七owner有意供后续有界任务，未声称stable恢复或进程退出。先保存/三同步再交网页，不按文件名/标签/定时器产生报警。')
    print(json.dumps(dict(id=v['ui_job_id'],evidence_file=rel,evidence_sha256=h)),flush=True)
if __name__=='__main__':main()
