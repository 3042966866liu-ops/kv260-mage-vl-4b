"""Full Mage-VL offline interface gate, then exploratory visual-token pruning.

NF4 CUDA is an interface test backend, NOT the M120 board quantization or a
quality reference. No held-out annotations, network, or board access.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import numpy as np
import torch
from transformers import AutoModelForCausalLM, BitsAndBytesConfig, AutoTokenizer
from bact.token_layout import select_layout
from bact.feature_budget import propose_budgets


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temp = path.with_suffix('.partial.json')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--model', type=Path, required=True)
    args = ap.parse_args()
    root = args.workspace
    destination = root / 'deployment/mage_vl4b/M319_TOKEN_ADAPTER_GPU_RESULT.json'
    result = dict(gate='M319-full-model-token-interface', status='RUNNING',
                  backend='local WSL CUDA NF4 weights / BF16 compute; NOT board M120',
                  board_modified=False, semantic_accuracy_passed=False,
                  position_policy='compact language 1D positions; visual 3D positions unchanged before merger',
                  source_sha256=digest(Path(__file__)), records=[])
    save(destination, result)
    try:
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA required; no silent CPU fallback')
        package = root / 'deployment/mage_vl4b/m181_m120_video_board_candidate'
        fixture = package / 'fixtures/official_four_frame_processor.npz'
        manifest = json.loads((package / 'PACKAGE_MANIFEST.json').read_text())
        entry = next(x for x in manifest['files'] if x['path'] == 'fixtures/official_four_frame_processor.npz')
        if digest(fixture) != entry['sha256']:
            raise RuntimeError('fixture identity mismatch')
        result['fixture_sha256'] = digest(fixture)
        result['model_config_sha256'] = digest(args.model / 'config.json')
        result['model_code_sha256'] = digest(args.model / 'modeling_mage_vl.py')
        print('M319_FIXTURE_AND_CUDA_PASS', flush=True)
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                  bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
        model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True,
                local_files_only=True, quantization_config=quant, device_map='auto',
                low_cpu_mem_usage=True).eval()
        tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True, local_files_only=True)
        result['parameter_devices'] = sorted({str(p.device) for p in model.parameters()})
        result['linear4bit_modules'] = sum(type(m).__name__ == 'Linear4bit' for m in model.modules())
        if not result['linear4bit_modules']:
            raise RuntimeError('NF4 quantization not active')
        if any(not v.startswith('cuda') for v in result['parameter_devices']):
            raise RuntimeError('CPU/disk offload: do not report as CUDA-only comparison')
        f = np.load(fixture, allow_pickle=False)
        inputs = {k: torch.from_numpy(f[k]).to('cuda') for k in
                  ('input_ids', 'attention_mask', 'pixel_values', 'image_grid_thw', 'patch_positions')}
        counts = (inputs['image_grid_thw'].prod(-1) // model.visual.spatial_merge_size**2).cpu().tolist()
        captured = {}

        def capture(module, positional, kwargs):
            for k in ('inputs_embeds', 'attention_mask', 'position_ids'):
                captured[k] = kwargs[k].detach().clone()

        hook = model.language_model.register_forward_pre_hook(capture, with_kwargs=True)
        with torch.inference_mode():
            original = model(**inputs, use_cache=True, output_hidden_states=True, logits_to_keep=1)
        hook.remove()
        full_ids = inputs['input_ids'].cpu().numpy()
        mask = inputs['attention_mask'].cpu().numpy()
        visual_positions = np.flatnonzero(full_ids[0] == model.config.image_token_id)
        features = captured['inputs_embeds'][0, visual_positions].float().cpu().numpy()

        def adapted(keep):
            layout = select_layout(full_ids, mask, keep, image_token_id=model.config.image_token_id,
                                   frame_counts=counts)
            tensors = {k: torch.from_numpy(getattr(layout, k)).to('cuda')
                       for k in ('attention_mask', 'position_ids', 'cache_position')}
            idx = torch.from_numpy(layout.sequence_indices).to('cuda')
            tensors['inputs_embeds'] = captured['inputs_embeds'].index_select(1, idx)
            return layout, tensors

        layout, tensors = adapted(list(range(sum(counts))))
        for k in ('inputs_embeds', 'attention_mask', 'position_ids'):
            if not torch.equal(tensors[k], captured[k]):
                raise RuntimeError('full-keep input mismatch: ' + k)
        with torch.inference_mode():
            identity = model(**tensors, use_cache=True, output_hidden_states=True, logits_to_keep=1)
        if not torch.equal(original.logits, identity.logits):
            raise RuntimeError('full-keep last-position full-vocabulary logits mismatch')
        if len(original.hidden_states) != len(identity.hidden_states) or not all(torch.equal(a, b) for a, b in zip(original.hidden_states, identity.hidden_states)):
            raise RuntimeError('full-keep hidden-state mismatch')

        def decode(output, n, steps=12):
            tokens, scores, lengths = [], [], []
            with torch.inference_mode():
                for step in range(steps):
                    scores.append(output.logits[:, -1].detach().float().cpu())
                    token = output.logits[:, -1].argmax(-1).reshape(1, 1)
                    tokens.append(int(token.item()))
                    length = output.past_key_values.get_seq_length()
                    lengths.append(length)
                    if length != n + step:
                        raise RuntimeError('KV length mismatch')
                    if step + 1 == steps or int(token.item()) == model.config.text_config.eos_token_id:
                        break
                    output = model(input_ids=token, past_key_values=output.past_key_values,
                        attention_mask=torch.ones((1, n+step+1), dtype=torch.long, device='cuda'),
                        position_ids=torch.tensor([[n+step]], device='cuda'),
                        cache_position=torch.tensor([n+step], device='cuda'), use_cache=True, logits_to_keep=1)
            return tokens, scores, lengths

        baseline, baseline_scores, original_lengths = decode(original, len(layout.sequence_indices))
        same, same_scores, same_lengths = decode(identity, len(layout.sequence_indices))
        if same != baseline or same_lengths != original_lengths or not all(torch.equal(a,b) for a,b in zip(baseline_scores, same_scores)):
            raise RuntimeError('full-keep decode/KV mismatch')
        result['identity'] = dict(status='PASS_EXACT', all_layer_hidden_states_exact=True,
            last_position_full_vocabulary_logits_exact=True, decode_logits_exact=True,
            token_ids=baseline, kv_lengths=original_lengths, full_tokens=int(full_ids.shape[1]),
            visual_tokens=sum(counts), text_and_special_tokens=int(full_ids.shape[1]-sum(counts)),
            answer=tokenizer.decode(baseline, skip_special_tokens=True))
        del original, identity
        print('M319_FULL_KEEP_EXACT_PASS', flush=True)
        save(destination, result)
        for fraction in (0.75, 0.5, 0.25):
            for method in ('uniform', 'content'):
                keep, offset = [], 0
                per_frame = []
                for count in counts:
                    budget = max(1, int(np.ceil(count * fraction)))
                    per_frame.append(budget)
                    if method == 'uniform':
                        indices = np.linspace(0, count-1, budget, dtype=np.int64).tolist()
                    else:
                        indices = list(propose_budgets(features[offset:offset+count],
                           np.zeros(count, dtype=np.int64), [budget], 0)[0].indices)
                    keep.extend(offset+i for i in indices)
                    offset += count
                layout, tensors = adapted(keep)
                torch.cuda.synchronize()
                begin = time.perf_counter()
                with torch.inference_mode():
                    output = model(**tensors, use_cache=True, logits_to_keep=1)
                torch.cuda.synchronize()
                prefill_ms = (time.perf_counter()-begin)*1000
                if not torch.isfinite(output.logits).all():
                    raise RuntimeError('nonfinite candidate logits')
                logits = output.logits[0,-1].float().cpu()
                ref = baseline_scores[0][0]
                generated, _, lengths = decode(output, len(layout.sequence_indices))
                result['records'].append(dict(method=method, fraction=fraction, per_frame=per_frame,
                    visual_indices=keep, total_tokens=len(layout.sequence_indices),
                    t32_batches=(len(layout.sequence_indices)+31)//32,
                    gpu_language_prefill_ms=prefill_ms, token_ids=generated, kv_lengths=lengths,
                    answer=tokenizer.decode(generated, skip_special_tokens=True),
                    first_token_same=generated[0]==baseline[0],
                    logits_relative_l2=float(torch.linalg.vector_norm(logits-ref)/torch.linalg.vector_norm(ref)),
                    logits_cosine=float(torch.nn.functional.cosine_similarity(logits[None],ref[None]).item())))
                save(destination, result)
                print(f'M319_CANDIDATE_DONE method={method} fraction={fraction} tokens={len(layout.sequence_indices)}', flush=True)
                del output
        result['status'] = 'PASS_INTERFACE_AND_EXPLORATORY_FORWARDS_NOT_QUALITY'
        result['limitations'] = ['one engineering fixture; no task-accuracy evidence',
            'NF4 GPU differs from deployed mixed W2/W4+A8',
            'post-merger pruning does not reduce vision-tower work',
            'single timing per candidate, no board speedup claim',
            '12-token greedy continuation may be truncated; no accuracy conclusion']
        save(destination, result)
        print(result['status'], flush=True)
        return 0
    except Exception as exc:
        result['status'] = 'FAIL'
        result['error'] = f'{type(exc).__name__}: {exc}'
        save(destination, result)
        raise


if __name__ == '__main__':
    raise SystemExit(main())
