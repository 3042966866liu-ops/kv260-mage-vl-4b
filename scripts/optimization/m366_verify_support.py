"""Validate the fixed-text expansion, scope, budget and fail-closed control."""
import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import types
import numpy as np
import m351_workflow as w

PKG=w.BASE/'candidates/M366-staged-text-02'


def main():
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in manifest['files']}|{'PACKAGE_MANIFEST.json'}
    for row in manifest['files']:assert w.sha(PKG/row['path'])==row['sha256'] and (PKG/row['path']).stat().st_size==row['bytes']
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for module,tree in trees.items():
        for n in ast.walk(tree):
            names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else ([n.module.split('.')[0]] if isinstance(n,ast.ImportFrom) and n.module else [])
            missing.extend((module,name) for name in names if name not in trees and name not in allowed)
    assert not missing,missing
    hardware=json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    assert hardware['status']=='PASS_ALL_NEW_CIRCUIT_PREREQUISITES'
    for row in hardware['prerequisites']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    source=(PKG/'m366_staged_text_gate.py').read_text(encoding='utf-8')
    assert "BLOCKED_BOARD_METHODS = ()" in source and "for name in ('decode',)" in source
    assert "token,logits,kv=model.prefill(hidden.copy())" in source
    assert 'one_layer(' not in source and "vision.tower.forward" in source and "engine.stream = forbid" in source
    assert "runtime.maximum_weight_window_bytes!=6963200" in source and 'index>=7' in source
    assert source.index("policy.seal(")<source.index('recvchannel.transfer')<source.index('model.prefill(hidden.copy())')
    assert "logical_calls']!=162" in source and "len(families)!=154" in source and "len(kv.keys)!=36" in source
    expected=json.loads((PKG/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))
    contract=expected['input_contract']
    assert expected['prior_reference_raw_sha256']=='897bb817d6bd2a12f5de5437bb015541210f86c297c85456bc570586d479673a'
    with np.load(w.ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/auxiliary/m77_text_aux_fp16.npz',allow_pickle=False) as archive:
        rows=np.asarray(archive['model.language_model.embed_tokens.weight'],np.float32)
    hidden=np.stack([rows[contract['selected_embedding_ids'].index(t)] for t in contract['prompt_token_ids']])
    assert hidden.shape==(30,2560) and hashlib.sha256(hidden.tobytes()).hexdigest()==contract['input_tensor']['sha256']
    # Exact constants from the frozen model; do not infer heads from hidden width.
    constants=(release/closure['modules']['video_language_runtime']).read_text(encoding='utf-8')
    assert 'LAYERS, HIDDEN, HEADS, KV_HEADS, HEAD_DIM = 36, 2560, 32, 8, 128' in constants
    payload=dict(full36layer_KV=36*2*30*8*128*4,gate_up_two_arrays=2*30*9728*4,full_last_row_logits=151936*4,attention_two_score_matrices=2*(32//8)*30*30*4)
    spec=importlib.util.spec_from_file_location('m366_policy_test',PKG/'m366_stage_policy.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    assert len(p.FAMILIES)==154 and [(r['layer'],r['family']) for r in expected['baseline']['families']]==p.FAMILIES
    m={'system_bytes':{'CmaFree':17<<20,'MemAvailable':320<<20},'process_bytes':{'VmRSS':400<<20,'VmHWM':400<<20}}
    counts={'reserved:alloc_pages_success':0,'reserved:alloc_pages_fail':0}
    rt=types.SimpleNamespace(kernel=object(),dma=object())
    snap=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
    base=types.SimpleNamespace(transaction_snapshot=lambda *a:dict(snap));res={}
    policy=p.StagePolicy(res,lambda:rt,base,snapshot=lambda:m,counters=lambda:counts)
    policy.seal([types.SimpleNamespace(nbytes=n) for n in p.SHAPES],0x4d333537)
    assert policy.safe() and not p.assess(m,400<<20,counts,counts,sealed=True,buffer_bytes=p.SHAPES)['production_64mib_would_admit']
    snap.update(ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098)
    cases=[(0,'q'),(10,'qkv'),(35,'mlp_down'),(None,'lm_head')]
    for layer,family in cases:
        ch=dict(layer=layer,family=family,chain_index=0,input_bytes=1,output_bytes=1)
        assert policy.wrap_launch(lambda ch:'exact','fixture')(ch)=='exact' and policy.safe()
    rejected=[(36,'qkv'),(0,'qkv'),(10,'q'),(None,'q'),(0,'lm_head')]
    for layer,family in rejected:
        try:policy.wrap_launch(lambda ch:None,'fixture')(dict(layer=layer,family=family))
        except RuntimeError:pass
        else:raise AssertionError('Scope accepted invalid family')
    # Generate separate controllers/collectors; the immutable previous package is unchanged.
    control=(w.HERE/'m365_control.ps1').read_text(encoding='utf-8').replace('M365','M366').replace('m365','m366').replace('M366-staged-layer-03','M366-staged-text-02').replace('M366-staged-layer-support-02','M366-staged-text-support-02').replace('M366-staged-layer-transfer-02','M366-staged-text-transfer-01').replace('m366_staged_layer_candidate_02','m366_staged_text_candidate_02').replace('m36603','m366').replace('run_m366_staged_layer.sh','run_m366_staged_text.sh').replace('PASS_OFFLINE_INDEPENDENT_STAGE_RULES_AND_SUPPORT','PASS_OFFLINE_FIXED_TEXT_SCOPE_BUDGET_AND_SUPPORT')
    w.atomic(w.HERE/'m366_control.ps1',control.encode('utf-8'))
    collect=(w.HERE/'m365_collect.py').read_text(encoding='utf-8').replace('M365','M366').replace('m365','m366').replace('M366-staged-layer-03','M366-staged-text-02').replace('M366-staged-layer-board-01','M366-staged-text-board-01').replace('independent-single-layer-capacity-diagnostic','independent-fixed-text-capacity-diagnostic').replace('PASS_M366_SINGLE_LAYER_DIAGNOSTIC','PASS_M366_FIXED_TEXT_DIAGNOSTIC').replace('完整runtime对象保留，只layer0/159重复文本embedding，非视频','完整runtime对象保留，原30-token文本/36层/完整head，非视频').replace('固定文本需独立论证与新包','真实视频需独立论证与新包')
    w.atomic(w.HERE/'m366_collect.py',collect.encode('utf-8'))
    receipt=(w.HERE/'m365_transfer_receipt.py').read_text(encoding='utf-8').replace('M365','M366').replace('m365','m366').replace('m36603','m366').replace('M366-staged-layer-transfer-02','M366-staged-text-transfer-01').replace('只一次候选layer0诊断','只一次固定文本诊断').replace('单层','固定文本').replace('全部25载荷','全部载荷')
    w.atomic(w.HERE/'m366_transfer_receipt.py',receipt.encode('utf-8'))
    assert 'PASS_OFFLINE_FIXED_TEXT_SCOPE_BUDGET_AND_SUPPORT' in control
    assert (PKG/'m366_assemble.py').exists() and 'M366_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in (PKG/'m366_assemble.py').read_text(encoding='utf-8')
    assert (PKG/'run_m366_staged_text.sh').exists() and 'm366_staged_text_gate.py' in (PKG/'run_m366_staged_text.sh').read_text(encoding='utf-8')
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    r=subprocess.run([ps,'-NoProfile','-File',str(w.HERE/'m366_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert r.returncode==0 and 'M366_CONTROL_SELFTEST_PASS' in r.stdout,r.stdout+r.stderr
    c_spec=importlib.util.spec_from_file_location('m366_collect_test',w.HERE/'m366_collect.py');c=importlib.util.module_from_spec(c_spec);c_spec.loader.exec_module(c)
    # Exercise strict transport refusal with the previous real, complete raw result.
    oldlog=(w.ROOT/'tmp/m365/run.log').read_text(encoding='utf-8-sig')
    try:c.decode(oldlog)
    except ValueError:pass
    else:raise AssertionError('Previous gate accepted as new full text')
    out=w.BASE/'runs/M366-staged-text-support-02'
    rules='''# M366 固定文本独立容量诊断准入

前级M365完整对象保留+一层数值/释放已通过且三记录同步。生产64MiB规则不改。当前只原30-token文本、36层、151936 logits和72份KV，不执行视觉forward、decode、视频或性能。

七块原DMA缓冲真实分配后封锁额外PYNQ.allocate。显式新增专用CMA预算0；每个family/真实DMA提交及完成检查内存和CMA API计数，未知活动保留进程与缓冲。保持同Overlay合法最小事务和固定环境。普通PS仍使用256MiB增长监控预算+64MiB MemAvailable余量；这是有界实验停止规则，非原生库总峰值证明。

已从冻结源码确认36层KV=8847360B、单层gate/up两数组=2334720B、最后一行完整logits=607744B、一个KV组的两份scores/probability=28800B。这些是部分显式数组，不能相加称精确总峰值；还存在暂存、复制、索引、原生库及embedding mmap。准备结果初稿score组用了5而非冻结32/8=4，支持审计已纠正为28800B，门禁源码不受该账目影响。

154语言family按原顺序，8 head chains，共162逻辑及原3缩放重试参考（165物理）。全部family输入/输出、151936 logits及36K/36V、重试/权重字节/macros与既有稳定M344参考逐位SHA一致。输入严格绑定原30-token字节SHA。原数学与保护性重试保持。

20ms采样、逐提交/完成检查、全局CMA计数变化保守停止（不归因本进程）；full-text soft240s仅安全边界停止，每事务原10s。观察器停止、原pack/parse线程结束后原七缓冲逆序幂等各释放一次，稳定Overlay重载。不可证明活动完成时不得kill/free/reset。

通过只证明该独立固定文本路径在观测条件下运行。视频的视觉懒缓存、权重恢复、视觉输出和159-token KV必须另核算/冻结，不能从文本推断视频准入；不做完整请求性能宣称。
'''
    w.atomic(out/'RULES.md',rules.encode('utf-8'),immutable=True)
    result=dict(status='PASS_OFFLINE_FIXED_TEXT_SCOPE_BUDGET_AND_SUPPORT',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),scope_positive_checks=len(cases),scope_negative_checks=len(rejected),source_closure_missing=missing,python310_syntax=True,complete154family_sequence=True,input_sha_exact=True,same_sha_hardware_evidence=True,control_failure_collected=True,prior_raw_gate_rejected=True,runner_and_assembler_paths_verified=True,controller_support_status_verified=True,known_partial_payloads_bytes=payload,production_policy_changed=False,board_executed=False,performance_pass=False,rules_sha256=w.sha(out/'RULES.md'),rejected_offline_draft='01 support missed renamed assembler payload/controller status compatibility; never uploaded/run.02 fixes both and source-derived score budget.')
    w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m366_stage_support',dict(status=result['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,manifest_sha256=result['manifest_sha256']),f'## M366 固定文本独立规则支持\n\n前级M365一层PASS后仅准备原30-token/36层/head与72KV；7真实缓冲后封锁额外CMA，256MiB PS监控预算+64MiB余量，生产规则不改。已冻结原完整数值/154family/162逻辑参考、scope正负例/控制失败收集/Python3.10/递归missing=0及同SHA硬件证据。准备score组初算5已按32/8=4纠正，非总峰值认证。证据SHA `{digest}`。尚未上板，下一步仅新包逐SHA及一次固定文本诊断。')
    print(json.dumps(result))


if __name__=='__main__':main()
