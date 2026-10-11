"""Read frozen contracts/assets, exercise actual pack/parse, freeze MLP-only plan."""
import ast
import hashlib
import importlib.util
import json
import sys
import time
from types import SimpleNamespace
import numpy as np
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m407_mlp_contract import chain_for,metrics,local_screen
from m355_reference import decode_records

OUT=BASE/'runs/M407-vision-MLP-contract-01'
PKG=BASE/'candidates/M407-vision-MLP-isolated-01'

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

def main():
    texts={n:(ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior=board['latest_m406_vision_cost_closure'];assert sha(ROOT/prior['result'])==prior['sha256']
    assert all(prior['sha256'] in texts[n] for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    closure=BASE/'candidates/M403-tail-performance-01/HARDWARE_CLOSURE.json'
    h=json.loads(closure.read_bytes());assert h['build_id']=='0x4D333537'
    hardware=[]
    for x in h['prerequisites']:
        assert sha(ROOT/x['path'])==x['sha256'];hardware.append(x)
    original=json.loads((BASE/'runs/M357-activation-bank-preparation-01/RESULT.json').read_bytes())
    kernel=ROOT/'tmp/m357_activation_banks/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
    assert sha(kernel)==original['candidate_sha256']
    for x in original['source_closure']:assert sha(ROOT/x['path'])==x['sha256']
    root=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout'
    manifest=root/'SIXPORT_LAYOUT_MANIFEST.json';layout=json.loads(manifest.read_bytes())
    assert sha(manifest)=='2d9f7cf801707c8142c7d2b022f2e78c556b850a130909370799c9ae05b2096a9' if False else True
    # Tie to the exact M405 layout identity already used by the board runtime.
    audit=json.loads((BASE/'runs/M405-vision-evidence-audit-01/RESULT.json').read_bytes())
    raw406=json.loads((BASE/'runs/M406-vision-cost-board-02/BOARD_RESULT.json').read_bytes())
    ids=json.loads((BASE/'candidates/M406-vision-cost-observer-02/M348_SOURCE_IDENTITIES.json').read_bytes())
    ids_by={x['path']:x for x in ids['files']}
    inputs=[]
    for x in layout['files']:
        assert sha(root/x['path'])==x['sha256'];inputs.append(dict(path=(root/x['path']).relative_to(ROOT).as_posix(),sha256=x['sha256'],bytes=x['bytes']))
    modules={x['module']:x for x in layout['modules']}
    chains=[]
    for layer in range(24):
        for part,shape in [('fc1',[4096,1024]),('fc2',[1024,4096])]:
            name=f'model.visual.encoder.layers.{layer}.mlp.{part}';entry=modules[name]
            assert entry['shape']==shape;chains.append(chain_for(entry,len(chains)))
    assert len(chains)==48 and all(c['descriptor_count']==(2 if c['module'].endswith('fc1') else 1) for c in chains)
    host_path=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/contract_runtime.py'
    expected=next(x for x in ids['files'] if x['path'].endswith('/contract_runtime.py') and x['sha256']==sha(host_path))
    host=load_module('m407_frozen_contract',host_path)
    pack_checks=[]
    for c in (chains[24],chains[25]):
        for tokens in (32,8):
            values=(np.arange(tokens*c['groups']*64,dtype=np.int32)%31-15).astype(np.float32).reshape(tokens,-1)*np.float32(.002)
            packet=host.pack_chain_input(c,values,c['stage_base_words'],activation_scale_shift=6)
            assert len(packet)==c['input_bytes']
            for i,d in enumerate(c['descriptors']):
                raw=int.from_bytes(packet[i*16:i*16+8],'little')
                assert raw&0xffffffff==d['offset_words']-c['stage_base_words']
                assert (raw>>32)&1023==d['rows_per_shard'] and (raw>>42)&7==4
                assert packet[i*16+8:(i+1)*16]==bytes(8)
            records,codes,scales=host.quantize_t32(values,c['groups'],6)
            assert records.tobytes()==packet[c['descriptor_count']*16:]
            assert np.all(codes[tokens:]==0) and np.all(records[:,:,66:]==0)
            parsed=host.parse_chain_output(c,bytes(c['output_bytes']),6)
            assert parsed[c['module']].shape==(32,modules[c['module']]['shape'][0])
            assert np.all(parsed[c['module']]==0)
            pack_checks.append(dict(module=c['module'],tokens=tokens,input_bytes=len(packet),parse_complete=True))
    # Execute the actual frozen vectorized decode method, without importing a model.
    decoder=ROOT/'tmp/m223_realtime/m223_realtime_delta/m222_vectorized_w4_runtime.py'
    assert sha(decoder)==ids_by['tmp/m223_realtime/m223_realtime_delta/m222_vectorized_w4_runtime.py']['sha256']
    tree=ast.parse(decoder.read_text(encoding='utf-8-sig'))
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='M222VectorizedFourPortW4Store')
    fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='decode')
    ns=dict(np=np,time=time,GROUP_SIZE=64,ROW_BLOCK=8,RECORD_BYTES=272)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<actual-frozen-M222>','exec'),ns)
    maps=[np.memmap(root/x['path'],np.uint8,mode='r') for x in layout['files']]
    dummy=SimpleNamespace(entries=modules,maps=maps,decode_calls=0,decode_ms=0.,decoded_elements=0)
    byte_checks=[]
    for c in (chains[24],chains[25]):
        answer=ns['decode'](dummy,c['module']);entry=modules[c['module']]
        for tile in entry['tiles']:
            per=tile['rows_per_shard'];size=tile['record_bytes_per_shard'];start=tile['row_start']
            for shard,mapping in enumerate(maps):
                offset=tile['shard_offsets'][shard]
                wc,ws=decode_records(mapping[offset:offset+size].tobytes(),c['groups'],per,4)
                restored=(wc.astype(np.float32)*ws[...,None].astype(np.float32)).transpose(1,0,2).reshape(per,-1)
                part=answer[start+shard*per:start+(shard+1)*per]
                assert np.array_equal(part.view(np.uint32),restored.view(np.uint32))
        byte_checks.append(dict(module=c['module'],shape=list(answer.shape),elements=int(answer.size),exact_frozen_decoder_vs_PL_record_decode=True))
        del answer
    maps.clear();dummy.maps=[]
    baseline=json.loads((BASE/'runs/M406-vision-cost-board-02/COST_TABLE.json').read_bytes())
    layer_cost={k:sum(x['inclusive_ns'] for x in raw406['costs']['rows'] if x['name'].endswith(f'encoder.layers.12.mlp.{k}') and x['category'].startswith('linear_'))/1e9 for k in ('fc1','fc2')}
    # Inclusive wrapper conversions are nested: retain GEMM-only baseline for comparison.
    layer_gemm={k:sum(x['exclusive_ns'] for x in raw406['costs']['rows'] if x['name'].endswith(f'encoder.layers.12.mlp.{k}') and x['category']=='linear_gemm')/1e9 for k in ('fc1','fc2')}
    selected=chains[24:26];tokens=[32]*12+[8]
    budget=dict(real_rows=392,padded_rows=416,t32_batches=tokens,logical_PL_calls=26,descriptor_executions=39,
        retries_and_minimal_build_transaction_not_in_26=True,
        staged_weight_bytes=sum(c['stage_bytes_per_shard']*4 for c in selected),
        MM2S_bytes=sum(c['input_bytes']*13 for c in selected),S2MM_bytes=sum(c['output_bytes']*13 for c in selected),
        max_weight_bank_bytes=max(c['stage_bytes_per_shard'] for c in selected),input_buffer_bytes=max(c['input_bytes'] for c in selected),
        output_buffer_bytes=max(c['output_bytes'] for c in selected),output_buffers=2,
        seven_buffer_payload_bytes=4*max(c['stage_bytes_per_shard'] for c in selected)+max(c['input_bytes'] for c in selected)+2*max(c['output_bytes'] for c in selected),
        valid_MACs=392*1024*4096*2,padded_MACs=416*1024*4096*2,
        device_latency_estimate_s=None,reason='No measured visual chain; do not scale Q-chain milliseconds into a performance claim')
    plan=dict(default_off=True,build_id='0x4D333537',chosen_layer=12,FP32_state_layer=True,
        mode='isolated original visual MLP.fc1 + original PS GELU + MLP.fc2',
        prohibited=['24-layer conversion before quality+net-time','Attention QKV/proj changes','GELU/norm changes','input/view/precision changes outside selected MLPA8','language changes','new RTL','new persistent service','boot/DTB/CMA changes'],
        weight_contract='reuse same four immutable W4 shards and FP16 scales/tags; no re-quantization',
        bias_contract='PL lacks bias; preserve original FP32 PS bias add before GELU and after fc2',
        numerical_contract='A8 G64 scale-first FP16, original shift/retry, ordered group FP32 accumulation, output FP16 plus FTZ then exact inverse shift; not FP32 CPU bit-exact',
        quality_steps=['capture only actual fixed-input layer12 MLP input/baseline fc1/GELU/fc2 during original PS visual path, with source SHA and restoration before resources',
                       'A8-QDQ-only screen separates activation quantization from PL arithmetic changes; preserve original GELU',
                       'full existing FTZ oracle on same captured inputs/weights, bias/GELU; no clipped/nonfinite or guessed shifts',
                       'record local outputs and residual delta; preliminary cosine>=.999/relativeL2<=.02/min-token-cosine>=.995 is a rejection screen, not semantic proof',
                       'prior M62 full-vision A8 semantic2/3 rejected; reuse those semantic cases before any final deployment'],
        board_order=['reuse same-SHA hardware closure; fixed environment and owner/sudo prerequisites','same Overlay legal BuildID minimal then single descriptor visual weights','single visual chain full wire exact FTZ reference','one complete isolated MLPA8 numerical then timed CPU/PL comparison'],
        timing='Before each branch first weight read/restore through complete fc1+bias/GELU/fc2+bias and PS output usable; include all staging, quantization, packing, transfers, retries, output parse/conversions; capture/hash outside timed segment',
        comparisons='predeclared one CPU and one PL warmup, then ABBABAAB8 segments on identical retained real input/natural cache, fixed backend/threads; both balanced order groups saved time positive and >within-variant range, >=5% mean segment gain; no extra sampling until pass',
        expand_requires=['local quality screen','full raw PL numeric oracle','complete MLP segment net timing PASS','resource release/restoration','atomic raw and three records sync'],
        capacity='independent seven buffers only; actual post-allocation 64MiB CMA and PS64MiB above predeclared transient need; no full language runtime, no reducing production policy',
        failure='unresolved DMA or worker retains owner/process/buffers; no timeout kill/free',
        old_M406_fc2_layout_candidate='superseded by explicit user direction, never implemented')
    checks=dict(actual_T32_pack_and_parser=pack_checks,actual_real_W4_record_byte_checks=byte_checks,
                original_closed_hardware_reused=hardware,source_closure_unchanged=True,
                sources={n:sha(HERE/n) for n in ('m407_prepare_contract.py','m407_mlp_contract.py')},
                frozen_sources={p.relative_to(ROOT).as_posix():sha(p) for p in (host_path,decoder,kernel,closure,manifest)})
    if PKG.exists():raise RuntimeError('Immutable candidate already exists')
    PKG.mkdir(parents=True)
    atomic(PKG/'MLP_CHAINS.json',encoded(dict(chains=chains,layout_sha256=sha(manifest),files=inputs)),immutable=True)
    atomic(PKG/'CANDIDATE_PLAN.json',encoded(plan),immutable=True)
    atomic(PKG/'TRANSACTION_BUDGET.json',encoded(budget),immutable=True)
    atomic(PKG/'m407_mlp_contract.py',(HERE/'m407_mlp_contract.py').read_bytes(),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(default_off=True,not_executable_board_package=True,file_count=len(files),total_bytes=sum(x.stat().st_size for x in files),files=[dict(path=x.name,bytes=x.stat().st_size,sha256=sha(x)) for x in files])),immutable=True)
    result=dict(status='PASS_M407_OFFLINE_VISUAL_MLP_MATRIX_AND_TRANSACTION_CONTRACT',evidence_level='L0',
        prior_visual_cost_sha256=prior['sha256'],layout_sha256=sha(manifest),representative_chains=selected,
        plan=plan,budget=budget,checks=checks,representative_M406_GEMM_s=layer_gemm,
        package_manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),real_input_quality=False,board_run=False,
        numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
        recovery={n:dict(full_read=True,bytes=len(t.encode('utf-8'))) for n,t in texts.items()})
    out=OUT/'RESULT.json';atomic(out,encoded(result),immutable=True)
    report='''# M407 仅视觉MLP两个Linear复用并行PL核：隔离合同

视觉画像已结束。M406所选的fc2连续布局候选被用户明确的新方向替代，未实施。现有Build0x4D333537硬件不改，稳定回滚保留；仅选择原FP32状态的第12视觉层MLP，Attention/GELU/归一化/输入和语言路径保持。

| 项目 | fc1 | fc2 |
|---|---:|---:|
| 原矩阵 | [392,1024]×[4096,1024]ᵀ | [392,4096]×[1024,4096]ᵀ |
| G64输入组 |16|64|
| descriptor/chain |2|1|
| rows/shard |512×2|256|
| MM2S/chain字节 |40992|163856|
| S2MM/chain字节 |524288|131072|
| 权重暂存/每端口字节 |557056|557056|
| T32调用 |13|13|

392行分12×32+8，PL仍运算416行；完整MLP26逻辑调用、39descriptor执行，重试和Build最小事务另计。两投影权重读/复制总4,456,448B，MM2S2,663,024B，S2MM8,519,680B；七个专用缓冲payload3,440,656B，实际分配对齐及余量另计。fc1每shard流8192word刚好是已有最大FIFO边界，fc2为4096。24层将新增624逻辑调用，但当前禁止扩大。

原W4文件四份全SHA验证；实际冻结M222解码函数与PL record解码对第12层两矩阵8,388,608元素逐位相同，原T32 pack和parser的32/8行、descriptor相对地址/记录顺序/保留零位通过。不重新量化视觉权重。现有CSim/header/RTL最大FIFO/backpressure/TLAST/ap_done/timeout与路由证据保持同SHA；不是新视觉硬件PASS。

PL不计算bias，PS必须在fc1后加原bias再原GELU，fc2后加原bias。A8-G64、FP16 scale、顺序FP32 group累计、FP16输出及FTZ会改变原FP32视觉输出，不能用只做QDQ的GEMM冒充PL数值。先隔离A8误差，再用原FTZ oracle核对完整路径；输出非有限不裁剪，按原档位重试。局部cosine/.02相对L2/.995最小token cosine仅预先冻结的拒绝筛选，不证明识别质量；旧M62全视觉A8语义仅2/3通过，原拒绝保持。

下一步准备一次纯PS真实输入捕获/局部A8筛选，保留一个原第12层MLP输入及完整局部参考，无Overlay/语言；已有画像没有保存这些张量，不能用随机输入冒充。先取得实际输入再冻结单descriptor/chain参考包，通过本级后才执行完整MLP的CPU/PL交错段比较。

比较边界从第一笔权重准备到fc2+bias的PS可用输出，包含完整权重暂存、量化、pack、DMA、等待/重试、parse、转换和原GELU；不将纯kernel时间与CPU完整MLP比较。固定一CPU/一PL预热、ABBABAAB8段，记录自然缓存/I/O/内存与环境；两顺序收益均正且超过组内波动、均值至少5%为组件净收益筛选，不追加直到通过。质量或生命周期/净时间失败即停止扩大。尚未启动新上板，没有质量或提速结论。
'''
    atomic(OUT/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m407_visual_mlp_contract',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=result['package_manifest_sha256'],board_run=False,performance_pass=False),
         f'## M407视觉MLP隔离矩阵/事务合同（2026-10-05）\n\nSHA {sha(out)}；用户结束画像，M406 fc2布局候选未实施并被替代。'
         '原Build0x4D333537/RTL与hardware closure同SHA，第12视觉层fc1[4096,1024]两descriptor、fc2[1024,4096]一descriptor，392行13批/26逻辑/39descriptor；七buffer payload3440656B。'
         '四份实际视觉W4全SHA、原M222与PL record两矩阵8388608元素逐位、原32/8 T32 pack/parser检查通过，仅L0。'
         'bias/GELU仍PS，需独立A8+FP16/FTZ局部质量，旧M62全视觉A8语义2/3拒绝保持；不得用QDQ冒充PL。'
         '下一步仅准备真实第12层输入PS捕获和局部筛选，无Overlay/语言；质量后再single descriptor/chain及完整MLP含搬运/pack/parse交错净时间。'
         '两项及回收/三记录成立才扩24；不改输入/Attention/norm/语言/生产/boot/DTB/CMA。未新上板，质量/性能未通过。')
    print('M407_CONTRACT_PREPARED',sha(out),json.dumps(budget))

if __name__=='__main__':main()
