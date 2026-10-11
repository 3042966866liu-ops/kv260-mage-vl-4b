"""Prepare independent M442 text gate after actual live parser layer PASS."""
import ast
import json
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m442_component_workflow01 import manifest

def once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)

def main():
    layer=BASE/'runs/M442-live-parser-layer-board-01/BOARD_RESULT.json'
    r=json.loads(layer.read_bytes());digest=sha(layer)
    assert r['status']=='PASS_M442L_SINGLE_LAYER_DIAGNOSTIC' and r['numerical_pass'] and r['safe_buffers_released'] and not r['unsafe_buffers_retained']
    assert all(digest in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    old=BASE/'candidates/M441-fixed-text-09'
    pkg=BASE/'candidates/M442-live-parser-text-01'
    boot=BASE/'candidates/M442-live-parser-text-transfer-01'
    assert not pkg.exists() and not boot.exists()
    remote='/home/ubuntu/m442_live_parser_text_01'
    evidence='/home/ubuntu/m442_live_parser_text_evidence_01'
    pkg.mkdir(parents=True)
    spec=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    old_layer=json.loads((old/'STAGE_PREREQUISITE.json').read_bytes())
    old_digest=sha(old/'STAGE_PREREQUISITE.json')
    assert old_layer['status']=='PASS_M441L_SINGLE_LAYER_DIAGNOSTIC'
    for row in spec['files']:
        p=old/row['path'];assert sha(p)==row['sha256']
        if row['path'] in ('SHA256SUMS','m441_text_assemble.py'):continue
        raw=p.read_bytes()
        if row['path']=='STAGE_PREREQUISITE.json':raw=layer.read_bytes()
        elif row['path']=='m441_text_gate.py':
            text=raw.decode('utf-8').replace('/home/ubuntu/m441_fixed_text_evidence_09',evidence).replace('M441T','M442T')
            text=text.replace(old_digest,digest).replace('PASS_M441L_SINGLE_LAYER_DIAGNOSTIC','PASS_M442L_SINGLE_LAYER_DIAGNOSTIC')
            text=once(text,'        board_cls = m243_video_server.M238PrefillRuntime',"        from m442_runtime_adapter02 import make_candidate_runtime_class\n        board_cls = make_candidate_runtime_class(m243_video_server.M238PrefillRuntime)\n        result['parser_candidate_sha256']=sha256(HERE/'m442_output_parser06.py')\n        result['parser_component_sha256']=sha256(HERE/'PARSER_COMPONENT.json')\n        result['parser_workers']=1\n        result['kernel_changed']=False\n        if result['parser_component_sha256']!='"+r['parser_component_sha256']+"':raise RuntimeError('Actual parser component differs before Overlay')")
            raw=text.encode('utf-8')
        elif row['path'] in ('m441_text_export.py','run_m441_text.sh'):
            raw=raw.replace(b'/home/ubuntu/m441_fixed_text_evidence_09',evidence.encode()).replace(b'M441T',b'M442T')
        if row['path'].endswith('.py'):ast.parse(raw,feature_version=(3,10))
        atomic(pkg/row['path'],raw,immutable=True)
    for name in ('m442_runtime_adapter02.py','m442_output_parser06.py','PARSER_COMPONENT.json'):
        src=BASE/'candidates/M442-live-parser-layer-01'/name
        atomic(pkg/name,src.read_bytes(),immutable=True)
    spec=manifest(pkg,'m442-live-parser-same-M441-fixed-text-v1')
    boot.mkdir(parents=True)
    transfer=(HERE/'m441_transfer.py').read_text(encoding='utf-8')
    transfer=once(transfer,"DESTINATION=Path('/home/ubuntu/m441_candidate_01')","DESTINATION=Path('"+remote+"')")
    transfer=once(transfer,"EVIDENCE=Path('/home/ubuntu/m441_transfer_evidence_01')","EVIDENCE=Path('/home/ubuntu/m442_live_parser_text_transfer_evidence_01')")
    atomic(boot/'m442_transfer01.py',transfer.encode(),immutable=True)
    rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(pkg/'PACKAGE_MANIFEST.json').stat().st_size,sha256=sha(pkg/'PACKAGE_MANIFEST.json'))]+spec['files']
    atomic(boot/'TRANSPORT_MANIFEST.json',encoded(dict(schema='m441-specific-peer-transfer-v1',package_manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))),immutable=True)
    atomic(boot/'run_m442_transfer.sh',(BASE/'candidates/M442-live-parser-transfer-01/run_m442_transfer.sh').read_bytes(),immutable=True)
    manifest(boot,'m442-live-parser-fixed-text-specific-peer-bootstrap')
    workflow=(HERE/'m442_layer_workflow01.py').read_text(encoding='utf-8')
    prefix=workflow[:workflow.index("\n_source=(HERE/'m365_collect.py')")]
    prefix=prefix.replace('M442-live-parser-layer-01','M442-live-parser-text-01').replace('M442-live-parser-transfer-01','M442-live-parser-text-transfer-01').replace('M442-live-parser-layer-preparation-01','M442-live-parser-text-preparation-01').replace('M442-live-parser-artifact-transfer-01','M442-live-parser-text-artifact-transfer-01').replace('latest_m442_live_parser_transfer','latest_m442_live_parser_text_transfer')
    decoder=(HERE/'m441_text_collect09.py').read_text(encoding='utf-8')
    decoder=decoder[:decoder.index('\ndef collect(logpath):')]
    decoder=decoder.replace('M441-fixed-text-09','M442-live-parser-text-01').replace('M441T','M442T').replace(old_digest,digest)
    # The strict original text decoder, including prior-layer/head admission,
    # is composed before the new candidate-specific checks.
    prefix+='\n_namespace_text={"__name__":"_m442_text_original_decoder"}\nexec(compile('+repr(decoder)+',"<strict original text decoder>","exec"),_namespace_text)\n'
    body=workflow[workflow.index('\ndef collect(log):'):]
    body=body.replace("_namespace['decode']","_namespace_text['decode']").replace('PASS_M442L_SINGLE_LAYER_DIAGNOSTIC','PASS_M442T_FIXED_TEXT_DIAGNOSTIC').replace('M442-live-parser-layer-board-01','M442-live-parser-text-board-01').replace('latest_m442_live_parser_layer_board','latest_m442_live_parser_text_board').replace('M442真实解析路径单层裁决','M442真实解析路径固定文本裁决').replace('原五family/159token/原完整参考','原30token/36层/154family/151936logits/72KV完整参考')
    atomic(HERE/'m442_text_workflow01.py',(prefix+body).encode(),immutable=True)
    control=(HERE/'m442_layer_control01.ps1').read_text(encoding='utf-8')
    for a,b in [('M442-live-parser-layer-preparation-01','M442-live-parser-text-preparation-01'),('M442-live-parser-layer-board-01','M442-live-parser-text-board-01'),('M442-live-parser-layer-01','M442-live-parser-text-01'),('M442-live-parser-transfer-01','M442-live-parser-text-transfer-01'),('M442-live-parser-artifact-transfer-01','M442-live-parser-text-artifact-transfer-01'),('m442_layer_workflow01','m442_text_workflow01'),('/home/ubuntu/m442_live_parser_layer_01',remote),('/home/ubuntu/m442_live_parser_transfer_bootstrap_01','/home/ubuntu/m442_live_parser_text_transfer_bootstrap_01'),('tmp/m442_layer01','tmp/m442_text01'),('run_m441_layer.sh','run_m441_text.sh'),('M442L_ENABLE_STAGED_LAYER','M442T_ENABLE_STAGED_LAYER')]:control=control.replace(a,b)
    atomic(HERE/'m442_text_control01.ps1',control.encode(),immutable=True)
    support=(HERE/'m442_layer_support01.py').read_text(encoding='utf-8')
    for a,b in [('m442_layer_workflow01','m442_text_workflow01'),('m442_layer_control01','m442_text_control01'),('M441-single-layer-board-09','M441-fixed-text-board-09'),('PASS_M442L_SINGLE_LAYER_DIAGNOSTIC','PASS_M442T_FIXED_TEXT_DIAGNOSTIC'),('M442L','M442T'),("w._namespace['decode']","w._namespace_text['decode']"),('PASS_M442_LIVE_LAYER_SUPPORT01','PASS_M442_LIVE_TEXT_SUPPORT01'),('M442-live-parser-layer-support-01','M442-live-parser-text-support-01'),('latest_m442_live_parser_layer_support','latest_m442_live_parser_text_support'),('m442_layer_workflow01.py','m442_text_workflow01.py'),('M442单层支持实际检查','M442固定文本支持实际检查')]:support=support.replace(a,b)
    anchor="r.update(status='PASS_M442T_FIXED_TEXT_DIAGNOSTIC'"
    assert support.count(anchor)==1
    support=support.replace(anchor,"r['prior_single_layer_raw_sha256']='"+digest+"'\n"+anchor)
    support=support.replace("('numerical_pass',False)","('prior_single_layer_raw_sha256','0'*64),('head_AST_checked_before_overlay',False),('numerical_pass',False)")
    atomic(HERE/'m442_text_support01.py',support.encode(),immutable=True)
    for name in ('m442_text_workflow01.py','m442_text_support01.py'):ast.parse((HERE/name).read_bytes(),feature_version=(3,10))
    record=dict(status='PREPARED_M442_LIVE_PARSER_FIXED_TEXT01',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),bootstrap_manifest_sha256=sha(boot/'PACKAGE_MANIFEST.json'),prior_layer_raw_sha256=digest,parser_component_sha256=r['parser_component_sha256'],kernel_build='0x4D343431',hardware_unchanged=True,seven_DMA_resident=True,parser_workers=1,board=False,performance=False,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (HERE/'m442_text_workflow01.py',HERE/'m442_text_control01.ps1',HERE/'m442_text_support01.py')])
    dest=BASE/'runs/M442-live-parser-text-preparation-01/RESULT.json'
    atomic(dest,encoded(record),immutable=True)
    sync('latest_m442_live_parser_text_preparation',dict(status=record['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),f'## M442新解析固定文本准备01（2026-10-10）\n\nSHA {sha(dest)}；新实际单层raw {digest} 后，原30token/36层/完整head/154family/151936logits/72KV参考，显式候选解析器和同M441硬件。独立原字节/安全/来源/PS预算判据，不扩大slot/bank。下一步实际支持检查后传输并一次Run；尚非文本数值或完整请求收益。')
    print(record['status'],sha(dest))

if __name__=='__main__':main()
