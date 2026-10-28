"""Common explicit explanation task over original M455 two-view input.

This intentionally replaces the old constrained 0/1 task for BOTH arms.
It does not change view creation, model math, token cap or native generation.
"""
import numpy as np
QUESTION='Is a knife visible in these views'

def render(timestamp=3.0):
    frames=('<|vision_start|>'+('<|image_pad|>'*49)+'<|vision_end|>')*2
    return '<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n'+frames+QUESTION+'<|im_end|>\n<|im_start|>assistant\n'

class RequestPreparation:
    def __init__(self,engine,frames,provider,preprocess,embeddings,expected_ids):
        if not callable(provider) or not callable(preprocess) or not callable(embeddings):raise ValueError('Original native callbacks required')
        f=np.asarray(frames)
        if f.shape!=(4,448,448,3) or f.dtype!=np.uint8:raise ValueError('Original M455 four-frame source window required')
        if not isinstance(expected_ids,list) or len(expected_ids)!=128 or expected_ids.count(151655)!=98:raise ValueError('Explicit common prompt with exactly98 visual slots required')
        self.engine,self.provider,self.preprocess,self.embeddings=engine,provider,preprocess,embeddings
        self.frames=np.array(f,copy=True,order='C');self.frames.setflags(write=False);self.ids=list(expected_ids)
    def __call__(self):
        # Count actual rendered IDs BEFORE any preprocessing or visual/model callback.
        ids=[int(i) for i in self.engine.tokenizer.encode(render(),add_special_tokens=False).ids]
        if len(ids)!=128 or (len(ids)+31)//32!=4:raise RuntimeError('Actual input exceeds five T32 blocks; no forward allowed')
        if ids!=self.ids:raise RuntimeError('Actual frozen five-block token IDs differ')
        tensors=self.preprocess(np.ascontiguousarray(self.frames[-1:]))
        if tensors['pixel_values'].shape!=(392,768) or int(tensors['view_count'])!=2 or int(tensors['merged_visual_tokens'])!=98:raise RuntimeError('Actual unchanged M455 preprocessing geometry required')
        visual=self.provider(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
        hidden=self.embeddings(self.engine.language,ids,visual)
        if hidden.shape!=(len(ids),2560) or hidden.dtype!=np.float32 or not np.isfinite(hidden).all():raise RuntimeError('Original complete native embedding preparation differs')
        return hidden,dict(task='visible knife plus one-sentence evidence',source_frames=4,selected_frame_index=3,views=2,visual_tokens=98,
            prompt_tokens=len(ids),prompt_T32_blocks=(len(ids)+31)//32,max_input_tokens=128,generation_cap=32,token_ids=ids,old_constrained_0_1_decision_used=False,video_file_decode_included=False,preprocess_vision_embedding_included=True)

def same_prefix_KL(reference,candidate):
    a,b=np.asarray(reference),np.asarray(candidate)
    if a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=151936 or not 1<=len(a)<=32 or a.dtype!=np.float32 or b.dtype!=np.float32 or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Complete matching-prefix native FP32 logits required')
    rows=[]
    for x,y in zip(a,b):
        x=x.astype(np.float64);y=y.astype(np.float64)
        lx=x-(x.max()+np.log(np.exp(x-x.max()).sum()));ly=y-(y.max()+np.log(np.exp(y-y.max()).sum()))
        value=float(np.sum(np.exp(lx)*(lx-ly)))
        if value < -1e-10 or not np.isfinite(value):raise FloatingPointError('KL computation invalid')
        rows.append(max(0.,value))
    return dict(direction='original_M455_to_pruned_M455',per_position=rows,mean=float(np.mean(rows)),max=float(np.max(rows)),semantic_quality_pass=None)
