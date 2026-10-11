"""Strict saved-byte fixed30 candidate collection; no hardware execution."""
import importlib.util
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,sync
PKG=BASE/'candidates/M401-tail-text-02'
PROOF=json.loads((BASE/'runs/M401-tail-text-draft-01/RESULT.json').read_text(encoding='utf-8'))['source_precheck']

def base_decoder():
    if sha(HERE/'m36603_collect.py')!='800c6cbee8ec9694da90bd35404d3c854cfe5396d00f6224888786f6c5eb0331':raise RuntimeError('Original strict text decoder source drift')
    text=(HERE/'m36603_collect.py').read_text(encoding='utf-8').replace('M366','M401').replace('M366-staged-text-03','M401-tail-text-02')
    text=text.replace("PKG=w.BASE/'candidates/M401-staged-text-03'","PKG=w.BASE/'candidates/M401-tail-text-02'").replace('independent-fixed-text-capacity-diagnostic','sealed-DMA-fixed30-full36-layer-tail-prefill').replace('PASS_M401_FIXED_TEXT_DIAGNOSTIC','PASS_M401_TAIL_TEXT_NUMERICAL')
    # Compile only decoder and its original imports; exclude dispatch/synchronization.
    import ast
    tree=ast.parse(text);tree.body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.Assign) or isinstance(n,ast.FunctionDef) and n.name=='decode']
    namespace={};exec(compile(tree,'<m401-reused-strict-fixed-text-decoder>','exec'),namespace)
    return namespace['decode']

BASE_DECODE=base_decoder()

def decode(text):
    digest,raw,r=BASE_DECODE(text)
    if type(r['gate_return_code']) is not int:raise ValueError('Original gate rc must be an integer')
    if r.get('source_precheck_before_hardware_import')!=PROOF:raise ValueError('Pre-resource full Prefill source proof differs')
    if r['status']=='PASS_M401_TAIL_TEXT_NUMERICAL':
        if r['layer_prerequisite_sha256']!='bca7bf2b4c6de4a4e861448162ce9a97da32e82fd68bf7af0dcf9c8eedde089c' or r['layer_closure_sha256']!='64acc9f2174e95c241b26f91cb328f732105d766751c0092d0ce0c8a3d608043':raise ValueError('Single layer prerequisite differs')
        if r.get('vision_forward_calls',0):raise ValueError('Fixed text escaped to visual forward')
        expected_scope=dict(plan=dict(tokens=30,tail_start=0,tail_count=30,original_logical=162,logical=162),
                            selected=[dict(layer=35,original_token_start=0,local_token_start=0,token_count=30,original_dma_slot=0,candidate_dma_slot=0)],
                            invoked=True,closed=True,retained=False,binding_callback_removed=True,extra_dma_allocations=0,ps_prefetch=False,parser_workers=1,silu_workspace=False)
        if r['tail_scope']!=expected_scope or not r['scope_weakref_dead']:raise ValueError('Complete Prefill owner/boundary closure differs')
        if not r['candidate_full_model_executed'] or r['extra_pynq_allocations'] or r['ps_prefetch_enabled'] or r['silu_workspace_enabled'] or r['original_parser_workers']!=1:raise ValueError('Unexpected full text variant')
        if r['original_buffer_release_count']!=7 or not r['patch_registry_cleared'] or r['stable_bit_sha256']!='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac':raise ValueError('Owned release/stable identity differs')
        prior=BASE/'runs/M366-staged-text-board-02/BOARD_RESULT.json'
        if sha(prior)!='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb':raise ValueError('Frozen full text reference differs')
        gold=json.loads(prior.read_text(encoding='utf-8'))
        if r['transactions']!=gold['transactions']:raise ValueError('All physical DMA identities differ')
        if r['logical_calls']!=162 or r['host_calls']!=165 or r['fpga_transactions']!=166 or r['layer_result']['retry_count']!=3:raise ValueError('Complete text/retry count differs')
        if r['diagnostic_ps_growth_limit_bytes']!=1024<<20 or r['diagnostic_ps_available_margin_bytes']!=64<<20 or r['additional_cma_requests_allowed']:raise ValueError('Sealed diagnostic policy changed')
        counts=r['stage_memory'][0]['cma_counts']
        for p in r['stage_memory']:
            d=p['admission']
            if d is None:continue
            if p['cma_counts']!=counts or not 0<=d['observed_rss_growth_bytes']<=1024<<20 or d['diagnostic_additional_explicit_cma_bytes'] or d['required_mem_available_bytes']!=(1024<<20)-d['observed_rss_growth_bytes']+(64<<20) or d['mem_available_bytes']<d['required_mem_available_bytes']:raise ValueError('Memory admission/counter mismatch')
    return digest,raw,r

def collect(path):
    digest,raw,r=decode(path.read_text(encoding='utf-8-sig'))
    out=BASE/'runs/M401-tail-text-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    passed=r['status']=='PASS_M401_TAIL_TEXT_NUMERICAL'
    sync('latest_m401_tail_text_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,fixed_text_numerical_pass=passed,performance_pass=False,formal_promotion_allowed=False),
         f'## M401 末层候选完整固定文本结果（2026-10-04）\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，raw `{digest}`，{r["status"]}。只固定30文本36层/head；完整154family/151936logits/72KV和原3重试、全部165物理身份严格核对，新增DMA0。源码检查先于硬件导入/分配、原生产政策保持；成功关闭原七DMA/owner并恢复稳定。PASS={passed}，尚无候选159视频或新性能；失败停固定文本级，只回收原字节。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],physical_calls=r['fpga_transactions'])))
