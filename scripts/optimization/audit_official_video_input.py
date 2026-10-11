"""Compare the fixed board adapter to official primitives with identical RGB/PTS.

The official default sampler is not used: the contract requires .5/1.5/2.5/3.5.
Preserve its actual source frame indices and exact training text format instead.
"""
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
MODEL=Path('/home/lyy/models/Mage-VL')
sys.path[:0]=[str(MODEL),str(ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate')]
import numpy as np
import torch
from transformers import Qwen2VLImageProcessor,AutoTokenizer
from processing_mage_vl import _expand_video_block_for_frames
from video_processing_mage_vl import build_patch_positions
from board_preprocess import preprocess
from sys_video_input import render_prompt
from measurement import sha256,write_json

out=BASE/'runs/OP01-official-input-audit-v1'
out.mkdir(exist_ok=False)
reference=BASE/'datasets/dev_bootstrap_v1/board_reference_v1'
binding=json.loads((reference/'result.json').read_text())
rgbfile=reference/'dev-0001_rgb.npy'
if sha256(rgbfile)!=binding['rgb_file_sha256']:raise RuntimeError('RGB file mismatch')
frames=np.load(rgbfile,allow_pickle=False)
decoded=binding['metadata']['decode']
times=decoded['actual_frame_times_s']; indices=decoded['selected_frame_indices']
sample=json.loads((BASE/'datasets/dev_bootstrap_v1/input_manifest.json').read_text())['samples'][0]
ip=Qwen2VLImageProcessor.from_pretrained(MODEL,local_files_only=True)
# Input is already contract-resized448; do not change the number of pixels/tokens.
official=ip(images=list(frames),do_resize=False,return_tensors='pt')
pp=build_patch_positions(torch.tensor([[4,28,28]]),spatial_merge_size=2,
                         frame_indices=[torch.tensor(indices)])
arrays={k:official[k].numpy() for k in ('pixel_values','image_grid_thw')}
arrays['patch_positions']=pp.numpy()
legacy=preprocess(frames)
metrics={}
for name in arrays:
    a,b=arrays[name],legacy[name]
    if a.shape!=b.shape:raise RuntimeError('Shape mismatch '+name)
    metrics[name]=dict(shape=list(a.shape),exact=bool(np.array_equal(a,b)),
        max_abs=float(np.max(np.abs(a.astype(np.float64)-b.astype(np.float64)))),
        different_elements=int(np.count_nonzero(a!=b)))
tokenizer=AutoTokenizer.from_pretrained(MODEL,trust_remote_code=True,local_files_only=True)
messages=[{'role':'system','content':'You are a helpful assistant.'},
    {'role':'user','content':[{'type':'video','video':'input.mp4'},
                             {'type':'text','text':sample['question']}]}]
template=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
placeholder='<|vision_start|><|video_pad|><|vision_end|>'
if template.count(placeholder)!=1:raise RuntimeError('Unexpected native video template')
prompt=template.replace(placeholder,_expand_video_block_for_frames(196,times))
oldprompt=render_prompt(sample['question'],times)
ids=tokenizer.encode(prompt,add_special_tokens=False)
if ids.count(tokenizer.convert_tokens_to_ids('<|image_pad|>'))!=784:raise RuntimeError('Visual slot count changed')
np.savez_compressed(out/'official_input.npz',**arrays)
write_json(out/'prompt.json',dict(prompt=prompt,input_token_ids=ids))
result=dict(status='MEASURED',scope='Official video input primitive audit, no inference or board mutation',
    source_hashes={str(p):sha256(p) for p in [MODEL/'processing_mage_vl.py',MODEL/'video_processing_mage_vl.py',
        MODEL/'preprocessor_config.json',MODEL/'chat_template.jinja',Path(__file__)]},
    actual_pts=times,source_frame_indices=indices,legacy_temporal_positions=[0,1,2,3],
    array_comparison=metrics,prompt_equal=prompt==oldprompt,
    official_prompt_token_count=len(ids),legacy_prompt_token_count=len(tokenizer.encode(oldprompt,add_special_tokens=False)),
    official_prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
    input_bundle_sha256=sha256(out/'official_input.npz'),prompt_file_sha256=sha256(out/'prompt.json'),
    numerical_acceptance=False,semantic_quality_pass=False)
write_json(out/'result.json',result)
print(json.dumps(result))
