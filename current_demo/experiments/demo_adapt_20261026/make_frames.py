"""Decode predeclared clean and label-preserving harder demo views on CPU."""
import sys,traceback,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_adapt import *
def main():
    p=verify(SOURCE);FRAMES.mkdir(exist_ok=False);v=dict(status='FAIL_M541_FRAME_PREPARATION',primary_rc=1,records=[],model_forwards=0,board_commands=0)
    try:
        import cv2
        from PIL import Image,ImageOps,ImageDraw,ImageFont
        sources={r['id']:r for r in p['sources']};tiles=[];font=ImageFont.truetype('/mnt/c/Windows/Fonts/msyh.ttc',16)
        for role,requests in [('fit',p['training']),('fresh-dev',p['fresh_development'])]:
            for j,r in enumerate(requests):
                file=ROOT/sources[r['video']]['path'];cap=cv2.VideoCapture(str(file))
                try:
                    assert cap.isOpened();fps=float(cap.get(cv2.CAP_PROP_FPS));assert cap.set(cv2.CAP_PROP_POS_FRAMES,r['index']);ok,bgr=cap.read();assert ok
                    frame=np.asarray(ImageOps.fit(Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)),(448,448),method=Image.Resampling.LANCZOS),np.uint8)
                finally:cap.release()
                for view in ['clean','hard-train' if role=='fit' else 'hard-check']:
                    image=frame.copy();meta={}
                    if view!='clean':
                        seed=p['seed']*100000+(10000 if role=='fit' else 20000)+j;rng=np.random.default_rng(seed);a=p['augmentation']
                        gamma=float(rng.uniform(*a['gamma']));brightness=float(rng.uniform(*a['brightness']));quality=int(rng.integers(a['JPEG_quality'][0],a['JPEG_quality'][1]+1));noise=float(rng.uniform(*a['gaussian_noise_std_RGB255']))
                        image=np.clip((image.astype(np.float32)/255)**gamma*brightness*255,0,255).round().astype(np.uint8)
                        stream=io.BytesIO();Image.fromarray(image).save(stream,format='JPEG',quality=quality,subsampling=0);stream.seek(0)
                        image=np.clip(np.asarray(Image.open(stream).convert('RGB')).astype(np.float32)+rng.normal(0,noise,image.shape),0,255).round().astype(np.uint8)
                        meta=dict(seed=seed,gamma=gamma,brightness=brightness,JPEG_quality=quality,noise_std=noise)
                    f=FRAMES/(r['id']+'_'+view+'.npy');png=f.with_suffix('.png')
                    with f.open('xb') as h:np.save(h,image,allow_pickle=False)
                    Image.fromarray(image).save(png)
                    row=dict(r,role=role,view=view,timestamp_s=r['index']/fps,frame=rel(f),frame_sha256=sha(f),png=rel(png),png_sha256=sha(png),augmentation=meta)
                    v['records'].append(row);tile=Image.new('RGB',(280,324),'white');tile.paste(Image.fromarray(image).resize((280,280)),(0,0));ImageDraw.Draw(tile).text((4,282),r['id']+' '+r['expected']+'\n'+role+' '+view,font=font,fill='black');tiles.append(tile)
        assert len(v['records'])==24
        for part in range(2):
            batch=tiles[part*12:(part+1)*12];sheet=Image.new('RGB',(1120,324*3),'white')
            for j,t in enumerate(batch):sheet.paste(t,((j%4)*280,(j//4)*324))
            sheet.save(FRAMES/('CONTACT_'+str(part+1)+'.jpg'),quality=94)
        v.update(status='COMPLETE_M541_FRAMES_AWAIT_VISUAL_REVIEW',primary_rc=0,clean_fit=8,hard_fit=8,fresh_clean=4,fresh_hard=4,training_started=False)
    except BaseException:v['traceback']=traceback.format_exc()
    save(FRAMES/'RESULT.json',v);print(v['status'],v.get('traceback',''),flush=True);return v['primary_rc']
if __name__=='__main__':raise SystemExit(main())
