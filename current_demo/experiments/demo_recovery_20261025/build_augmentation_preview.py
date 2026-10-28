"""Paired training-only views. Contact-sheet labels never enter training arrays."""
from common_recovery import *
import io
def main():
    import numpy as np
    from PIL import Image,ImageDraw
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'));policy=read(RUNS/(PREFIX+'-augmentation-policy-01/RESULT.json'))
    out=RUNS/(PREFIX+'-augmentation-preview-01');assert not out.exists();out.mkdir()
    chosen={r['id']:r for r in p['train_requests'] if r['id'] in policy['first_safe_augmentation_scope']};assert len(chosen)==4
    sheet=Image.new('RGB',(448*3,480*4),'white');draw=ImageDraw.Draw(sheet);records=[]
    for row,(name,r) in enumerate(chosen.items()):
        source=ROOT/r['frames'];assert sha(source)==r['frames_sha256'];frame=np.load(source,allow_pickle=False)[r['timestamp_index']].copy();assert frame.shape==(448,448,3) and frame.dtype==np.uint8
        for col,stage in enumerate(policy['initial_curriculum']):
            seed=524+row*100+col;rng=np.random.default_rng(seed)
            gamma=float(rng.uniform(*stage['gamma']));brightness=float(rng.uniform(*stage['brightness']));quality=int(rng.integers(stage['JPEG_quality'][0],stage['JPEG_quality'][1]+1));noise=float(rng.uniform(*stage['gaussian_noise_std_RGB255']))
            if stage['stage']==0:image=frame.copy()
            else:
                pixels=np.clip(((frame.astype(np.float32)/255)**gamma)*brightness*255,0,255).round().astype(np.uint8)
                buffer=io.BytesIO();Image.fromarray(pixels).save(buffer,format='JPEG',quality=quality,subsampling=0);buffer.seek(0)
                pixels=np.asarray(Image.open(buffer).convert('RGB')).astype(np.float32)
                image=np.clip(pixels+rng.normal(0,noise,pixels.shape),0,255).round().astype(np.uint8)
            assert image.shape==frame.shape and image.dtype==np.uint8
            file=out/'training_views'/name/(stage['name']+'.npy');file.parent.mkdir(parents=True,exist_ok=True)
            with file.open('xb') as stream:np.save(stream,image,allow_pickle=False)
            records.append(dict(source_request=name,source_split='fit',teacher_request=name,source_frame_file=relative(source),source_frame_SHA256=sha(source),source_timestamp_index=r['timestamp_index'],student_view=stage['name'],student_file=relative(file),student_sha256=sha(file),seed=seed,gamma=gamma,brightness=brightness,JPEG_quality=quality,noise_std_RGB255=noise,geometry_changed=False,source_label_unchanged=True,positive_visibility_not_automatically_guaranteed=True,used_for_training=False))
            sheet.paste(Image.fromarray(image),(448*col,480*row));draw.text((448*col+8,480*row+451),name+' / '+stage['name']+' / TRAIN ONLY',fill='black')
    sheet.save(out/'CONTACT_SHEET.png')
    save(out/'RESULT.json',dict(status='PAIRED_TRAINING_AUGMENTATION_PREVIEW_ONLY',records=records,training_whitelist=[r['student_file'] for r in records],contact_sheet_not_training_input=True,actual_training_steps=0,reserved_cal_views_generated=0,test_views_generated=0,geometry_preserved=True,visibility_review_pending=True,source_sha256=sha(__file__)))
    print('TRAINING_ONLY_AUGMENTED_VIEWS',len(records),relative(out/'CONTACT_SHEET.png'),flush=True)
if __name__=='__main__':main()
