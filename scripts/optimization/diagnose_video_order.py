"""Unmodified official CLI plus controlled temporal/position probes.

Only read-only hooks inspect actual Conv2d inputs. No model/processor source is
patched. This is a development diagnosis, not board or quality acceptance.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['OMP_NUM_THREADS']='20'
os.environ['MKL_NUM_THREADS']='20'
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import argparse
from pathlib import Path
import subprocess
import sys
import time
import threading
sys.dont_write_bytecode=True
from measurement import sha256,write_json,exclusive_lock
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
MODEL=Path('/home/lyy/models/Mage-VL')
OUT=BASE/'runs/OP01-video-order-diagnostic-v1'


def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--wording',action='store_true')
    args=parser.parse_args()
    if args.wording:OUT=BASE/'runs/OP01-video-wording-diagnostic-v1'
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',board_executed=False,formal_quality_pass=False,cases=[])
    phase=['native official CLI'];stop=threading.Event();start=time.perf_counter()
    def heartbeat():
        while not stop.wait(30):print('VIDEO_DIAG_HEARTBEAT '+phase[0],flush=True)
    threading.Thread(target=heartbeat,daemon=True).start()
    try:
        dataset=BASE/'datasets/dev_bootstrap_v1'
        sample=json.loads((dataset/'input_manifest.json').read_text())['samples'][0]
        video=dataset/sample['file']
        if sha256(video)!=sample['sha256']:raise RuntimeError('Video identity changed')
        entry=MODEL/'inference.py';before=sha256(entry)
        command=[sys.executable,'-B',str(entry),'--mode','offline','--video',str(video),
            '--model',str(MODEL),'--video-backend','frames','--num-frames','4',
            '--max-new-tokens','32','--question',sample['question']]
        if args.wording:
            prior=BASE/'runs/OP01-video-order-diagnostic-v1/result.json'
            result['native_cli']=json.loads(prior.read_text())['native_cli']
            result['reused_native_result_sha256']=sha256(prior)
            if result['native_cli']['entry_sha256']!=before:raise RuntimeError('Native source changed')
        else:
            with (OUT/'native_stdout.txt').open('w') as stdout,(OUT/'native_stderr.txt').open('w') as stderr:
                proc=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=300)
            result['native_cli']=dict(command=command,exit_code=proc.returncode,entry_sha256=before,
                entry_unchanged=sha256(entry)==before,stdout=(OUT/'native_stdout.txt').read_text(),
                stdout_sha256=sha256(OUT/'native_stdout.txt'),stderr_sha256=sha256(OUT/'native_stderr.txt'),
                note='Untouched official CLI samples linspace0..47 =>0,15,31,47; not contract PTS quartet')
        write_json(OUT/'result.json',result)
        print('NATIVE_CLI '+json.dumps(result['native_cli']),flush=True)
        if result['native_cli']['exit_code']:raise RuntimeError('Native CLI failed; preserve raw stderr before retry')
        import numpy as np
        import torch
        from PIL import Image,ImageDraw
        from transformers import AutoModelForCausalLM,AutoProcessor
        torch.set_num_threads(20)
        phase[0]='load official model for controlled probes'
        processor=AutoProcessor.from_pretrained(MODEL,trust_remote_code=True,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(MODEL,trust_remote_code=True,
            local_files_only=True,torch_dtype='auto',device_map={'':'cpu'}).eval()
        frames=np.load(dataset/'board_reference_v1/dev-0001_rgb.npy',allow_pickle=False)
        questions=[('direction',sample['question']),
            ('first_position','In the first frame, is the red circle on the left or right side of the image?'),
            ('last_position','In the last frame, is the red circle on the left or right side of the image?')]
        if args.wording:
            questions=[('reversed_options','In which direction does the red circle move, right to left or left to right?'),
                ('open_direction','Describe the direction in which the red circle moves across the video.'),
                ('structured_direction','State the red circle position in the first frame and the last frame, then state its movement direction.')]
        result['model_dtype']=str(model.dtype)
        result['bounded_protocol']='Exactly three frozen questions in two frame orders; no answer-guided retries'
        for reverse in (False,True):
            ordered=frames[::-1].copy() if reverse else frames.copy()
            for kind,question in questions:
                case=('reversed_' if reverse else 'forward_')+kind
                phase[0]=case
                messages=[{'role':'user','content':[{'type':'video'},{'type':'text','text':question}]}]
                text=processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
                inputs=processor(text=[text],videos=[list(ordered)],return_tensors='pt',padding=True)
                inputs={k:v.to(model.device) if hasattr(v,'to') else v for k,v in inputs.items()}
                inputs['pixel_values']=inputs['pixel_values'].to(model.dtype)
                captured=[]
                def capture(module,args):
                    captured.append(args[0].detach().float().cpu().numpy().copy())
                hook=model.model.visual.embeddings.patch_embedding.register_forward_pre_hook(capture)
                tick=time.perf_counter()
                try:
                    with torch.inference_mode():
                        output=model.generate(**inputs,max_new_tokens=32,do_sample=False)
                finally:hook.remove()
                answer=processor.tokenizer.decode(output[0,inputs['input_ids'].shape[1]:],skip_special_tokens=True)
                if len(captured)!=1:raise RuntimeError('Unexpected vision executions '+str(len(captured)))
                patches=captured[0]
                if patches.shape!=(3136,3,16,16):raise RuntimeError('Actual patch shape changed '+str(patches.shape))
                spatial=patches.reshape(4,14,14,2,2,3,16,16).transpose(0,5,1,3,6,2,4,7).reshape(4,3,448,448)
                # Reverse only normalization for visualization; the captured tensor is separately retained.
                mean=np.asarray(processor.image_processor.image_mean,np.float32).reshape(1,3,1,1)
                std=np.asarray(processor.image_processor.image_std,np.float32).reshape(1,3,1,1)
                restored=np.rint(np.clip((spatial*std+mean)*255,0,255)).astype(np.uint8).transpose(0,2,3,1)
                centers=[]
                for frame in restored:
                    f=frame.astype(np.int16);mask=(f[:,:,0]>150)&(f[:,:,0]-f[:,:,1]>80)&(f[:,:,0]-f[:,:,2]>80)
                    _,xs=np.nonzero(mask);centers.append(float(xs.mean()))
                panel=Image.new('RGB',(1792,474),'white');draw=ImageDraw.Draw(panel)
                for i,frame in enumerate(restored):
                    panel.paste(Image.fromarray(frame),(448*i,26));draw.text((448*i+10,5),f'{i+1}: x={centers[i]:.2f}',fill='black')
                panel.save(OUT/(case+'_vision_input.png'))
                np.savez_compressed(OUT/(case+'_vision_input.npz'),conv_input=patches,
                    patch_positions=inputs['patch_positions'].cpu().numpy(),grid=inputs['image_grid_thw'].cpu().numpy())
                item=dict(case=case,question=question,answer=answer,prompt_tokens=int(inputs['input_ids'].shape[1]),
                    token_ids=output[0,inputs['input_ids'].shape[1]:].tolist(),
                    actual_conv_input_shape=list(patches.shape),decoded_red_centers_x=centers,
                    reconstruction_max_u8_error=int(np.max(np.abs(restored.astype(np.int16)-ordered.astype(np.int16)))),
                    capture_sha256=sha256(OUT/(case+'_vision_input.npz')),
                    visual_panel=str(OUT/(case+'_vision_input.png')),elapsed_s=time.perf_counter()-tick,
                    source_indices=([42,30,18,6] if reverse else [6,18,30,42]),
                    note='Official predecoded-frame entry dense time tags0..3, identical except tested question/frame order')
                result['cases'].append(item);write_json(OUT/'result.json',result)
                print('VIDEO_DIAG_CASE '+json.dumps(item),flush=True)
        result['status']='MEASURED'
    except Exception as exc:result.update(status='FAIL',error=f'{type(exc).__name__}: {exc}',phase=phase[0])
    finally:
        stop.set();result['wall_s']=time.perf_counter()-start;write_json(OUT/'result.json',result)
    print('VIDEO_DIAG_END '+result['status'],flush=True)
    return 0 if result['status']=='MEASURED' else 1

if __name__=='__main__':
    with exclusive_lock(BASE/'software_reference.lock'):raise SystemExit(main())
