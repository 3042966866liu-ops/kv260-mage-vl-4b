"""M120 reconstructed-weight/A8 software adapter gate; no board operations.

This uses the existing M307 software reference, not an RTL/PL bit-exact oracle.
Fixed engineering fixture, no independent semantic accuracy claim.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'deployment/mage_vl4b/scripts')]
sys.dont_write_bytecode = True
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from mage_a8_runtime import install_packed_linear_a8_hooks
from packed_checkpoint_artifact import load_packed_checkpoint
from bact.token_layout import select_layout
from bact.feature_budget import propose_budgets

MANIFEST = '5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0'
BLOB = '9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix('.partial.json')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--checkpoint', type=Path, required=True)
    ap.add_argument('--preflight-only', action='store_true')
    args = ap.parse_args()
    outpath = ROOT/'deployment/mage_vl4b/M320_M120_TOKEN_ADAPTER_RESULT.json'
    m = args.checkpoint/'CHECKPOINT_MANIFEST.json'
    assert sha(m) == MANIFEST, 'checkpoint manifest hash'
    manifest = json.loads(m.read_text())
    assert manifest['blob']['sha256'] == BLOB, 'checkpoint declaration'
    assert (args.checkpoint/manifest['blob']['path']).stat().st_size == manifest['blob']['bytes']
    package = ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate'
    fixture = package/'fixtures/official_four_frame_processor.npz'
    pm = json.loads((package/'PACKAGE_MANIFEST.json').read_text())
    assert sha(fixture) == next(x['sha256'] for x in pm['files'] if x['path'] == 'fixtures/official_four_frame_processor.npz')
    assert (args.model/'config.json').is_file()
    if args.preflight_only:
        print('M320_IMPORT_PATH_AND_FIXTURE_PREFLIGHT_PASS', flush=True)
        print(Path('/proc/meminfo').read_text().splitlines()[:3], flush=True)
        return 0
    r = dict(gate='M320-M120-A8-offline-token-adapter', status='RUNNING',
             backend='WSL CPU M120 reconstructed BF16 weights with 253 language A8-G64 hooks',
             board_execution_run=False, semantic_accuracy_passed=False, records=[],
             sources={str(p.relative_to(ROOT)):sha(p) for p in
               [Path(__file__),ROOT/'bact/token_layout.py',ROOT/'bact/feature_budget.py',
                ROOT/'deployment/mage_vl4b/scripts/mage_a8_runtime.py',
                ROOT/'deployment/mage_vl4b/scripts/packed_checkpoint_artifact.py']},
             fixture_sha256=sha(fixture))
    save(outpath, r)
    phase = ['loading']
    done = threading.Event()
    start = time.monotonic()
    def heartbeat():
        while not done.wait(30):
            print(f'M320_HEARTBEAT phase={phase[0]} elapsed_s={time.monotonic()-start:.1f}', flush=True)
    threading.Thread(target=heartbeat, daemon=True).start()
    handles = []
    try:
        torch.set_num_threads(20)
        model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True,
            local_files_only=True, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True,
            attn_implementation='eager', device_map={'':'cpu'}).eval()
        tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True, local_files_only=True)
        phase[0] = 'M120 reconstruction'
        r['checkpoint'] = load_packed_checkpoint(torch, model, args.checkpoint, verify_blob=True, row_chunk=32)
        handles, names = install_packed_linear_a8_hooks(torch, model, args.checkpoint,
                                                      r'^(model\.language_model\.layers\.|lm_head$)')
        assert len(names) == 253
        r['a8_hook_count'] = len(names)
        r['torch_version'] = torch.__version__
        with np.load(fixture, allow_pickle=False) as f:
            inputs = {k:torch.from_numpy(f[k].copy()) for k in
                      ('input_ids','attention_mask','pixel_values','image_grid_thw','patch_positions')}
        captured = {}
        def capture(module, positional, kw):
            for k in ('inputs_embeds','attention_mask','position_ids'):
                captured[k] = kw[k].detach().clone()
        hook = model.language_model.register_forward_pre_hook(capture, with_kwargs=True)
        phase[0] = 'original full forward'
        with torch.inference_mode():
            original = model(**inputs, use_cache=True, output_hidden_states=True, logits_to_keep=1)
        hook.remove()
        ids = inputs['input_ids'].numpy()
        mask = inputs['attention_mask'].numpy()
        counts = (inputs['image_grid_thw'].prod(-1)//model.visual.spatial_merge_size**2).tolist()
        features = captured['inputs_embeds'][0,np.flatnonzero(ids[0]==model.config.image_token_id)].float().numpy()
        def adapt(keep):
            layout = select_layout(ids, mask, keep, image_token_id=model.config.image_token_id, frame_counts=counts)
            kw = {k:torch.from_numpy(getattr(layout,k)) for k in ('attention_mask','position_ids','cache_position')}
            kw['inputs_embeds'] = captured['inputs_embeds'][:,layout.sequence_indices]
            return layout, kw
        layout, kw = adapt(list(range(sum(counts))))
        for k in captured:
            assert torch.equal(captured[k],kw[k]), k
        phase[0] = 'full-keep equivalence'
        with torch.inference_mode():
            identity = model(**kw, use_cache=True, output_hidden_states=True, logits_to_keep=1)
        assert torch.equal(original.logits,identity.logits), 'identity logits'
        assert len(original.hidden_states)==len(identity.hidden_states)
        assert all(torch.equal(a,b) for a,b in zip(original.hidden_states,identity.hidden_states)), 'identity hidden states'
        eos = model.config.text_config.eos_token_id
        eos = {eos} if isinstance(eos,int) else set(eos)
        def decode(output,n,steps=12):
            tokens, scores, lengths = [], [], []
            with torch.inference_mode():
                for step in range(steps):
                    assert torch.isfinite(output.logits).all(), 'nonfinite output'
                    scores.append(output.logits[0,-1].float().clone())
                    token = output.logits[:,-1].argmax(-1).view(1,1)
                    tokens.append(int(token.item()))
                    lengths.append(output.past_key_values.get_seq_length())
                    assert lengths[-1] == n+step, 'KV length'
                    if step+1==steps or tokens[-1] in eos:
                        break
                    output = model(input_ids=token, past_key_values=output.past_key_values,
                        attention_mask=torch.ones(1,n+step+1,dtype=torch.long),
                        position_ids=torch.tensor([[n+step]]),cache_position=torch.tensor([n+step]),
                        use_cache=True,logits_to_keep=1)
            return tokens,scores,lengths
        baseline, scores, lengths = decode(original,ids.shape[1])
        same, other, same_lengths = decode(identity,ids.shape[1])
        assert baseline==same and lengths==same_lengths and all(torch.equal(a,b) for a,b in zip(scores,other))
        r['identity'] = dict(status='PASS_EXACT_SOFTWARE_REFERENCE', full_tokens=ids.shape[1],
            all_hidden_states_exact=True, logits_exact=True, decode_logits_exact=True,
            token_ids=baseline, kv_lengths=lengths, answer=tokenizer.decode(baseline,skip_special_tokens=True))
        save(outpath,r)
        print('M320_FULL_KEEP_EXACT_PASS', flush=True)
        del original,identity
        for fraction in (.75,.5):
            for method in ('uniform','content'):
                phase[0] = f'{method}-{fraction}'
                keep,offset = [],0
                for count in counts:
                    budget = int(np.ceil(count*fraction))
                    indices = (np.linspace(0,count-1,budget,dtype=np.int64).tolist() if method=='uniform' else
                               propose_budgets(features[offset:offset+count],np.zeros(count,dtype=np.int64),[budget],0)[0].indices)
                    keep.extend(offset+int(i) for i in indices)
                    offset += count
                layout,kw = adapt(keep)
                begin = time.monotonic()
                with torch.inference_mode():
                    output = model(**kw,use_cache=True,logits_to_keep=1)
                prefill_ms = (time.monotonic()-begin)*1000
                tokens,candidate_scores,kv = decode(output,len(layout.sequence_indices))
                delta = candidate_scores[0]-scores[0]
                r['records'].append(dict(method=method,fraction=fraction,total_tokens=len(layout.sequence_indices),
                    visual_indices=keep,software_language_prefill_ms=prefill_ms, token_ids=tokens,kv_lengths=kv,
                    answer=tokenizer.decode(tokens,skip_special_tokens=True),
                    logits_relative_l2=float(torch.linalg.vector_norm(delta)/torch.linalg.vector_norm(scores[0]))))
                save(outpath,r)
                print(f'M320_CANDIDATE_DONE {method} {fraction}',flush=True)
                del output
        r['status'] = 'PASS_M120_SOFTWARE_INTERFACE_NOT_BOARD_OR_SEMANTIC_ACCEPTANCE'
        r['limitations'] = ['One engineering fixture; no task accuracy claim',
            'BF16 reconstructed GEMM+A8 QDQ is not bit-exact PL integer-group accumulation',
            'Vision runtime differs from board M207 scheduling',
            'CPU timing is diagnostic, not paired CPU/FPGA benchmark',
            'No compression ratio promoted; up to 12 generated tokens may truncate']
        save(outpath,r)
        print(r['status'],flush=True)
    except Exception as exc:
        r.update(status='FAIL', error=f'{type(exc).__name__}: {exc}', phase=phase[0])
        save(outpath,r)
        raise
    finally:
        done.set()
        for handle in handles:
            handle.remove()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
