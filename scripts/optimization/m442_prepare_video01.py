"""Same-M441 one-request fixed159 gate with explicit M442 parser."""
import ast
import json
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m442_component_workflow01 import manifest
from m442_prepare_text01 import once

def main():
    prior=BASE/'runs/M442-live-parser-text-board-01/BOARD_RESULT.json'
    r=json.loads(prior.read_bytes());digest=sha(prior)
    assert r['status']=='PASS_M442T_FIXED_TEXT_DIAGNOSTIC' and r['numerical_pass'] and r['safe_buffers_released'] and not r['unsafe_buffers_retained']
    assert all(digest in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    old=BASE/'candidates/M441-fixed-video-09';pkg=BASE/'candidates/M442-live-parser-video-01';boot=BASE/'candidates/M442-live-parser-video-transfer-01'
    assert not pkg.exists() and not boot.exists()
    remote='/home/ubuntu/m442_live_parser_video_01';evidence='/home/ubuntu/m442_live_parser_video_evidence_01'
    pkg.mkdir(parents=True);spec=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes());old_digest=sha(old/'STAGE_PREREQUISITE.json')
    for row in spec['files']:
        src=old/row['path'];assert sha(src)==row['sha256']
        if row['path'] in ('SHA256SUMS','m441_video_assemble.py'):continue
        data=src.read_bytes()
        if row['path']=='STAGE_PREREQUISITE.json':data=prior.read_bytes()
        elif row['path']=='m441_video_gate.py':
            text=data.decode('utf-8').replace('/home/ubuntu/m441_fixed_video_evidence_09',evidence).replace('M441V','M442V').replace(old_digest,digest).replace('PASS_M441T_FIXED_TEXT_DIAGNOSTIC','PASS_M442T_FIXED_TEXT_DIAGNOSTIC')
            text=once(text,'        board_cls = m243_video_server.M238PrefillRuntime',"        from m442_runtime_adapter02 import make_candidate_runtime_class\n        board_cls = make_candidate_runtime_class(m243_video_server.M238PrefillRuntime)\n        result['parser_candidate_sha256']=sha256(HERE/'m442_output_parser06.py')\n        result['parser_component_sha256']=sha256(HERE/'PARSER_COMPONENT.json')\n        result['parser_workers']=1\n        result['kernel_changed']=False\n        if result['parser_component_sha256']!='"+r['parser_component_sha256']+"':raise RuntimeError('Actual A53 parser component differs before Overlay')")
            data=text.encode('utf-8')
        elif row['path'] in ('m441_video_export.py','run_m441_video.sh','m441_video_entry.py','m432_trials.py','m432_request_visual.py'):
            data=data.replace(b'/home/ubuntu/m441_fixed_video_evidence_09',evidence.encode()).replace(b'M441V',b'M442V')
        if row['path'].endswith('.py'):ast.parse(data,feature_version=(3,10))
        atomic(pkg/row['path'],data,immutable=True)
    for name in ('m442_runtime_adapter02.py','m442_output_parser06.py','PARSER_COMPONENT.json'):atomic(pkg/name,(BASE/'candidates/M442-live-parser-layer-01'/name).read_bytes(),immutable=True)
    spec=manifest(pkg,'m442-live-parser-fixed159-same-M441-v1');boot.mkdir(parents=True)
    transfer=(HERE/'m441_transfer.py').read_text(encoding='utf-8')
    transfer=once(transfer,"DESTINATION=Path('/home/ubuntu/m441_candidate_01')","DESTINATION=Path('"+remote+"')")
    transfer=once(transfer,"EVIDENCE=Path('/home/ubuntu/m441_transfer_evidence_01')","EVIDENCE=Path('/home/ubuntu/m442_live_parser_video_transfer_evidence_01')")
    atomic(boot/'m442_transfer01.py',transfer.encode(),immutable=True)
    rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(pkg/'PACKAGE_MANIFEST.json').stat().st_size,sha256=sha(pkg/'PACKAGE_MANIFEST.json'))]+spec['files']
    atomic(boot/'TRANSPORT_MANIFEST.json',encoded(dict(schema='m441-specific-peer-transfer-v1',package_manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))),immutable=True)
    atomic(boot/'run_m442_transfer.sh',(BASE/'candidates/M442-live-parser-transfer-01/run_m442_transfer.sh').read_bytes(),immutable=True)
    manifest(boot,'m442-live-parser-fixed159-specific-peer-bootstrap')
    decoder=(HERE/'m441_video_collect09.py').read_text(encoding='utf-8')
    decoder=decoder[:decoder.index('\ndef collect(path):')].replace('M441-fixed-video-09','M442-live-parser-video-01').replace('M441-fixed-video-board-09','M442-live-parser-video-board-01').replace('M441V','M442V').replace(old_digest,digest)
    anchor="    if r['status']=='PASS_M442V_INTEGRATED_VIDEO_NUMERICAL':"
    extra="\n        if r.get('parser_candidate_sha256')!=sha(PKG/'m442_output_parser06.py') or r.get('parser_component_sha256')!=sha(PKG/'PARSER_COMPONENT.json') or r.get('parser_workers')!=1 or r.get('kernel_changed') is not False:raise ValueError('New parser/worker/kernel identity differs')"
    decoder=once(decoder,anchor,anchor+extra)
    atomic(HERE/'m442_video_decoder01.py',decoder.encode(),immutable=True)
    workflow=(HERE/'m442_text_workflow01.py').read_text(encoding='utf-8')
    prefix=workflow[:workflow.index('\n_namespace_text=')]
    for a,b in [('M442-live-parser-text-preparation-01','M442-live-parser-video-preparation-01'),('M442-live-parser-text-artifact-transfer-01','M442-live-parser-video-artifact-transfer-01'),('M442-live-parser-text-transfer-01','M442-live-parser-video-transfer-01'),('M442-live-parser-text-01','M442-live-parser-video-01'),('latest_m442_live_parser_text_transfer','latest_m442_live_parser_video_transfer')]:prefix=prefix.replace(a,b)
    body='''
from m442_video_decoder01 import decode
def collect(log):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'))
    out=BASE/'runs/M442-live-parser-video-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    atomic(out.with_name('COLLECTION.json'),encoded(dict(raw_sha256=digest,log_sha256=sha(Path(log)),hardware_rerun=False,chunks=count)),immutable=True)
    sync('latest_m442_live_parser_video_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],performance_pass=False),f'## M442新解析固定159视频裁决（2026-10-10）\\n\\nSHA {digest}；{r["status"]}，原rc{r["gate_return_code"]}。同M441硬件及M437后11层视觉，单parser/七DMA驻留/159提示/原末帧两视图；完整视觉边界/语言/KV/logits/重试原参考及安全释放/回滚独立核对。非完整请求收益，失败只本级。')
    print(r['status'],digest,r['errors'],flush=True)
    return r['gate_return_code']
if __name__=='__main__':
    if sys.argv[1:]==['send']:raise SystemExit(send())
    if len(sys.argv)==3 and sys.argv[1]=='collect':raise SystemExit(collect(sys.argv[2]))
    if len(sys.argv)==3 and sys.argv[1]=='transfer-collect':raise SystemExit(transfer_collect(sys.argv[2]))
    raise RuntimeError('Saved collection or explicit send only')
'''
    atomic(HERE/'m442_video_workflow01.py',(prefix+body).encode(),immutable=True)
    control=(HERE/'m442_text_control01.ps1').read_text(encoding='utf-8')
    for a,b in [('M442-live-parser-text-preparation-01','M442-live-parser-video-preparation-01'),('M442-live-parser-text-board-01','M442-live-parser-video-board-01'),('M442-live-parser-text-artifact-transfer-01','M442-live-parser-video-artifact-transfer-01'),('M442-live-parser-text-transfer-01','M442-live-parser-video-transfer-01'),('M442-live-parser-text-01','M442-live-parser-video-01'),('m442_text_workflow01','m442_video_workflow01'),('/home/ubuntu/m442_live_parser_text_01',remote),('/home/ubuntu/m442_live_parser_text_transfer_bootstrap_01','/home/ubuntu/m442_live_parser_video_transfer_bootstrap_01'),('tmp/m442_text01','tmp/m442_video01'),('run_m441_text.sh','run_m441_video.sh'),('M442T_ENABLE_STAGED_LAYER','M442V_ENABLE_INTEGRATED_VIDEO'),('$taskSHA $taskAction B1','$taskSHA $taskAction'),('-TimeoutSeconds 900','-TimeoutSeconds 1500')]:control=control.replace(a,b)
    atomic(HERE/'m442_video_control01.ps1',control.encode(),immutable=True)
    for name in ('m442_video_decoder01.py','m442_video_workflow01.py'):ast.parse((HERE/name).read_bytes(),feature_version=(3,10))
    result=dict(status='PREPARED_M442_LIVE_PARSER_FIXED159_VIDEO01',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),bootstrap_manifest_sha256=sha(boot/'PACKAGE_MANIFEST.json'),prior_text_raw_sha256=digest,kernel_build='0x4D343431',hardware_unchanged=True,original_visual_policy_and_math=True,parser_workers=1,seven_DMA_resident=True,expected_language_physical=781,expected_visual_physical=286,total_with_minimal=1068,board=False,performance=False,files=[evidence(HERE/name) for name in ('m442_video_decoder01.py','m442_video_workflow01.py','m442_video_control01.ps1')])
    dest=BASE/'runs/M442-live-parser-video-preparation-01/RESULT.json';atomic(dest,encoded(result),immutable=True)
    sync('latest_m442_live_parser_video_preparation',dict(status=result['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),f'## M442新解析固定视频准备01（2026-10-10）\n\nSHA {sha(dest)}；新实际文本raw {digest} 后，原159token/后11层13..23视觉/末帧两视图/完整视觉语言KVlogits参考。显式新解析与同M441硬件，不新增bank/slot/预读/worker。下一步实际支持/传输/一次Run，非请求提速或晋级。')
    print(result['status'],sha(dest))

def evidence(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))
if __name__=='__main__':main()
