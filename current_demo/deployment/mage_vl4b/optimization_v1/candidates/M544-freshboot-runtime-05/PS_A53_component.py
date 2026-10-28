"""Native saved-input PS MLP checks only; no complete visual/language forward."""
import gc,hashlib,json,sys
from pathlib import Path
import numpy as np

def check(pkg):
    read=lambda p:json.loads(Path(p).read_bytes())
    release=Path('/home/ubuntu/tellme_release_install_20260926')
    closure=read(pkg/'SOURCE_CLOSURE.json')
    sys.path[:0]=[str(release/p) for p in closure['module_dirs']]
    import torch
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    from m273_latest_vision_runtime import M273LatestPSVisionRuntime
    from PS_crop_native import PSCropSelector
    parent=release/'deployment/mage_vl4b/m181_m120_video_board_candidate'
    runtime=M273LatestPSVisionRuntime(parent/'ps_vision_payload',parent/'vision_layout',parent/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
    selector=None;rows=[]
    try:
        selector=PSCropSelector(torch,runtime,pkg,idle=lambda:None)
        for arm in ('A','B','A'):
            selector.choose(arm);selector.begin_request()
            for row in selector.rows:
                i=row['index'];x=np.load(pkg/('component_inputs/vision_'+str(i).zfill(2)+'.npy'),allow_pickle=False)
                assert x.shape==(392,1024) and x.dtype==np.float32 and np.isfinite(x).all()
                original=row['original'];dense=[np.asarray(m.store.decode(m.name),np.float32).copy() for m in original]
                biases=[m.bias.detach().clone() for m in original]
                if arm=='B':
                    plan=next(p for p in read(pkg/'PS_NATIVE_PLAN.json')['selected'] if p['index']==i)
                    keep=np.asarray(plan['kept_original_G64_groups']);ids=(keep[:,None]*64+np.arange(64)).reshape(-1)
                    dense=[dense[0][ids],dense[1][:,ids]];biases[0]=biases[0][torch.from_numpy(ids)]
                    for m,w in zip(row['cropped'],dense):assert m.store.decode(m.name).tobytes()==np.ascontiguousarray(w).tobytes()
                with torch.inference_mode():
                    tx=torch.from_numpy(x[None].copy())
                    expected=torch.nn.functional.linear(row['mlp'].activation_fn(torch.nn.functional.linear(tx,torch.from_numpy(dense[0]),biases[0])),torch.from_numpy(np.ascontiguousarray(dense[1])),biases[1])
                    if arm=='B':expected=torch.add(expected,row['R1'])
                    actual=row['mlp'](tx)
                assert actual.dtype==torch.float32 and torch.isfinite(actual).all() and torch.equal(actual,expected),(arm,i)
                rows.append(dict(arm=arm,layer=i,rows=392,full_MLP_native_equal=True,sha256=hashlib.sha256(actual.numpy().tobytes()).hexdigest()))
                del dense,biases,tx,expected,actual;gc.collect()
            selector.end_request()
        selector.close()
        return dict(status='PASS_A53_PS3072_SAVED_LOCAL_MLP_AND_RESTORE',rows=rows,full_model_forwards=0,Overlay=0,DMA=0)
    finally:
        if selector is not None and not selector.closed:selector.close()
        runtime.close();gc.collect()
