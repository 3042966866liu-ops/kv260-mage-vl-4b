"""Freeze the explicitly selected old campus03 + new campus12 demonstration pair."""
import sys,json,hashlib,ast,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs'
OUT=RUNS/'M540-campus03-demo-media-selection-01'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.open('x',encoding='utf8').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def derive(name):
    prior=ROOT/'experiments/campus_demo_media_20261026'/name
    tree=ast.parse(prior.read_text(encoding='utf8'));changes=[];fields=[]
    class Bind(ast.NodeTransformer):
        def visit_Constant(self,node):
            if isinstance(node.value,str):
                before=node.value;after=before.replace('M539','M540').replace('campus12','campus03').replace('CAMPUS12','CAMPUS03').replace('四帧','五帧')
                if after!=before:changes.append(dict(before=before,after=after));node.value=after
            return node
        def visit_keyword(self,node):
            self.generic_visit(node)
            if node.arg in ['false_yes','all_selected_frames_No']:
                previous=node.arg;node.arg={'false_yes':'yes_count','all_selected_frames_No':'all_actual_No'}[node.arg]
                fields.append(dict(before=previous,after=node.arg))
            return node
    edited=Bind().visit(copy.deepcopy(tree));ast.fix_missing_locations(edited)
    # Only path/log labels and two negative-only summary field names change.
    restored=copy.deepcopy(edited)
    class Unbind(ast.NodeTransformer):
        def visit_Constant(self,node):
            for r in changes:
                if isinstance(node.value,str) and node.value==r['after']:node.value=r['before'];break
            return node
        def visit_keyword(self,node):
            self.generic_visit(node)
            for r in fields:
                if node.arg==r['after']:node.arg=r['before'];break
            return node
    restored=Unbind().visit(restored)
    assert ast.dump(restored,include_attributes=False)==ast.dump(tree,include_attributes=False)
    source=ast.unparse(edited)+'\n';compile(source,str(HERE/name),'exec')
    (HERE/name).open('x',encoding='utf8').write(source)
    return dict(source=rel(prior),source_sha256=sha(prior),derived=rel(HERE/name),derived_sha256=sha(HERE/name),
        literal_changes=changes,summary_field_renames=fields,numerical_AST_unchanged=True)
def main():
    assert not OUT.exists();OUT.mkdir(parents=True)
    sources=[derive(n) for n in ['quality.py','quality_host.py']]
    old=RUNS/'M530-campus-demo-media-review-01/DECODE_RESULT.json';data=read(old)
    source=next(r for r in data['videos'] if r['id']=='campus_03')
    assert sha(ROOT/source['source'])==source['sha256']
    negative=read(RUNS/'M539-campus12-demo-media-review-01/RESULT.json');assert negative['primary_rc']==0
    frames={r['index']:r for r in source['frames']};cases=[]
    for index,expected in [(0,'No'),(48,'Yes'),(64,'Yes'),(80,'Yes'),(192,'No')]:
        r=frames[index]
        for file,key in [('source_png','source_sha256'),('input_png','input_png_sha256'),('input_npy','input_npy_sha256')]:assert sha(ROOT/r[file])==r[key]
        cases.append(dict(id='campus03_f'+str(index).zfill(5),frame=r['input_npy'],frame_sha256=r['input_npy_sha256'],
            source_frame_index=index,timestamp_s=r['timestamp_s'],expected=expected,label_origin='assistant_review_of_actual_input_visible_knife_not_whole_clip_label',
            role='clear_knife_demo' if expected=='Yes' else 'same_video_knife_not_visible_control'))
    assert len(cases)==5 and len({r['id'] for r in cases})==5
    pair=dict(version='M540_CAMPUS_DEMO_PAIR_V1',selection_authorization='用户2026-10-26明确选校园灰衣持刀视频（3），配（12）号手机无刀视频。',
        positive=dict(id='campus_03',source=source['source'],source_sha256=source['sha256'],duration_s=source['duration_s'],
            clear_knife_interval_s=[2,4],initial_frame_knife_visible=False,not_all_frames_positive=True),
        negative=dict(id='campus_12',source='data/campus_demo_20261026/campus_12.mp4',source_sha256=negative['source_sha256'],
            software_four_frame_result='deployment/mage_vl4b/optimization_v1/runs/M539-campus12-demo-media-review-01/RESULT.json',
            software_result_sha256=sha(RUNS/'M539-campus12-demo-media-review-01/RESULT.json')),
        UI=dict(Yes='large red knife alert',No='no alert',Invalid='pending/manual review,never treated as No',show_TTFT=False,
            inference_source='actual submitted frame only;never filename/predefined result',playback='start capture on play;single first-frame judgment cannot cover a later knife event'),
        source_origin='AI-generated demonstration',new_positive_video_required=False,no_training=True,heldout_opened=False,
        accepted_on_board=False,web_input_accepted=False,original_contracts_and_evidence_unchanged=True)
    save(OUT/'DEMO_PAIR.json',pair);save(OUT/'SOURCE_DERIVATION.json',dict(files=sources))
    prior=read(RUNS/'M539-campus12-demo-quality-protocol-01/RESULT.json');frozen=dict(prior['frozen'])
    paths=[HERE/'prepare_quality.py',HERE/'quality.py',HERE/'quality_host.py',OUT/'DEMO_PAIR.json',OUT/'SOURCE_DERIVATION.json',old,ROOT/source['source']]
    paths.extend(ROOT/r['frame'] for r in cases)
    for f in paths:
        if f.suffix=='.py':compile(f.read_text(encoding='utf8'),str(f),'exec')
    frozen.update({rel(f):sha(f) for f in paths})
    p=dict(status='FROZEN_M540_SELECTED_CAMPUS03_POSITIVE_AND_VISIBLE_STATE_CONTROLS',cases=cases,frozen=frozen,
        package=prior['package'],package_manifest_sha256=prior['package_manifest_sha256'],budget=dict(full_prefills=len(cases),seconds=900),
        views=2,visual_slots=98,tokens=128,decode_calls=0,no_binary_mask=True,no_training=True,board_commands=0,heldout_opened=False,
        purpose='Verify clear-knife frames of explicitly selected old demo, plus same-video initial/late No controls. No frame/epoch/prompt search.',
        no_claim_first_frame_predicts_future=True,web_or_board_accepted=False,model_numeric_AST_equals_prior=True)
    protocol=RUNS/'M540-campus03-demo-quality-protocol-01/RESULT.json';save(protocol,p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(protocol);synchronized('latest_m540_selected_demo_pair_protocol01',dict(status=p['status'],result=rel(protocol),sha256=h,pair=rel(OUT/'DEMO_PAIR.json'),board=False,promoted=False),
        '## M540按用户明确选择改为旧（3）号校园持刀＋新（12）号手机配对\n\n协议SHA '+h+'；不再等待明天新阳性素材。（3）源SHA '+source['sha256']+'，10.0417s，仅约2–4秒刀在448裁剪清晰，开头无刀、后期刀不可见，不能全片标Yes或仅首帧推未来。新五帧0/2/2.67/3.33/8秒分别No/Yes/Yes/Yes/No冻结；用当前3584/原头/128双视图完整词表，0训练/板/heldout。求值源码仅路径日志与负样本特定摘要字段改名，数值AST保持。配对与UI要求已保存：真实Yes红警、No静默、不显TTFT；目前非Web或实板验收。')
    print(dict(status=p['status'],sha256=h,cases=[(r['timestamp_s'],r['expected']) for r in cases]))
if __name__=='__main__':main()
