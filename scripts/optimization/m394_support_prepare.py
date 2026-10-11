"""Prepare isolated video control and saved-only strict recovery support."""
from m351_workflow import HERE,atomic

def main():
    for src,dst in [('m393_control.ps1','m394_control.ps1'),('m393_workflow.py','m394_workflow.py')]:
        s=(HERE/src).read_text(encoding='utf-8-sig').replace('M393','M394').replace('m393','m394')
        s=s.replace('silu-text','silu-video').replace('silu_text','silu_video').replace('SILU_TEXT','SILU_VIDEO').replace('M386-ps-text-01','M387-ps-video-01')
        s=s.replace('捕获包传输核对','SiLU视频包传输核对').replace('一次独立layer0 SiLU数值门禁','一次原固定159视频SiLU数值门禁')
        atomic(HERE/dst,s.encode('utf-8'))
    s=(HERE/'m393_collect.py').read_text(encoding='utf-8').replace('M393','M394').replace('m393','m394')
    s=s.replace('fixed30 text / complete LM head','fixed159 video / complete LM head').replace('silu-text','silu-video').replace('silu_text','silu_video').replace('fixed-text-numerical','fixed159-video-numerical').replace('SILU_TEXT','SILU_VIDEO')
    s=s.replace("PRIOR='8eb467882777edd2ff8d9b11e6b02077a58b72f20a1d401478ac67502b35a63d'","PRIOR='5f304889c48969a259297b56dfc4d7e361f19ed434208b4e8ae8a154c33785b3'")
    s=s.replace('workspace_bytes=1167360','workspace_bytes=6187008').replace('silu_layer_prerequisite_sha256','silu_text_prerequisite_sha256').replace("'LAYER_EXPECTED.json'","'VIDEO_EXPECTED.json'").replace("r['layer_result']","r['video_result']").replace('256<<20','1024<<20')
    a=s.index("        if r['head_observer_proof']['original_module']");z=s.index("    elif r['gate_return_code']",a)
    s=s[:a]+'''        visual=json.loads((PKG/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))
        if r['vision_forward_calls']!=1 or not all(r['visual_exact_comparison'].values()) or r['visual_features']!=visual['visual_features'] or r['preprocessed']!=visual['preprocessed'] or r['prompt_token_ids']!=visual['prompt_token_ids']:raise ValueError('Visual identities differ')
        if r['same_loading_path_video_sha256']!='dbd3325e8152bf24402ce616b7fad4fe0584a4e7972aae573fb245a4eb52abaf':raise ValueError('Original video prerequisite differs')
        proof=r['head_observer_proof']
        if proof['original_module']!='m230_prefill_runtime' or proof['original_function']!='M230PrefillRuntime._execute' or not proof['removed_observation_calls_ast_equals_original'] or proof['inserted_observation_calls']!=2 or not proof['every_retry_physical_boundary'] or proof['exact_frozen_head_chains']!=8 or len([t for t in r['transactions'] if t['method']=='head-original-execute'])!=8:raise ValueError('Physical head coverage differs')
        from m368_video_contract import validate_stream
        try:semantic=validate_stream(r['events'],r['decoder'],r['build_id'])
        except RuntimeError as e:raise ValueError(str(e)) from e
        if semantic!=r['candidate_semantic']:raise ValueError('Actual stream semantic differs')
        normalized=dict(semantic,proof=dict(semantic['proof'],build_id=expected['semantic']['proof']['build_id']))
        if normalized!=expected['semantic']:raise ValueError('Original constrained decision differs')
''' +s[z:]
    a=s.index("         f'## M394");z=s.index("    print(",a)
    s=s[:a]+'''         f'## M394 SiLU固定159视频板端结果（2026-10-04）\\n\\nBuild0x4D333537，原rc{r["gate_return_code"]}，{r["status"]}，原SHA {d}。原视觉/159Token/36层/完整head/logits/72KV/778逻辑及物理重试、36次SiLU scope/owner/绑定/七DMA释放和稳定恢复核对。PS预读与双parser关闭，0新DMA，1GiB普通预算/64MiB普通余量，生产准入不改。仅视频数值和生命周期；下一步独立闭合后轻量交错整体请求性能。')
''' +s[z:]
    atomic(HERE/'m394_collect.py',s.encode('utf-8'))
    print('M394_SUPPORT_DRAFT_READY')

if __name__=='__main__':main()
