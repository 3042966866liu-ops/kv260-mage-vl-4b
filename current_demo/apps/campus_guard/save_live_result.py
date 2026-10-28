"""Save one exact UART result and synchronize before exposing it to the UI."""
import argparse,base64,hashlib,json,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'))
from common_joint import read,sha,save,relative,RUNS,OPT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('line_file');args=ap.parse_args()
    line=Path(args.line_file).read_text(encoding='utf-8-sig').strip();marker,h,encoded=line.split(' ',2);assert marker=='M529_RESULT'
    raw=zlib.decompress(base64.b64decode(encoded,validate=True));assert len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==h
    v=json.loads(raw);assert v['primary_rc']==0 and v['completed_request'] and v['argmax_verified'] and v['actual_full_vocab']==151936 and v['physical_calls']>=324
    assert v['owner_released'] is False and v['stable_restored'] is False
    p=read(RUNS/'M529-campus-persistent-worker-protocol-01/RESULT.json');assert v['software_delta_manifest_sha256']==p['manifest_sha256'] and v['package_manifest_sha256']==p['model_manifest_sha256']
    case=next(r for r in read(ROOT/p['package']/'DEMO_BOARD_PLAN.json')['demo_requests'] if r['id']==v['case_id']);assert case['frame_sha256']==v['frame_sha256']
    assert len(v['ui_job_id'])==32 and all(c in '0123456789abcdef' for c in v['ui_job_id'])
    out=RUNS/'M529-campus-persistent-worker-live-01'/v['ui_job_id'];out.mkdir(parents=True)
    result=out/'RESULT.json';result.open('xb').write(raw);assert sha(result)==h
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    synchronized('latest_m529_live_completed_request01',dict(status=v['status'],result=relative(result),sha256=h,board=True,hardware=True,owner_still_live=True,production_promoted=False),'## M529网页固定窗口真实请求完成（原持久owner仍在）\n\nRESULT SHA '+h+'；任务'+v['ui_job_id']+'，窗口'+v['case_id']+'，实际首词'+v['decision']+'，TTFT '+str(v['TTFT_s'])+'秒；原全151936 logits argmax/物理调用/帧SHA/nonce绑定。仅本请求完成，七owner有意保留供下一有界任务，不称stable恢复或整体服务退出；本条先同步后才交网页。')
    print(json.dumps(dict(id=v['ui_job_id'],evidence_file=relative(result),evidence_sha256=h)),flush=True)
if __name__=='__main__':main()
