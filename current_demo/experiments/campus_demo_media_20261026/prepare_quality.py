"""Assistant visual review and four predeclared new demonstration frames."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs';OUT=RUNS/'M539-campus12-demo-media-review-01'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.open('x',encoding='utf8').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
    d=read(OUT/'DECODE_RESULT.json');host=read(OUT/'HOST_RESULT.json');assert d['primary_rc']==host['host_rc']==0
    intake=ROOT/'data/campus_demo_20261026/INTAKE.json';i=read(intake);assert sha(ROOT/i['workspace_source'])==i['sha256']
    for f in d['frames']:
        for n,k in [('source_png','source_sha256'),('input_png','input_png_sha256'),('input_npy','input_npy_sha256')]:assert sha(ROOT/f[n])==f[k]
    frames=[]
    for time in [0,1,8,20]:
        f=min(d['frames'],key=lambda a:abs(a['timestamp_s']-time))
        frames.append(dict(id='campus12_f'+str(f['index']).zfill(5),frame=f['input_npy'],frame_sha256=f['input_npy_sha256'],
            source_frame_index=f['index'],timestamp_s=f['timestamp_s'],expected='No',label_origin='assistant_visual_review_not_human_confirmed',role='user_demo_development'))
    assert len({f['id'] for f in frames})==4
    review=dict(status='ASSISTANT_VISUAL_REVIEW_COMPLETE_MODEL_PENDING',source=i['workspace_source'],source_sha256=i['sha256'],
        duration_s=d['duration_s'],fps=d['fps'],width=d['width'],height=d['height'],frame_count=d['frame_count'],
        reviewed_sample_count=len(d['frames']),contact_sheets=d['contact_sheets'],scene='走廊中蓝色外套人物走近，约7至8秒后拿起并查看手机。',
        observation='本次均匀抽帧及首秒补帧未见明确刀具；手机在后半段可见。仅对已复核帧记No，不以片名判标签、不证明未抽到帧均无刀。',
        proposed_demo_role='No-alarm negative demonstration',AI_generated_watermark_visible=True,training_authorized_by_this_intake=False,
        human_label_confirmed=False,new_positive_video_pending=True,selected_frames=frames,model_prediction=None,
        preprocessing_limit='PIL_LANCZOS_center448 review input; browser exact RGB export requires separate identity/acceptance. Not equal to arbitrary uploaded Web frame by assumption.',
        model_runs=0,board_commands=0,heldout_opened=False)
    save(OUT/'VISUAL_REVIEW.json',review)
    oldcontracts=[OPT/'contracts/EVALUATION_DATASET.json',OPT/'contracts/EVALUATION_DATASET_M464_KNIFE_VIDEO_V1.json',OPT/'contracts/EVALUATION_DATASET_M530_CAMPUS_DEMO_V1.json']
    contract=OPT/'contracts/EVALUATION_DATASET_M539_CAMPUS_DEMO_V2.json'
    save(contract,dict(version='M539_CAMPUS_DEMO_V2',purpose='Explicit actual user demonstration source,development-only',source_review=rel(OUT/'VISUAL_REVIEW.json'),
        source_review_sha256=sha(OUT/'VISUAL_REVIEW.json'),source=i['workspace_source'],source_sha256=i['sha256'],
        previous_contracts_unchanged={rel(f):sha(f) for f in oldcontracts},expected_only_on_reviewed_frames='No',labels_from_filenames=False,
        human_label_confirmed=False,training_started=False,heldout_opened=False))
    old=read(RUNS/'M537-V4-matched-ablation-protocol-01/RESULT.json');frozen=dict(old['frozen'])
    paths=[HERE/'prepare_quality.py',HERE/'quality.py',HERE/'quality_host.py',HERE/'intake.py',HERE/'decode.py',intake,OUT/'DECODE_RESULT.json',OUT/'VISUAL_REVIEW.json',contract]
    paths.extend(ROOT/r['frame'] for r in frames)
    pkg=OPT/'candidates/M536-V4-3584-recovery-01';paths.extend(pkg/f['path'] for f in read(pkg/'PACKAGE_MANIFEST.json')['files']);paths.append(pkg/'PACKAGE_MANIFEST.json')
    paths.extend(oldcontracts)
    for f in paths:
        if f.suffix=='.py':compile(f.read_text(encoding='utf8'),str(f),'exec')
    frozen.update({rel(f):sha(f) for f in paths})
    p=dict(status='FROZEN_M539_NEW_VIDEO_FOUR_FRAME_SOFTWARE_ACCEPTANCE',cases=frames,frozen=frozen,package=rel(pkg),
        package_manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),budget=dict(full_prefills=len(frames),seconds=900),
        tokens=128,visual_slots=98,views=2,decode_calls=0,head_frozen=True,new_training_steps=0,board_commands=0,heldout_opened=False,
        no_no_bias_or_binary_mask=True,prior_positive_controls='M536 exact same component fixed chef cal04t0/cal04t1 both Yes;reused historical controls,not new-video positive acceptance.',
        limits='Four predeclared reviewed frames;not full-video, browser or board acceptance;no epoch/group/prompt tuning on this demo.')
    dest=RUNS/'M539-campus12-demo-quality-protocol-01/RESULT.json';save(dest,p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(dest);synchronized('latest_m539_campus12_intake_protocol01',dict(status=p['status'],result=rel(dest),sha256=h,board=False,promoted=False),
        '## M539新增实际演示视频：30秒手机无刀画面复核与软件验收冻结\n\n协议SHA '+h+'；源'+i['sha256']+'，1280×720/24fps/721帧/30.0417s，均匀抽帧及首秒补帧可见蓝衣人物走廊拿手机、未见明确刀具，AI水印可见，仅assistant画面标签未成人类确认。独立V2合同不覆盖M530/原数据，0训练/heldout/板。预定0/1/约8/约20秒四帧用当前3584+原头128双视图完整词表判断，非全片/浏览器/板端通过。明天新有刀素材待接收。')
    print(dict(protocol=rel(dest),sha256=h,cases=[(r['id'],r['timestamp_s']) for r in frames]))
if __name__=='__main__':main()
