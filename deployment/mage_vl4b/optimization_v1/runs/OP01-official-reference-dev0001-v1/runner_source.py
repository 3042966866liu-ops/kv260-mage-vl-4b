"""Full four-frame M120 reconstructed+A8 software diagnostic, NOT bit-exact RTL.

Uses exact board-decoded RGB. Does not call this a PL numerical acceptance or
an official unquantized quality baseline; those require separate comparisons.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'deployment/mage_vl4b/scripts'),
             str(ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate')]
import numpy as np
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from packed_checkpoint_artifact import load_packed_checkpoint
from mage_a8_runtime import install_packed_linear_a8_hooks
from board_preprocess import preprocess
from sys_video_input import render_prompt
from measurement import sha256,write_json,exclusive_lock


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--mode',choices=('m120','official'),default='m120')
    args=parser.parse_args()
    out=BASE/('runs/OP01-software-reference-dev0001-v1' if args.mode=='m120'
              else 'runs/OP01-official-reference-dev0001-v1')
    out.mkdir(exist_ok=False)
    result=dict(status='RUNNING',backend=('WSL_CPU_M120_reconstructed_BF16_A8_QDQ' if args.mode=='m120'
        else 'WSL_CPU_official_BF16_no_A8'),
        board_execution=False,PL_bit_exact_oracle=False,numerical_acceptance=False,
        semantic_quality_pass=False,steps=[],sources={str(p.relative_to(ROOT)):sha256(p) for p in
        [Path(__file__),Path(__file__).with_name('sys_video_input.py'),
         ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate/board_preprocess.py',
         ROOT/'deployment/mage_vl4b/scripts/packed_checkpoint_artifact.py',
         ROOT/'deployment/mage_vl4b/scripts/mage_a8_runtime.py']})
    path=out/'result.json'
    write_json(path,result)
    phase=['identity']; stop=threading.Event(); started=time.perf_counter()
    def heartbeat():
        while not stop.wait(30):print(f'OP01_REFERENCE_HEARTBEAT phase={phase[0]} elapsed_s={time.perf_counter()-started:.1f}',flush=True)
    threading.Thread(target=heartbeat,daemon=True).start()
    handles=[]
    try:
        reference=BASE/'datasets/dev_bootstrap_v1/board_reference_v1'
        binding=json.loads((reference/'result.json').read_text())
        rgbfile=reference/'dev-0001_rgb.npy'
        if sha256(rgbfile)!=binding['rgb_file_sha256']:raise RuntimeError('Board RGB container changed')
        frames=np.load(rgbfile,allow_pickle=False)
        if hashlib.sha256(frames.tobytes()).hexdigest()!=binding['metadata']['raw_sha256']:
            raise RuntimeError('Board RGB payload changed')
        dataset=json.loads((BASE/'datasets/dev_bootstrap_v1/input_manifest.json').read_text())
        sample=dataset['samples'][0]
        times=binding['metadata']['decode']['actual_frame_times_s']
        prompt=render_prompt(sample['question'],times)
        result.update(input_sha256=sample['sha256'],rgb_sha256=binding['metadata']['raw_sha256'],
            question=sample['question'],actual_frame_times_s=times,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
        if sha256(args.checkpoint/'CHECKPOINT_MANIFEST.json')!='5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0':
            raise RuntimeError('M120 checkpoint manifest changed')
        torch.set_num_threads(20)
        phase[0]='load official architecture'+(' and reconstruct M120 weights' if args.mode=='m120' else '')
        model=AutoModelForCausalLM.from_pretrained(args.model,trust_remote_code=True,local_files_only=True,
            torch_dtype=torch.bfloat16,low_cpu_mem_usage=True,attn_implementation='eager',device_map={'':'cpu'}).eval()
        tokenizer=AutoTokenizer.from_pretrained(args.model,trust_remote_code=True,local_files_only=True)
        names=[]
        if args.mode=='m120':
            result['checkpoint']=load_packed_checkpoint(torch,model,args.checkpoint,verify_blob=True,row_chunk=32)
            handles,names=install_packed_linear_a8_hooks(torch,model,args.checkpoint,r'^(model\.language_model\.layers\.|lm_head$)')
            if len(names)!=253:raise RuntimeError('Language A8 coverage differs')
        ids=tokenizer.encode(prompt,add_special_tokens=False)
        if ids.count(model.config.image_token_id)!=784:raise RuntimeError('Visual placeholder count mismatch')
        arrays=preprocess(frames)
        inputs={k:torch.from_numpy(v.copy()) for k,v in arrays.items()}
        inputs.update(input_ids=torch.tensor([ids]),attention_mask=torch.ones((1,len(ids)),dtype=torch.long))
        if len(ids)+31>1024:raise RuntimeError('32-step reference context would exceed board limit')
        result.update(input_token_ids=ids,prompt_tokens=len(ids),language_a8_modules=len(names),
                      torch_version=torch.__version__)
        captured={}
        def capture(module,arguments,kw):captured['inputs_embeds']=kw['inputs_embeds'].detach().float().cpu().numpy().copy()
        hook=model.language_model.register_forward_pre_hook(capture,with_kwargs=True)
        phase[0]='four-frame visual and language prefill'
        with torch.inference_mode():
            forward=model(**inputs,use_cache=True,output_hidden_states=True,logits_to_keep=1)
        hook.remove()
        np.savez_compressed(out/'prefill_reference.npz',inputs_embeds=captured['inputs_embeds'],
            layer0_output=forward.hidden_states[1].detach().float().numpy(),
            final_hidden=forward.hidden_states[-1][:,-1].detach().float().numpy(),
            logits=forward.logits[0,-1].detach().float().numpy())
        result['prefill_reference_sha256']=sha256(out/'prefill_reference.npz')
        eos=model.config.text_config.eos_token_id
        eos={eos} if isinstance(eos,int) else set(eos)
        logits_all=[];valid=[]
        phase[0]='causal decode (up to32, respect EOS)'
        with torch.inference_mode():
            for step in range(32):
                if not torch.isfinite(forward.logits).all():raise RuntimeError('Nonfinite reference logits')
                token=int(forward.logits[0,-1].argmax())
                length=forward.past_key_values.get_seq_length()
                if length!=len(ids)+step:raise RuntimeError('Reference KV length mismatch')
                logits_all.append(forward.logits[0,-1].float().numpy().copy())
                result['steps'].append(dict(token_id=token,kv_length=length,eos=token in eos))
                write_json(path,result)
                print(f'OP01_REFERENCE_TOKEN step={step} id={token} kv={length}',flush=True)
                if token in eos:
                    result['finish_reason']='eos';break
                valid.append(token)
                if step==31:
                    result['finish_reason']='length';break
                forward=model(input_ids=torch.tensor([[token]]),past_key_values=forward.past_key_values,
                    attention_mask=torch.ones((1,len(ids)+step+1),dtype=torch.long),
                    position_ids=torch.tensor([[len(ids)+step]]),cache_position=torch.tensor([len(ids)+step]),
                    use_cache=True,logits_to_keep=1)
        np.savez_compressed(out/'decode_reference.npz',logits=np.stack(logits_all))
        result.update(status='PASS',valid_token_ids=valid,answer=tokenizer.decode(valid,skip_special_tokens=True),
            decode_reference_sha256=sha256(out/'decode_reference.npz'),
            note=('Software execution only. BF16 GEMM/A8 QDQ and vision policy differ from PL/M207; compare before numeric acceptance.'
                  if args.mode=='m120' else 'Official BF16 software reference; no packed weight replacement or A8 hooks. Not board performance or semantic acceptance.'))
    except Exception as exc:
        result.update(status='FAIL',error=f'{type(exc).__name__}: {exc}',failed_phase=phase[0])
    finally:
        stop.set()
        for handle in handles:handle.remove()
        result['software_wall_s']=time.perf_counter()-started
        write_json(path,result)
    print(json.dumps({k:result.get(k) for k in ('status','answer','error','software_wall_s') }),flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    with exclusive_lock(BASE/'software_reference.lock'):raise SystemExit(main())
