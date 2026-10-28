"""Synchronize the real current-boot fixed warmup gate before Web worker readiness."""
import base64,hashlib,json,re,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate(v,binding,plan):
    assert re.fullmatch('[0-9a-f]{32}',v['session']) and v['package_manifest_sha256']==binding['package_manifest_sha256']
    p=v['fixed_gate_proof'];assert isinstance(p,dict) and p['status']=='PASS_M544_CURRENT_BOOT_FIXED_WARMUP_BEFORE_WEB' and p['primary_rc']==0
    assert p['session']==v['session'] and p['package_manifest_sha256']==v['package_manifest_sha256'] and p['boot_id']==plan['expected_boot']==binding['worker_expected_boot']
    assert p['completed_request'] is True and p['answer_correct'] is True and p['decision']==p['expected_decision']==plan['demo_requests'][0]['expected_decision']
    assert p['frame_sha256']==plan['demo_requests'][0]['frame_sha256'] and p['actual_full_vocab']==151936 and p['argmax_verified'] is True
    assert p['physical_calls']>=324 and p['visual_physical_calls']>=104 and p['input_tokens']==128 and p['T32_blocks']==4 and p['decode_calls']==0 and p['owners_still_live'] is True
    for k in ['logits_sha256','source_sample_sha256']:assert re.fullmatch('[0-9a-f]{64}',p[k])
    return p
def main():
    packet=Path(sys.argv[1]);marker,h,encoded=packet.read_text(encoding='utf-8-sig').strip().split(' ',2);assert marker=='M544_READY'
    d=zlib.decompressobj();raw=d.decompress(base64.b64decode(encoded,validate=True),32769);assert d.eof and not d.unused_data and not d.unconsumed_tail and len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==h
    v=json.loads(raw);binding=json.loads((HERE/'LIVE_BINDING.json').read_bytes());prep=json.loads((ROOT/binding['worker_preparation']).read_bytes());pkg=ROOT/prep['package'];assert sha(pkg/'PACKAGE_MANIFEST.json')==binding['package_manifest_sha256']==prep['manifest_sha256'];plan=json.loads((pkg/'DEMO_BOARD_PLAN.json').read_bytes());p=validate(v,binding,plan)
    out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-live-fixed-gates'/v['session'];out.mkdir(parents=True,exist_ok=False);result=out/'RESULT.json';result.open('x',encoding='utf-8').write(json.dumps(p,sort_keys=True,indent=2)+'\n');(out/'ORIGINAL_READY.packet').open('xb').write(packet.read_bytes());digest=sha(result)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    synchronized('latest_m544_live_current_fixed_gate',dict(status=p['status'],result=result.relative_to(ROOT).as_posix(),sha256=digest,board=True,hardware=True,owner_still_live=True,promoted=False),'## M544本次启动网页前固定预热实际门已返回\n\nRESULT SHA '+digest+'；本boot '+p['boot_id']+'，完整151936词表/原画面/128四块/物理调用与正确Yes已核；七owner仍为有界网页会话持有，不称已释放/稳定恢复。先原字节保存和三同步，再允许READY及网页任务；预热答案不显示网页。仅固定样例，不当新视频泛化。')
    print('SYNCHRONIZED_ACTUAL_CURRENT_BOOT_FIXED_WARMUP',digest)
if __name__=='__main__':main()
