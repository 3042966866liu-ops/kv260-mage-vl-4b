"""Read existing code, contracts and saved measurements; no board/model execution."""
import csv
import io
import json
import statistics
from collections import defaultdict
from m351_workflow import ROOT, BASE, HERE, sha, atomic, encoded, sync
from m371_profile_summary import summarize


def main():
    recovery = {}
    texts = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        path = ROOT/name
        texts[name] = path.read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=sha(path), bytes=path.stat().st_size, lines=len(texts[name].splitlines()))
    board = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    evidence = []

    def bound(name, filename='RESULT.json'):
        path = BASE/'runs'/name/filename
        digest = sha(path)
        matches = [v for v in board.values() if isinstance(v, dict) and v.get('sha256') == digest]
        assert matches and all(digest in texts[n] for n in ('CURRENT_STATE.md', 'docsMILESTONES.md')), name
        value = json.loads(path.read_bytes())
        evidence.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=digest, status=value['status']))
        return value

    prior = bound('M439-board-summary-01')
    assert prior['status'] == 'CLOSED_M439_FIRST_VERSION_BOARD_BENEFIT_NOT_PROVEN'
    comparison = bound('M439-compare-board-01', 'BOARD_RESULT.json')
    assert comparison['gate_return_code'] == 1 and comparison['comparison']['cases']['q_full']['pass_']
    narrow = bound('M439-record-load-narrow-closure-01')
    csim = bound('M439-record-load-csim-02')
    maximum = bound('M439-max-protocol-rtl-01')
    profile_closure = bound('M371-candidate-profile-closure-01')
    wait_closure = bound('M375-video-wait-closure-01')
    current = bound('M437-natural-IO-board-01', 'BOARD_RESULT.json')
    current_closure = bound('M437-natural-IO-closure-01')
    visual = bound('M430-complete-visual-warm-board-01', 'BOARD_RESULT.json')
    io_record = bound('M436-IO-observation-board-02', 'INTERPRETATION.json')
    read_audit = bound('M434-read-path-audit-01')
    assert current['build_id'] == '0x4D333537' and current['selected_layers'] == list(range(13,24))
    assert current['PS_prefetch'] is False and current['parser_workers'] == 1
    pkg = BASE/'candidates/M437-late11-natural-IO-performance-01'
    assert sha(pkg/'PACKAGE_MANIFEST.json') == current['manifest_sha256']
    manifest = json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes())
    for row in manifest['files']:
        path = pkg/row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    closure = json.loads((pkg/'SOURCE_CLOSURE.json').read_bytes())
    sources = []
    source_text = {}
    for row in closure['files']:
        options = [ROOT/row['path'], ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'/row['path']]
        path = next((p for p in options if p.is_file() and p.stat().st_size == row['bytes'] and sha(p) == row['sha256']), None)
        assert path is not None, row['path']
        sources.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size))
        source_text[row['path']] = path.read_text(encoding='utf-8-sig')
    for name, row in profile_closure['source_evidence'].items():
        assert sha(ROOT/row['path']) == row['sha256']
        assert any(s['sha256'] == row['sha256'] for s in sources)
    trace_path = BASE/'runs/M371-candidate-profile-board-01/PREFILL_TRACE.json'
    summary_path = trace_path.parent/'PROFILE_SUMMARY.json'
    assert sha(trace_path) == profile_closure['trace_sha256'] and sha(summary_path) == profile_closure['summary_sha256']
    trace = json.loads(trace_path.read_bytes())
    summary = summarize(trace)
    assert summary == json.loads(summary_path.read_bytes())
    events = trace['trace']['events']
    byid = {r['id']:r for r in events}
    contracts = {}
    for label, key in (('LANGUAGE','language'),('LMHEAD','lmhead')):
        path = ROOT/f'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_{label}_RUNTIME_CONTRACT_RESULT.json'
        assert sha(path) == read_audit['language_layouts'][key]['contract_sha256']
        contracts[key] = json.loads(path.read_bytes())
        evidence.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), status=contracts[key]['status']))
    chains = {(r['layer'],r['family']):r for r in contracts['language']['chains']}

    def owner(event):
        while event is not None:
            if event['name'] == 'language_family':
                return (event['metadata']['layer'], event['metadata']['family'])
            if event['name'] == 'lm_head':
                return ('head','lm_head')
            event = byid.get(event['parent'])
        return None

    stats = defaultdict(lambda: defaultdict(float))
    for row in events:
        key = owner(row)
        if key is None:
            continue
        if row['name'] == 'device_completion_wait':
            stats[key]['device_wait_s'] += row['inclusive_ns']/1e9
            stats[key]['physical_calls'] += 1
        if row['name'] == 'weight_stage':
            stats[key]['weight_stage_s'] += row['inclusive_ns']/1e9
            stats[key]['stage_calls'] += 1
        if row['name'] == 'language_family':
            stats[key]['family_wall_s'] += row['inclusive_ns']/1e9
            stats[key]['family_calls'] += 1
            assert row['metadata']['input_shape'] == [159, chains[key]['groups']*64]
    assert len([k for k in stats if k[0] != 'head']) == 154
    assert sum(s['physical_calls'] for s in stats.values()) == 781
    assert abs(sum(s['device_wait_s'] for s in stats.values()) - summary['main_exclusive_s']['device_completion_wait']) < 1e-10
    rows = []
    categories = defaultdict(list)
    for chain in contracts['language']['chains']:
        key = chain['layer'],chain['family']
        s = stats[key]
        assert s['family_calls'] == s['stage_calls'] == 1 and s['physical_calls'] >= 5
        drows = [d['rows_per_shard'] for d in chain['descriptors']]
        record_words = 1+4*chain['bits']
        records = chain['groups']*sum(n//8 for n in drows)
        payload_bytes = records*record_words*16
        assert payload_bytes == sum(d['record_bytes_per_shard'] for d in chain['descriptors'])
        window_bytes = (max(d['offset_words']*16+d['record_bytes_per_shard'] for d in chain['descriptors'])
                        - min(d['offset_words']*16 for d in chain['descriptors']))
        assert window_bytes == chain['staged_bytes_per_shard'] and window_bytes >= payload_bytes
        row = dict(chain_index=chain['chain_index'], layer=chain['layer'], family=chain['family'],
                   bits=chain['bits'], groups=chain['groups'], descriptor_count=chain['descriptor_count'],
                   rows_per_shard=drows, output_bytes=chain['output_bytes'],
                   record_words=record_words, records_per_shard=records,
                   weight_record_payload_bytes_per_shard=payload_bytes,
                   staged_window_gap_bytes_per_shard=window_bytes-payload_bytes,
                   group_address_strides_bytes=[n//8*record_words*16 for n in drows],
                   staged_bytes_all_shards=chain['staged_bytes_all_shards'], logical_calls=5,
                   physical_calls=int(s['physical_calls']), device_wait_s=s['device_wait_s'],
                   weight_stage_s=s['weight_stage_s'], family_wall_s=s['family_wall_s'])
        rows.append(row)
        categories[(row['family'],row['bits'],row['groups'],row['descriptor_count'],tuple(drows))].append(row)
    category_rows = []
    for key, items in categories.items():
        category_rows.append(dict(family=key[0],bits=key[1],groups=key[2],descriptors=key[3],rows_per_shard=list(key[4]),
             chains=len(items), logical_calls=sum(r['logical_calls'] for r in items),
             physical_calls=sum(r['physical_calls'] for r in items),
             device_wait_s=sum(r['device_wait_s'] for r in items),weight_stage_s=sum(r['weight_stage_s'] for r in items),
             family_wall_s=sum(r['family_wall_s'] for r in items),
             per_call_wait_ms_range=[min(r['device_wait_s']/r['physical_calls']*1000 for r in items),max(r['device_wait_s']/r['physical_calls']*1000 for r in items)],
             chain_indices=[r['chain_index'] for r in items],layers=[r['layer'] for r in items]))
    w2 = [r for r in rows if r['bits'] == 2]
    q = [r for r in rows if r['family'] == 'q']
    assert len(w2)==25 and len(q)==10 and sum(r['logical_calls'] for r in rows)==770
    w2_wait=sum(r['device_wait_s'] for r in w2)
    q_wait=sum(r['device_wait_s'] for r in q)
    main_wait=summary['main_exclusive_s']['device_completion_wait']
    major_w4=sum(r['device_wait_s'] for r in rows if r['bits']==4 and r['family'] in ('gate_up','mlp_down'))
    plan = json.loads((pkg/'PLAN.json').read_bytes())
    visual_chains=[]
    for layer in range(13,24):
        for part in ('fc1','fc2'):
            c=plan['chains'][str(layer)][part]
            dr=[d['rows_per_shard'] for d in c['descriptors']]
            assert c['bits']==4 and sum(d['weight_bytes_per_shard'] for d in c['descriptors'])==c['stage_bytes_per_shard']==557056
            visual_chains.append(dict(layer=layer,part=part,bits=4,groups=c['groups'],descriptors=c['descriptor_count'],
                 rows_per_shard=dr,output_bytes=c['output_bytes'],logical_calls=13,
                 records_per_shard=c['groups']*sum(n//8 for n in dr),
                 group_address_strides_bytes=[n//8*17*16 for n in dr]))
    b_visual=[s for s in visual['warmup_samples']+visual['formal_samples'] if s['variant']=='B']
    assert len(visual['PL_rows'])==len(b_visual)*286
    visual_formal=[]
    for i,s in enumerate(b_visual):
        physical=visual['PL_rows'][i*286:(i+1)*286]
        assert sum(r['wait_ns'] for r in physical)==s['device_wait_ns']
        if s['phase']=='formal':
            visual_formal.append(dict(index=s['index'],visual_s=s['elapsed_ns']/1e9,
                  device_wait_s=s['device_wait_ns']/1e9,staging_s=s['staging_ns']/1e9,
                  fc1_wait_s=sum(r['wait_ns'] for r in physical if r['part']=='fc1')/1e9,
                  fc2_wait_s=sum(r['wait_ns'] for r in physical if r['part']=='fc2')/1e9))
    assert len(visual_formal)==4
    current_means={}
    for variant in ('A','B'):
        samples=[s for s in current['formal_samples'] if s['variant']==variant]
        assert len(samples)==4
        current_means[variant]=dict(total_s=statistics.mean(s['timing']['total_ms']/1000 for s in samples),
              vision_s=statistics.mean(s['timing']['stages_ms']['vision']/1000 for s in samples),
              prefill_s=statistics.mean(s['timing']['stages_ms']['prefill']/1000 for s in samples),
              head_s_included_in_prefill=statistics.mean(s['timing']['stages_ms']['head']/1000 for s in samples),
              visual_weight_staging_s=statistics.mean(sum(r['elapsed_ns'] for r in s['visual_staging'])/1e9 for s in samples),
              stored_read_bytes=[s['io_delta']['read_bytes'] for s in samples])
        assert all('device_wait_ns' not in s for s in samples)
    kernel_path=ROOT/'tmp/m357_activation_banks/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
    kernel=kernel_path.read_text(encoding='utf-8')
    required=('const unsigned words = 1 + 4 * bits;', 'const unsigned base = group * blocks * words + block * words;', 'ap_uint<128> tagged = memory[base];', 'm89x_decode_pair(memory + base, pair, bits, tagged0, tagged1,', 'for (unsigned token_pair = 0; token_pair < 16; ++token_pair)', 'm89x_shard(s0, x[0], as[0]', 'm89x_shard(s3, x[3], as[3]')
    assert all(x in kernel for x in required)
    sources.append(dict(path=kernel_path.relative_to(ROOT).as_posix(),sha256=sha(kernel_path),bytes=kernel_path.stat().st_size))
    m238=source_text[closure['modules']['m238_prefill_runtime']]
    assert m238.index('buffers, base_words = self._stage(')<m238.index('for block_index, token_start in enumerate(blocks):')
    assert 'ThreadPoolExecutor(max_workers=1, thread_name_prefix="m238-parse")' in m238
    result=dict(status='PASS_M440_SAVED_LONG_CHAIN_RELEVANCE_AUDIT_ONLY',build_id='0x4D333537',
       recovery_read=recovery,evidence=evidence,verified_sources=sources,profile_trace_sha256=sha(trace_path),
       language_categories=category_rows,language_chains=rows,head_instrumented_totals=dict(stats[('head','lm_head')]),
       visual_chains=visual_chains,visual_isolated_formal=visual_formal,current_request_means=current_means,
       W2_chains=25,W2_logical_calls=125,Q_exact_geometry_chains=10,Q_logical_calls=50,
       instrumented_W2_wait_s=w2_wait,instrumented_Q_wait_s=q_wait,
       instrumented_W2_wait_fraction=w2_wait/main_wait,instrumented_Q_wait_fraction=q_wait/main_wait,
       instrumented_W4_gate_down_wait_s=major_w4,instrumented_W4_gate_down_wait_fraction=major_w4/main_wait,
       M439_long_W4_performance_proven=False,current_request_device_CPU_split_recorded=False,
       board_calls=0,model_forward_calls=0,weight_payload_reads=0,hardware_reexecuted=False,
       old_M439_verdict_changed=False,new_candidate_implemented=False,promoted=False,
       next_step='If a new long-chain experiment is authorized, prioritize real full-size language W4 gate_up, then W4 mlp_down; freeze a new independent protocol before tests. Preserve closed M439 verdict and do not add its samples. No complete-request gain estimate from Q alone.')
    folder=BASE/'runs/M440-long-chain-relevance-audit-01'
    path=folder/'RESULT.json'
    report='# M440：完整模型长链相关性与已有成本核对\n\n'
    report+='只读取已有结果、当前冻结代码和调用合同；没有上板、模型前向、权重数据读取或新性能样本。M439原FAIL关闭，未增加样本、改旧判据或自动实现下一版。\n\n'
    report+='结论：有理由另立长链实验，但重点应是语言W4 gate_up／mlp_down。Q的单链收益是真实局部证据，不能直接推到整个请求；全部W2在已有并行核诊断中的设备等待仅占7.69%。完整视觉MLP的W4性能仍需按真实大尺寸独立证明。\n\n'
    report+='## 1. 相同读取结构，不同规模与跨记录步长\n\n'
    report+='实际M357四shard共用m89x_shard：block→group→读scale字→四pair分别读权重并MAC。W2记录9×128bit，W4记录17×128bit；地址为group×blocks×words＋block×words。因此所有合法W2/W4链具备相同代码结构，但不同groups、每descriptor行数、descriptor个数、权重/输出规模和跨group地址步长，不能视为相同DDR等待。\n\n'
    report+='| 代表 | 位数/G | D与每shard行数 | 每shard记录数 | 每shard读取128位字 | 跨group地址步长B | T32输出B |\n|---|---|---|---:|---:|---|---:|\n'
    reps=[('M439小W2',2,40,[8],4096),('M439完整Q',2,40,[512,512],524288),('语言gate_up W4',4,40,[512]*4+[384]+[512]*4+[384],2490368),('语言mlp_down W4',4,152,[512,128],327680),('视觉fc1 W4',4,16,[512,512],524288),('视觉fc2 W4',4,64,[256],131072)]
    for name,bits,g,dr,out in reps:
        words=1+4*bits;nr=g*sum(n//8 for n in dr)
        report+=f'| {name} | W{bits}/G{g} | {len(dr)} / {dr} | {nr} | {nr*words} | {sorted(set(n//8*words*16 for n in dr))} | {out} |\n'
    report+='\n小W2只有一条descriptor、每shard8行；完整Q为两条各512行，记录/返回字/输出均是小W2的128倍，跨group步长144→9216B。这是重要差别；仅凭该差别仍不能判定46.67%降幅的具体DDR根因。所有链均保留原T32 MAC和FP32顺序；新记录缓冲只改变权重供给。PL实际访问的记录字数与PS暂存窗口分开：部分gate_up窗口包含descriptor间隙（例如第0层每port额外2048B）；已按原offset和末端核对，不将暂存量直接当PL返回量。\n\n'
    report+='## 2. 语言实际调用与旧并行核诊断的对应成本\n\n'
    report+='下表从M126原合同与M371完整trace重新按parent链归属计算；154个family/770逻辑批，另8个head，3次重试，共781次物理事务严格闭合。输入159→32/32/32/32/31，最后一批仍执行原T32合同。计时属于M371一次带观察、包含自然读盘的诊断，不能当最新暖请求的分项计时。\n\n'
    report+='| family | W/G/D | 链数 | 逻辑/物理事务 | 设备完成等待s | 一次family前暂存s | family墙钟s |\n|---|---|---:|---|---:|---:|---:|\n'
    for r in category_rows:
        report+=f"| {r['family']} | W{r['bits']}/G{r['groups']}/D{r['descriptors']} | {r['chains']} | {r['logical_calls']}/{r['physical_calls']} | {r['device_wait_s']:.6f} | {r['weight_stage_s']:.6f} | {r['family_wall_s']:.6f} |\n"
    head=stats[('head','lm_head')]
    report+=f"| LM head | W4/G40/D10×7＋D5×1 | 8 | 8/8 | {head['device_wait_s']:.6f} | {head['weight_stage_s']:.6f} | {next(r['inclusive_ns'] for r in events if r['name']=='lm_head')/1e9:.6f} |\n"
    report+=f'\n与Q完全相同几何的层0–9 Q：10链/50次，等待{q_wait:.6f}s，占本诊断30.009027s设备等待的{q_wait/main_wait*100:.2f}%。W2还包括层0–9 attention_out、3层gate_up及2层mlp_down：总25链/125次，等待{w2_wait:.6f}s（{w2_wait/main_wait*100:.2f}%）。其他W2只有结构相同，不能继承Q的46.67%实测降幅。\n\n'
    report+=f'W4 gate_up＋mlp_down等待{major_w4:.6f}s，占{major_w4/main_wait*100:.2f}%；是新的长链候选最有价值的目标。精确层号、逐链尺寸、暂存/等待与跨group步长都在CALLS.csv与RESULT.json中。family墙钟包含暂存、等待、PS调度/解析收尾，不与这些子项再次相加。\n\n'
    report+='## 3. 大W4证据边界\n\n'
    report+='M439七组真实权重CSim包括G40/D10 gate_up、G152/D2 down、G40/D4 qkv和head，但都是每shard8行的缩小数值夹具。小W4窄RTL证明实际17拍burst、AR680→42及该小尺寸仿真周期改善；板端W4双descriptor链也只有每shard8行。最大协议RTL覆盖512行/D10/FIFO8192，但G=1且全零，是协议/背压证明。以上均不构成真实全尺寸W4的板端性能证据。M439未测完整语言gate_up/down或视觉fc1/fc2的增量收益。\n\n'
    report+='旧M357上的完整视觉W4证据已经存在：后11层fc1为G16/D2/512+512，fc2为G64/D1/256；392行→13批，每请求22 Linear/286事务。它证明现有核该范围的数值和性能，不证明M439会加速。\n\n'
    report+='| M430视觉独立B正式请求 | 完整视觉s | fc1设备等待s | fc2设备等待s | 总设备等待s | 权重暂存s |\n|---|---:|---:|---:|---:|---:|\n'
    for r in visual_formal:report+=f"| {r['index']} | {r['visual_s']:.6f} | {r['fc1_wait_s']:.6f} | {r['fc2_wait_s']:.6f} | {r['device_wait_s']:.6f} | {r['staging_s']:.6f} |\n"
    report+='\n设备等待均值约2.1235s，视觉约38s；其余视觉仍包含CPU Linear、权重恢复、Attention、GELU、归一化、转换和调度。不能把约38秒全算作PL事务，也不能把剩余时间全部归到某一个CPU算子。当前M437正式请求保存了视觉总时长和22暂存，未保存其逐事务wait_ns。\n\n'
    report+='## 4. 完整请求与精细画像必须分开\n\n'
    report+='| M437正式均值 | 请求s | 视觉s | 语言Prefill s（含head） | head s | 视觉权重暂存s（含在视觉） |\n|---|---:|---:|---:|---:|---:|\n'
    for variant,r in current_means.items():report+=f"| {variant} | {r['total_s']:.6f} | {r['vision_s']:.6f} | {r['prefill_s']:.6f} | {r['head_s_included_in_prefill']:.6f} | {r['visual_weight_staging_s']:.6f} |\n"
    report+='\nM437八正式样本均read_bytes=0，协议仍保留自然I/O；该次观察零读盘不等于消除了read、复制或同步。B的视觉约35.86%、Prefill约61.50%，其余约2.82s是计时边界中的其他工作。M437没有导出语言逐事务时间、语言暂存分解、解析实际等待或CPU数学分项：这些当前比例明确记为未记录，不将旧画像百分比套到65.59s。\n\n'
    report+='M371诊断Prefill91.377140s、请求135.588430s：主线程互斥设备等待30.009027s（Prefill32.84%）、权重读/复制/同步与bookkeeping29.679277s（32.48%）、PS数学8.488920s（9.29%）、其他23.199916s（25.39%）。设备等待含DMA、DDR、计算、输出背压和调度，不是纯PL计算。读取26.877673s、复制1.121958s、同步0.120390s是其子项。后台解析33.663709s及pack5.356398s与主线程重叠，不再相加。\n\n'
    report+='M375另一次窄等待观察测得实际解析阻塞11.299733s，其中gate_up8.098718s（71.67%），复用3.822935s/收尾7.476798s；它不与M371画像相加，也不代替M437暖请求分项。较快PL可能暴露更多解析、pack或CPU成本，因此长链局部收益必须最终通过完整请求检验。M436两次请求的语言/head读盘不同，进一步说明缓存影响不可忽略。\n\n'
    report+='## 5. 是否另立长链候选\n\n'
    report+='值得准备一个独立实验，首先针对真实全尺寸W4 gate_up，其次W4 mlp_down；Q作为长W2对照。若目标是视觉，再单独覆盖fc1 G16/D2与fc2 G64/D1。不能仅测Q或小W4，也不能改变视觉层选择、量化、提示或输入来混入额外收益。\n\n'
    report+='新实验须在运行前冻结自己的问题、形状、计时边界和停止条件，区分完整尺寸数值、完整事务周期、读取/输出限制与完整请求净收益。小事务作为正确性覆盖，不据当前记录宣称小事务等价或无回退。无论新结果如何，M439总FAIL与所有旧样本保持；本审计未准备/上传新硬件包或解锁完整模型。\n\n'
    report+='证据与源码身份已绑定于RESULT.json，完整逐链CSV可复算；本报告只解读已有证据，不是新优化PASS或生产晋级。\n'
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader()
    for row in rows:writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    atomic(folder/'CALLS.csv',stream.getvalue().encode('utf-8-sig'),immutable=True)
    atomic(folder/'REPORT.md',report.encode('utf-8'),immutable=True)
    result['report_sha256']=sha(folder/'REPORT.md');result['calls_csv_sha256']=sha(folder/'CALLS.csv')
    atomic(path,encoded(result),immutable=True)
    sync('latest_m440_long_chain_audit',dict(status=result['status'],result=path.relative_to(ROOT).as_posix(),sha256=sha(path),report=(folder/'REPORT.md').relative_to(ROOT).as_posix(),board=False,old_M439_verdict_changed=False),
         '## M440 完整模型长链相关性与成本审计（2026-10-07）\n\nSHA '+sha(path)+'；仅当前冻结源码/合同及保存结果复算，0上板/前向/权重数据/新样本。W2为25链125批，精确Q为10链50批；M371等待W2 '+f'{w2_wait:.6f}'+'s（7.69%），Q '+f'{q_wait:.6f}'+'s（1.98%），W4 gate_up/down '+f'{major_w4:.6f}'+'s（69.56%）。当前M437 B请求106.645947s/视觉38.242428s/Prefill65.586963s，逐设备与PS分解未记录，不能套旧画像占比；旧视觉W4完整证据属M357，不证明M439大W4收益。M439FAIL关闭不改。可另立预先冻结的真实长W4 gate_up/down独立实验，本轮未实现/上板。详见REPORT和154链CSV。')
    print(json.dumps(dict(status=result['status'],sha256=sha(path),W2_wait_s=w2_wait,Q_wait_s=q_wait,W4_gate_down_wait_s=major_w4,current_request_means=current_means)))


if __name__=='__main__':main()
