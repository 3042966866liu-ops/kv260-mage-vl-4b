"""Bind the UI to the actual four-window board evidence. No inference."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OPT=ROOT/'deployment/mage_vl4b/optimization_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    pkg=OPT/'candidates/M523-fixed-demo-subset-board-07'
    plan=json.loads((pkg/'DEMO_BOARD_PLAN.json').read_bytes())
    source=OPT/'runs/M523-fixed-demo-pruning-128-board-07/Run/BOARD_RESULT.json'
    assert sha(source)=='b08c66fb4c1fca8cfab9eb6cac1e7ec40ee74b4bc2e2b94ac8455528ef43c499'
    result=json.loads(source.read_bytes());assert result['primary_rc']==0 and result['safe_cleanup_complete']
    frames=HERE/'static/frames';frames.mkdir(parents=True,exist_ok=True)
    rows=[]
    for r in plan['demo_requests']:
        f=pkg/r['frame_path'];assert sha(f)==r['frame_sha256']
        video=ROOT/r['video'];assert sha(video)==r['video_sha256']
        a=np.load(f,allow_pickle=False);assert a.dtype==np.uint8 and a.shape==(448,448,3)
        image=frames/(r['id']+'.png');Image.fromarray(a).save(image)
        s=next(s for s in result['sample_summaries'] if s['validation'] and s['request_id']==r['id'])
        rows.append(dict(id=r['id'],camera_id='kitchen' if '04' in r['id'] else 'workshop',video=r['video'],video_sha256=r['video_sha256'],timestamp_ms=r['timestamp_ms'],frame_path='/static/frames/'+image.name,frame_sha256=r['frame_sha256'],image_sha256=sha(image),actual_decision=s['display_decision'],token=s['raw_first_token'],TTFT_s=s['first_token_wall_s'],prepare_s=s['prepare_s'],prefill_s=s['prefill_s'],sample_sha256=s['sample_sha256'],logits_sha256=s['first_logits_sha256'],label=s['label']))
    value=dict(evidence_file=source.relative_to(ROOT).as_posix(),evidence_sha256=sha(source),model_package=pkg.relative_to(ROOT).as_posix(),package_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),model_build='M455 / M525 · 10V18L',rows=rows,hot_TTFT_s=[s['first_token_wall_s'] for s in result['sample_summaries'] if not s['validation']],first_request_TTFT_s=rows[0]['TTFT_s'],scope='AI-generated simulation material; four frozen windows only. First-token decisions. Historical hardware evidence, not live campus footage.')
    (HERE/'catalog.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(windows=len(rows),historical_board_sha256=sha(source),board_commands=0),ensure_ascii=False))
if __name__=='__main__':main()
