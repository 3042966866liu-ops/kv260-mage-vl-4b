"""CPU-only source and canonical448 contact sheets, no model predictions."""
import cv2,numpy as np,json,hashlib,traceback
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/campus_demo_20261026'
OUT=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M539-campus12-demo-media-review-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def main():
    intake=json.loads((DATA/'INTAKE.json').read_bytes());source=ROOT/intake['workspace_source'];assert sha(source)==intake['sha256']
    result=dict(status='FAIL_CPU_SOURCE_DECODE',primary_rc=1,frames=[],source_sha256=sha(source),model_runs=0,board_commands=0)
    cap=cv2.VideoCapture(str(source))
    try:
        assert cap.isOpened();fps=float(cap.get(cv2.CAP_PROP_FPS));n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        assert fps>0 and n>0 and w>0 and h>0
        indices=sorted(set([0,min(n-1,round(fps*.25)),min(n-1,round(fps))]+np.rint(np.linspace(0,n-1,min(32,n))).astype(int).tolist()))
        font=ImageFont.truetype('/mnt/c/Windows/Fonts/msyh.ttc',16);sheets=[]
        for index in indices:
            assert cap.set(cv2.CAP_PROP_POS_FRAMES,index);ok,bgr=cap.read();assert ok
            rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB);image=Image.fromarray(rgb);crop=ImageOps.fit(image,(448,448),method=Image.Resampling.LANCZOS)
            stem='frame_'+str(index).zfill(5);original=OUT/(stem+'.source.png');inputpng=OUT/(stem+'.input448.png');npy=OUT/(stem+'.input448.npy')
            image.save(original);crop.save(inputpng)
            with npy.open('xb') as f:np.save(f,np.asarray(crop,np.uint8),allow_pickle=False)
            result['frames'].append(dict(index=int(index),timestamp_s=index/fps,source_png=rel(original),source_sha256=sha(original),input_png=rel(inputpng),input_png_sha256=sha(inputpng),input_npy=rel(npy),input_npy_sha256=sha(npy)))
            tiles=[]
            for img in [image,crop]:
                t=Image.new('RGB',(320,210),'#f5f6f8');thumb=ImageOps.contain(img,(316,174));t.paste(thumb,((320-thumb.width)//2,2))
                ImageDraw.Draw(t).text((8,180),f'{index/fps:.2f}s  frame {index}',fill='#102234',font=font);tiles.append(t)
            sheets.append(tiles)
        outputs=[]
        for kind,i in [('SOURCE_CONTACT',0),('INPUT448_CONTACT',1)]:
            for part in range((len(sheets)+15)//16):
                batch=sheets[part*16:(part+1)*16];sheet=Image.new('RGB',(1280,40+210*((len(batch)+3)//4)),'white')
                ImageDraw.Draw(sheet).text((12,8),f'campus12 | {w}x{h} | {n/fps:.3f}s | {kind} | {part+1}',font=font,fill='#102234')
                for j,t in enumerate(batch):sheet.paste(t[i],((j%4)*320,40+(j//4)*210))
                dest=OUT/(kind+'_'+str(part+1)+'.jpg');sheet.save(dest,quality=93);outputs.append(dict(path=rel(dest),sha256=sha(dest)))
        result.update(status='COMPLETE_CPU_DECODE_AWAITING_VISUAL_REVIEW',primary_rc=0,fps=fps,frame_count=n,width=w,height=h,duration_s=n/fps,contact_sheets=outputs,
            crop_note='PIL center-crop448 review, not browser-pixel identity or full deployed global/detail preprocessing.',labels_inferred=False,training_started=False,heldout_opened=False)
    except BaseException:result['traceback']=traceback.format_exc()
    finally:cap.release()
    (OUT/'DECODE_RESULT.json').open('x',encoding='utf8').write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print({k:result[k] for k in ['status','primary_rc','duration_s','width','height','fps','frame_count'] if k in result},result.get('traceback',''),flush=True)
    return result['primary_rc']
if __name__=='__main__':raise SystemExit(main())
