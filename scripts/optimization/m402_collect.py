"""Strict saved-only fixed159 candidate collector. Never executes a gate."""
import ast
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,sync
PKG=BASE/'candidates/M402-tail-video-01'
OUT=BASE/'runs/M402-tail-video-board-01/BOARD_RESULT.json'
KEY='latest_m402_tail_video_board'

def original_decoder():
    p=HERE/'m398_collect.py'
    # Original source is frozen independently of generated code formatting.
    if sha(p)!='0c437d7c3af58dfbe9a890f37b49f25a7c73aa970efa80c4a931bff328db3891':
        raise RuntimeError('Original video decoder SHA drift')
    s=p.read_text(encoding='utf-8').replace('M398','M402').replace('M402-tail-reference-01','M402-tail-video-01')
    s=s.replace('sealed-DMA-original-fixed159-tail-reference','sealed-DMA-fixed159-full36-layer-tail-prefill').replace('PASS_M402_ORIGINAL_TAIL_REFERENCE','PASS_M402_TAIL_VIDEO_NUMERICAL')
    lines=s.splitlines(True)
    # Capture-only acceptance is replaced by strict candidate scope checks below.
    lines=[line for line in lines if "r['tail_capture_prerequisite_sha256']" not in line and '        validate_capture(r,expected)' not in line]
    s=''.join(lines).replace('from m368_video_contract import validate_stream','from m402_video_contract import validate_stream')
    t=ast.parse(s);t.body=[n for n in t.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.Assign)) or isinstance(n,ast.FunctionDef) and n.name=='decode']
    import importlib.util
    spec=importlib.util.spec_from_file_location('m402_video_contract',PKG/'m402_video_contract.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    import sys
    sys.modules['m402_video_contract']=module
    ns={};exec(compile(t,'<frozen-video-decoder-with-explicit-tail-scope>','exec'),ns)
    return ns['decode']

BASE_DECODE=original_decoder()

def decode(text):
    digest,raw,r=BASE_DECODE(text)
    source_proof=json.loads((BASE/'runs/M401-tail-text-board-02/BOARD_RESULT.json').read_bytes())['source_precheck_before_hardware_import']
    if r.get('source_precheck_before_hardware_import')!=source_proof:raise ValueError('Pre-resource full Prefill source proof differs')
    if r['status']=='PASS_M402_TAIL_VIDEO_NUMERICAL':
        from m402_count_scope import SOURCE_SHA
        count_proof=dict(original_source_sha256=SOURCE_SHA,original159_calls=778,original30_calls=162,code_equal=True)
        wanted_count=dict(proof=count_proof,accepted_calls=1,original_expected=778,candidate_expected=766,closed=True,binding_restored=True,board_evidence_changed=False)
        wanted_scope=dict(plan=dict(tokens=159,tail_start=128,tail_count=31,original_logical=778,logical=766),selected=[dict(layer=35,original_token_start=128,local_token_start=0,token_count=31,original_dma_slot=0,candidate_dma_slot=0)],invoked=True,closed=True,retained=False,binding_callback_removed=True,extra_dma_allocations=0,ps_prefetch=False,parser_workers=1,silu_workspace=False)
        if r.get('tail_scope')!=wanted_scope or r.get('count_scope')!=wanted_count or r.get('count_source_precheck')!=count_proof:raise ValueError('Tail/count ownership contract differs')
        if not all(r.get(k) is True for k in ('scope_weakref_dead','count_scope_weakref_dead','tail_candidate_executed','candidate_numerical_pass','candidate_full_model_executed')):raise ValueError('Candidate completion missing')
        if r['ps_prefetch_enabled'] or r['worker_started'] or r['silu_workspace_enabled'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1:raise ValueError('Other optimization enabled')
        pins=dict(text_prerequisite_sha256='e4ffe98c1deed4863701a783a90f2b1272cbbd7eb71136f37e0a38238d52da85',text_closure_sha256='0e3e6e2241fec9fb520f2334a84006b11991f052d58165f28c367506c25b914b',layer_prerequisite_sha256='bca7bf2b4c6de4a4e861448162ce9a97da32e82fd68bf7af0dcf9c8eedde089c',layer_closure_sha256='64acc9f2174e95c241b26f91cb328f732105d766751c0092d0ce0c8a3d608043',original_reference_sha256='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef')
        if any(r.get(k)!=v for k,v in pins.items()):raise ValueError('Prior gate closure identity differs')
        expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_bytes())
        if r['transactions']!=expected['transactions']:raise ValueError('All retained physical transaction identities differ')
        if (r['logical_calls'],r['host_calls'],r['fpga_transactions'])!=(766,767,768):raise ValueError('Actual candidate counters differ')
        if len(r['video_result']['families'])!=154 or len(r['video_result']['keys'])!=36 or len(r['video_result']['values'])!=36:raise ValueError('Full model outputs incomplete')
    return digest,raw,r

def collect(path):
    digest,raw,r=decode(path.read_text(encoding='utf-8-sig'))
    atomic(OUT,raw,immutable=True)
    passed=r['status']=='PASS_M402_TAIL_VIDEO_NUMERICAL'
    sync(KEY,dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,candidate_numerical_pass=passed,performance_pass=False,formal_promotion_allowed=False),f'## M402 末层候选固定159视频结果（2026-10-04）\n\nBuild0x4D333537，原rc{r["gate_return_code"]}，raw `{digest}`，{r["status"]}。原同输入完整视觉/154family/72KV/151936logits/判断和全部物理身份严格核对；候选合同766逻辑/保留一次重试767模型物理加minimal768。新增DMA0，双scope退出及七DMA/稳定恢复核对。数值PASS={passed}；尚无此裁剪候选性能或晋级，失败只本级debug或回收原字节。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],fpga_transactions=r['fpga_transactions'])))
