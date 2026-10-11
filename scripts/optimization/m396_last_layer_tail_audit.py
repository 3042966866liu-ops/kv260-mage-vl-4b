"""Saved-source/evidence audit only. No COM3, imports of runtime, or model runs."""
import ast
import hashlib
import json
from pathlib import Path

from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync

RELEASE = ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
OUT = BASE/'runs/M396-last-layer-tail-audit-01'
FAMILIES = ('attention_out','gate_up','mlp_down')

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    if OUT.exists(): raise RuntimeError('Immutable audit already exists; read it only')
    recovery = {}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/name; s=p.read_text(encoding='utf-8-sig')
        recovery[name]={'sha256':sha(p),'bytes':p.stat().st_size,'lines':len(s.splitlines())}
    board=load(ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json')
    prior=board['latest_m395_silu_performance_closure']
    assert sha(ROOT/prior['result']) == prior['sha256']
    assert prior['status']=='CLOSED_SILU_WORKSPACE_NET_BENEFIT_UNPROVEN'
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    closure_path=BASE/'candidates/M395-silu-performance-01/SOURCE_CLOSURE.json'
    closure=load(closure_path)
    identities=[]
    sources={}
    for row in closure['files']:
        p=RELEASE/row['path']
        assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'], row['path']
        identities.append(row)
        if p.suffix=='.py':sources[row['path']]=p.read_text(encoding='utf-8-sig')
    modules=closure['modules']
    language=sources[modules['m241_video_language_runtime']]
    executor=sources[modules['m238_prefill_runtime']]
    parser=sources[modules['m236_prefill_runtime']]
    math_source=sources[modules['video_language_runtime']]
    packet=sources[modules['contract_runtime']]
    # Explicit source assertions support the consumer and batch dependency audit.
    assert 'keys.append(k.copy())' in language and 'values.append(v.copy())' in language
    assert language.index('keys.append(k.copy())') < language.index('projected = self._family')
    assert 'rms_norm(hidden[-1:]' in language and 'self.runtime.lm_head(final)[0]' in language
    assert 'axis=-1, keepdims=True' in math_source
    assert 'initial_shift = self._initial_scale_shift(block_values)' in executor
    assert 'pending.attempted_shifts[-1] - 1' in parser
    assert 'token_start:token_start + token_count' in parser
    assert 'token_start' not in ast.get_source_segment(packet,next(n for n in ast.parse(packet).body if isinstance(n,ast.FunctionDef) and n.name=='pack_chain_input'))
    consumers=[]
    for path,s in sources.items():
        for i,line in enumerate(s.splitlines(),1):
            if '.prefill(' in line:
                consumers.append({'path':path,'line':i,'source':line.strip()})
    # Search current optimization helpers and frozen resolved closure, not stale bulk snapshots.
    hits=[]; searched=[]
    patterns=('last_layer','tail_batch','last-layer-tail','末层','最后一层')
    for p in sorted((ROOT/'scripts/optimization').glob('*.py')):
        if p.name.startswith('m396_'):continue
        s=p.read_text(encoding='utf-8-sig'); searched.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})
        for i,line in enumerate(s.splitlines(),1):
            if any(t in line for t in patterns):hits.append({'path':p.relative_to(ROOT).as_posix(),'line':i,'source':line[:300]})
    contract_path=RELEASE/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
    contract=load(contract_path)
    chains={c['family']:c for c in contract['chains'] if c.get('layer')==35 and c['family'] in FAMILIES}
    assert len(chains)==3
    evidence_paths=[BASE/'runs/M371-candidate-profile-board-01/PREFILL_TRACE.json',
                    BASE/'runs/M375-video-wait-board-01/WAIT_TRACE.json',
                    BASE/'runs/M394-silu-video-board-01/BOARD_RESULT.json']
    trace,wait,numeric=map(load,evidence_paths)
    assert numeric['numerical_pass'] and numeric['build_id']=='0x4D333537'
    assert len(numeric['video_result']['scale_attempts'])==778
    costs=[]; es=trace['trace']['events']
    for fam in FAMILIES:
        family=next(e for e in es if e['name']=='language_family' and e['metadata']=={'family':fam,'input_shape':[159,9728 if fam=='mlp_down' else 4096 if fam=='attention_out' else 2560],'layer':35})
        ids={family['id']}; children=[]
        for e in es:
            if e['parent'] in ids:ids.add(e['id']); children.append(e)
        stage=sum(e['inclusive_ns'] for e in children if e['name']=='weight_stage')
        launches=[e for e in children if e['name']=='_launch_prepacked']
        assert len(launches)==5
        remove_ids={e['id'] for e in launches[:4]} | {e['id'] for e in children if e['name']=='_launch_once'}
        removed_wait=sum(e['inclusive_ns'] for e in children if e['name']=='device_completion_wait' and e['parent'] in remove_ids)
        wr=[r for r in wait['records'] if r.get('layer')==35 and r.get('family')==fam and r.get('kind')=='parse']
        record={'family':fam,'chain_index':chains[fam]['chain_index'],
                'inclusive_ms_diagnostic':family['inclusive_ns']/1e6,'unchanged_stage_ms_diagnostic':stage/1e6,
                'nonstage_wall_ms_diagnostic':(family['inclusive_ns']-stage)/1e6,
                'removed_transaction_wait_ms_diagnostic':removed_wait/1e6,
                'removed_parse_result_wait_ms_separate_run':sum(r['result_wall_ns'] for r in wr if r['token_start']<128)/1e6,
                'all_parse_result_wait_ms_separate_run':sum(r['result_wall_ns'] for r in wr)/1e6,
                'per_transaction_input_bytes':chains[fam]['input_bytes'],
                'per_transaction_output_bytes':chains[fam]['output_bytes'],
                'per_transaction_expected_macros':chains[fam]['expected_macros'],
                'unchanged_staged_weight_bytes':chains[fam]['staged_bytes_all_shards']}
        costs.append(record)
    # The accept order is 0,32,64,128,96: final two outputs resolve by DMA slot.
    shifts=[]
    for fam in FAMILIES:
        rows=[a for a in numeric['video_result']['scale_attempts'] if a.get('layer')==35 and a['family']==fam]
        assert len(rows)==5
        for start,a in zip((0,32,64,128,96),rows): shifts.append(dict(a,original_token_start=start,retained=start==128))
    deleted_retries=sum(len(a['attempted_shifts'])-1 for a in shifts if not a['retained'])
    retained_retry=sum(len(a['attempted_shifts'])-1 for a in shifts if a['retained'])
    assert deleted_retries==2 and retained_retry==0
    calls={'original_logical':778,'candidate_planned_logical':778-3*4,
           'removed_logical':12,'original_recorded_physical':781,
           'removed_retries_in_saved_input':deleted_retries,'remaining_retries_in_saved_input':3-deleted_retries,
           'candidate_expected_physical_if_numerically_identical':781-12-deleted_retries,
           'minimum_transaction_excluded':True,
           'formula_general':'154*ceil(N/32)+8-3*(ceil(N/32)-1); physical=logical+actual retries',
           'scale_accept_original_order_token_starts':[0,32,64,128,96]}
    demand={'removed_nominal_macros':4*sum(c['expected_macros'] for c in chains.values()),
            'removed_macros_including_saved_retries':4*sum(c['expected_macros'] for c in chains.values())+2*chains['mlp_down']['expected_macros'],
            'removed_input_bytes_including_saved_retries':4*sum(c['input_bytes'] for c in chains.values())+2*chains['mlp_down']['input_bytes'],
            'removed_output_bytes_including_saved_retries':4*sum(c['output_bytes'] for c in chains.values())+2*chains['mlp_down']['output_bytes'],
            'unchanged_three_family_weight_staging_bytes':sum(c['staged_bytes_all_shards'] for c in chains.values()),
            'removed_gate_up_float32_output_allocation_bytes':128*9728*4*2,
            'additional_dma_allocations':0,'additional_ps_workspace_required':False}
    references=[]
    for name in ('m241_video_language_runtime','m238_prefill_runtime','m236_prefill_runtime','video_language_runtime','contract_runtime','m276_video_runtime'):
        p=modules[name]; references.append({'module':name,'path':p,'sha256':sha(RELEASE/p)})
    value={'status':'PASS_READ_ONLY_TAIL_AUDIT_WORTH_ISOLATED_GATE','evidence_level':'SOURCE_AND_SAVED_DIAGNOSTICS_ONLY',
           'candidate_build_id':'0x4D333537','stable_rollback_build_id':'0x4D395832','recovery_read':recovery,
           'prior_closure_sha256':prior['sha256'],'source_closure_sha256':sha(closure_path),'verified_frozen_files':identities,
           'resolved_modules':references,'prefill_consumers_in_resolved_closure':consumers,
           'prior_attempt_search_files':searched,'prior_attempt_search_hits':hits,'same_candidate_found_in_searched_scope':bool(hits),
           'search_is_global_absence_proof':False,'saved_evidence':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in evidence_paths],
           'contract':{'path':contract_path.relative_to(ROOT).as_posix(),'sha256':sha(contract_path)},
           'batch_plan':{'tokens':159,'tail_start':128,'tail_count':31,'before_layer35_attention':'full159',
                         'preserved_layers':35,'preserved_kv_tensors':72,'preserved_lm_head_logits':151936,
                         'retained_packet_padding_tokens':1,'original_tail_dma_slot':0,'candidate_tail_dma_slot':0},
           'tail_scale_records_from_saved_video':shifts,'calls':calls,'demand':demand,'costs':costs,
           'quantization_cross_batch_dependency_found':False,'token_start_is_wire_field':False,
           'cross_batch_counters_are_diagnostic_only':True,
           'important_caveat':'Skipped rows no longer pass post-Attention/post-MLP finite checks. Limit first candidate to explicit fixed159 diagnostic; preserve full QKV/KV/Attention checks and reject unsupported API consumers.',
           'missing_metrics':['Measured tail-only request time','Exact last-token hidden tensor reference in saved JSON','Last31 projected tensors: only full159 hashes saved','Per-layer uninstrumented timing','Exact runtime peak'],
           'production_call_contract_unchanged':True,'implementation_done':False,'board_run':False,'numerical_pass':False,'performance_pass':False,'formal_promotion_allowed':False,
           'rejected_attempts':['Do not reinterpret full159 tensor SHA as last31 tensor SHA','Do not expect 769 physical calls: saved first mlp_down batch includes two deleted retries','Do not patch production expected_physical_calls globally','Do not claim all family inclusive time can be saved; staging remains'],
           'next_step':'Prepare default-off isolated fixed159 scope and actual frozen packet/scale/parser checks; compare full/reference and tail last hidden + 151936 logits + 72 KV. Keep original SiLU, single parser, PS prefetch off; no board run before scoped gates.'}
    atomic(OUT/'RESULT.json',encoded(value),immutable=True);h=sha(OUT/'RESULT.json')
    total=sum(c['inclusive_ms_diagnostic'] for c in costs);nonstage=sum(c['nonstage_wall_ms_diagnostic'] for c in costs)
    lines=['# M396 末层保留原最后T32批：只读审计','',
           '**结论：值得做一个隔离候选，尚未实现或上板；没有新提速结论。**',
           '', '冻结实际加载闭包全部逐文件SHA核对。最后一层先完成全部Q/K/V、RoPE、Attention及K/V复制，然后进入三个逐token投影；完整前35层保持。最终只有hidden[-1:]进入最终RMS和完整词表LM head。KVCache仍含36层全部159行K/V；继承Decode只读/追加这些K/V，不依赖已丢弃的末层其他hidden行。所选加载闭包和现有优化脚本未找到同样裁剪；不是全项目历史不存在的证明。','',
           '最后一层必须同时截取attended[128:159]与residual[128:159]，之后保持原RMS、SiLU×up、残差和原family方法。不能只截投影输入而保留159行残差。新候选不叠加已关闭的SiLU工作缓冲、PS预读或双解析worker。','',
           '原初始shift在每个block内独立计算，重试档位保存在当前_pending_block，未发现跨批传播。量化组max沿64通道维计算，packet不含全局token_start；解析token_start只是目标数组行偏移。31行截片与原末批输入相同才可保留字节及选档。159输入末批原block_index=4，使用DMA slot0；候选唯一block_index=0同样用slot0。保留原T32 padding、descriptor/weight-offset、32行输出长度及完整FIFO事务。','',
           '**诊断顺序陷阱**：scale_attempts的接收顺序是0、32、64、128、96，不是token顺序；末尾按DMA slot排序收尾。原末层down首批0发生6→5→4，两次重试会随裁掉的批消失；原末批128是6→6无重试。必须保存原全局起始行与候选局部起始行映射，不能用列表最后一项冒充末批。','',
           f'原778逻辑/781物理，候选计划**766逻辑**；按已有相同输入选档不变推导为**767物理**（保留第6层一次重试，裁掉末层两次），另计合法最小事务。物理次数最终以实际重试为准，绝不硬编码成功重试为0。生产M276入口仍要求778，候选需独立proof合同；原服务计数函数不改。','',
           '| layer35 family | 已有带观察墙钟ms | 保留的权重stage ms | 非stage墙钟ms | 被裁事务设备等待ms |','| --- | ---: | ---: | ---: | ---: |']
    for c in costs:lines.append(f'| {c["family"]} | {c["inclusive_ms_diagnostic"]:.3f} | {c["unchanged_stage_ms_diagnostic"]:.3f} | {c["nonstage_wall_ms_diagnostic"]:.3f} | {c["removed_transaction_wait_ms_diagnostic"]:.3f} |')
    lines += ['',f'三处原墙钟共{total/1000:.6f}s，其中约{(total-nonstage)/1000:.6f}s权重stage保持；非stage约{nonstage/1000:.6f}s仍包括必须保留的末批。这里只说明机会大约在一秒量级，不能把这{total/1000:.3f}s全部当成可省时间。M371带大量观察，Prefill91.377s不是轻量正常请求；设备等待含DMA/访存/计算。M375的解析等待来自另一请求，只列作单独线索，不与M371设备时间或后台累计时间相加。没有新的组件/完整请求性能测量。','',
              f'名义少{demand["removed_nominal_macros"]:,}个现有contract expected_macros计数单位；连同已记录两次down重试少{demand["removed_macros_including_saved_retries"]:,}。该单位不是FLOP。输入DMA字节计划少{demand["removed_input_bytes_including_saved_retries"]:,}，输出少{demand["removed_output_bytes_including_saved_retries"]:,}；三family权重暂存仍{demand["unchanged_three_family_weight_staging_bytes"]:,}B。两个gate/up FP32目标数组少{demand["removed_gate_up_float32_output_allocation_bytes"]/2**20:.2f}MiB累计申请量，不是已测RSS峰值。无新增DMA或工作slot需求。','',
              '独立候选限定原159-token首token诊断。原末层对所有hidden的finite检查会变成只检查保留31行；因此不宣称错误检测语义对任意输入完全不变。全QKV/KV/Attention仍执行并核对；unsupported shape/consumer应拒绝。保留所有完整输入检查，不能以此修改生产准入。','',
              '现有结果保存全159 family哈希、logits及72KV哈希，没有可由哈希推导的末31 tensor或最后hidden数组。隔离门禁须从同输入原路径获取末层切片参考，核对三family末批输入/输出/选档及最后hidden，再核对完整logits、72KV、视觉和最终判断。前151个完整family仍按原参考比较。不能将形状改变解释为旧参考自动通过。','',
              '验证顺序：默认关闭scope的源码/真实冻结pack-scale-parser离线检查 → 固定末层三个代表chain末批隔离数值/生命周期 → 单层 → 固定文本（≤32时计划不裁剪）→ 原159视频完整数值 → 同缓存政策轻量ABBABAAB完整请求。各级证据同步后再推进，失败留在当前级。只改变末层处理范围，复用匹配硬件47项证据；当前并行Build0x4D333537，稳定rollback0x4D395832保持。','',
              '实际源码依据：']
    for x in references:lines.append(f'- `{x["path"]}` SHA `{x["sha256"]}`')
    lines+=['','已有证据：']
    for x in value['saved_evidence']:lines.append(f'- `{x["path"]}` SHA `{x["sha256"]}`')
    lines+=['',f'审计RESULT SHA `{h}`。未访问COM3、未加载Overlay、未改稳定源码/服务/回滚/boot/DTB/CMA。','']
    atomic(OUT/'REPORT.md','\n'.join(lines).encode('utf-8'),immutable=True)
    sync('latest_m396_last_layer_tail_audit',{'status':value['status'],'result':(OUT/'RESULT.json').relative_to(ROOT).as_posix(),'sha256':h,'build_id':'0x4D333537','board_run':False,'numerical_pass':False,'performance_pass':False,'formal_promotion_allowed':False},
         f'## M396 末层最后T32批只读审计（2026-10-04）\n\n审计SHA `{h}`，报告 `{(OUT/"REPORT.md").relative_to(ROOT).as_posix()}`；冻结{len(identities)}文件同SHA，后三投影逐token、末批shift/重试独立，前三十五层和完整末层QKV/Attention/KV保持。计划766逻辑，按原输入推导767物理（裁掉down首批两重试），实际物理仍按重试记录。三family原带观察墙钟{total/1000:.6f}s，stage保留约{(total-nonstage)/1000:.6f}s，非stage尚含必须保留末批，不是已测收益。仅只读审计，未实现/上板，生产778计数合同/准入/服务不改；SiLU工作缓冲、PS预读、双parser关闭，旧硬件40.81%保持。下一步独立默认关闭scope与原pack/scale/parser组件门禁，再逐级数值/视频/性能；不得由全159哈希冒充末31参考。')
    print(json.dumps({'status':value['status'],'sha256':h,'costs':costs,'calls':calls,'demand':demand,'duplicate_search_hits':hits,'report':str(OUT/'REPORT.md')},ensure_ascii=False))

if __name__=='__main__':main()
