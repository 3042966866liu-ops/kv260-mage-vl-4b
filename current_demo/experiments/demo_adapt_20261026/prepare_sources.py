"""Source-only new demo-development registration before decoding/augmentation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_adapt import *
def main():
    assert not SOURCE.exists()
    old=RUNS/'M540-campus03-demo-media-selection-01/RESULT.json';assert read(old)['semantic_quality_pass'] is False
    pair=read(old.with_name('DEMO_PAIR.json'));sources=[]
    for k in ['positive','negative']:
        r=pair[k];f=ROOT/r['source'];assert sha(f)==r['source_sha256'];sources.append(dict(id=r['id'],path=r['source'],sha256=r['source_sha256']))
    # New training timestamps differ from known failing demonstration checks.
    training=[dict(id='campus03_f'+str(i).zfill(5),video='campus_03',index=i,expected=t) for i,t in [(6,'No'),(52,'Yes'),(68,'Yes'),(84,'Yes'),(176,'No')]]
    training += [dict(id='campus12_f'+str(i).zfill(5),video='campus_12',index=i,expected='No') for i in [48,288,576]]
    fresh=[dict(id='campus03_f'+str(i).zfill(5),video='campus_03',index=i,expected=t) for i,t in [(60,'Yes'),(76,'Yes'),(208,'No')]]
    fresh += [dict(id='campus12_f00360',video='campus_12',index=360,expected='No')]
    paths=[HERE/'common_adapt.py',HERE/'make_frames.py',HERE/'prepare_sources.py',HERE/'host.py',old,old.with_name('DEMO_PAIR.json')]
    for f in paths:
        if f.suffix=='.py':compile(f.read_text(encoding='utf8'),str(f),'exec')
    frozen={rel(f):sha(f) for f in paths};frozen.update({r['path']:r['sha256'] for r in sources})
    v=dict(status='FROZEN_M541_USER_AUTHORIZED_DEMO_DOMAIN_ADAPTATION_SOURCES',authorization='用户明确选（3）＋（12），发现0/3持刀后要求修复；本版本允许对展示域适配，不能当独立泛化。',
        sources=sources,training=training,fresh_development=fresh,frozen=frozen,
        augmentation=dict(gamma=[.92,1.08],brightness=[.92,1.08],JPEG_quality=[88,96],gaussian_noise_std_RGB255=[.5,1.2]),
        seed=541,budgets=dict(frames_seconds=180),no_crop_flip_occlusion=True,
        source_policy='Two explicitly chosen AI-generated demo videos. Known M539/M540 checks retained as demo-development regression,not independent validation. Original reserved/test clips never used for gradients/epochs.',
        model_forwards=0,optimizer_updates=0,board_commands=0,heldout_opened=False)
    save(SOURCE,v)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(SOURCE);synchronized('latest_m541_demo_adapt_sources01',dict(status=v['status'],result=rel(SOURCE),sha256=h,board=False,promoted=False),
        '## M541按用户修复要求独立注册展示域恢复\n\nSOURCE SHA '+h+'；保留M540三持刀漏判，用户选校园（3）＋手机（12），新8训练时点（含同背景无刀）+4新同源开发时点，不暗称独立测试。原5失败/4手机检查保留回归，另随机增强只改变光照/JPEG/小噪声不裁刀。先CPU解码复核，再冻结现有rank8头清晰/较难学生同预算恢复；原10V18L/V4/W4/A8不改，不加新推理支路，不对原reserved/test训练，不上板。')
    print(dict(status=v['status'],sha256=h))
if __name__=='__main__':main()
