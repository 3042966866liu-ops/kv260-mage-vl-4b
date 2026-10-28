"""New unseen temporal samples and mild independent perturbations, CPU only."""
import sys,traceback,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_fix import *
def main():
    p=verify(FRAMEPROTO);FRAMES.mkdir(exist_ok=False);v=dict(status='FAIL_M542_NEW_FRAMES',primary_rc=1,records=[],model_forwards=0)
    try:
        import cv2
        from PIL import Image,ImageOps,ImageFont,ImageDraw
        tiles=[];font=ImageFont.truetype('/mnt/c/Windows/Fonts/msyh.ttc',16)
        for j,r in enumerate(p['new_temporal_cases']):
            file=ROOT/p['videos'][r['video']]['path'];cap=cv2.VideoCapture(str(file))
            try:
                assert cap.isOpened();fps=float(cap.get(cv2.CAP_PROP_FPS));assert cap.set(cv2.CAP_PROP_POS_FRAMES,r['index']);ok,bgr=cap.read();assert ok
                frame=np.asarray(ImageOps.fit(Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)),(448,448),method=Image.Resampling.LANCZOS),np.uint8)
            finally:cap.release()
            for view in ['clean','hard-check']:
                a=frame.copy();meta={}
                if view=='hard-check':
                    rng=np.random.default_rng(542900+j);gamma=float(rng.uniform(.92,1.08));brightness=float(rng.uniform(.92,1.08));quality=int(rng.integers(88,97));noise=float(rng.uniform(.5,1.2))
                    a=np.clip((a.astype(np.float32)/255)**gamma*brightness*255,0,255).round().astype(np.uint8)
                    b=io.BytesIO();Image.fromarray(a).save(b,format='JPEG',quality=quality,subsampling=0);b.seek(0)
                    a=np.clip(np.asarray(Image.open(b).convert('RGB')).astype(np.float32)+rng.normal(0,noise,a.shape),0,255).round().astype(np.uint8)
                    meta=dict(seed=542900+j,gamma=gamma,brightness=brightness,JPEG_quality=quality,noise_std=noise)
                name=r['id']+'_'+view;f=FRAMES/(name+'.npy');png=FRAMES/(name+'.png')
                with f.open('xb') as stream:np.save(stream,a,allow_pickle=False)
                Image.fromarray(a).save(png);v['records'].append(dict(r,key=name,view=view,role='new-temporal-check',frame=rel(f),frame_sha256=sha(f),png=rel(png),png_sha256=sha(png),
                    timestamp_s=r['index']/fps,target=9454 if r['expected']=='Yes' else 2753,augmentation=meta))
                tile=Image.new('RGB',(280,325),'white');tile.paste(Image.fromarray(a).resize((280,280)),(0,0));ImageDraw.Draw(tile).text((4,283),r['id']+' '+r['expected']+'\n'+view,font=font,fill='black');tiles.append(tile)
        sheet=Image.new('RGB',(1120,975),'white')
        for j,t in enumerate(tiles):sheet.paste(t,((j%4)*280,(j//4)*325))
        sheet.save(FRAMES/'CONTACT.jpg',quality=95);v.update(status='COMPLETE_M542_NEW_FRAMES_AWAIT_REVIEW',primary_rc=0)
    except BaseException:v['traceback']=traceback.format_exc()
    save(FRAMES/'RESULT.json',v);print(v['status'],v.get('traceback',''),flush=True);return v['primary_rc']
if __name__=='__main__':raise SystemExit(main())
