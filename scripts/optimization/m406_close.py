"""Close the PS cost observation and select one bounded component hypothesis."""
import json
from m406_analyze import analyze
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

def main():
    texts={n:(ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md')}
    a=analyze()
    p=BASE/'runs/M406-vision-cost-board-02/BOARD_RESULT.json';r=json.loads(p.read_bytes())
    assert sha(p)==a['raw_sha256'] and r['component_pass'] and r['numerical_pass'] and r['visual_owner_closed']
    gemm=[x for x in r['costs']['rows'] if x['category']=='linear_gemm'];assert len(gemm)==98
    decoder=ROOT/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py'
    source=decoder.read_text(encoding='utf-8-sig')
    assert 'output = torch.nn.functional.linear(values, weight, bias)' in source
    assert 'weight = torch.from_numpy(self.store.decode(self.name))' in source
    assert '.contiguous()' not in source
    audit=json.loads((BASE/'runs/M405-vision-evidence-audit-01/RESULT.json').read_bytes())
    # M405 froze the actual source; current board resolved identity independently rechecked it.
    assert any(v['sha256']==sha(decoder) for v in r['resolved_modules'].values())
    gelu=[x for x in r['native_cpu_operators'] if x['name']=='aten::gelu']
    captured=sum(x['calls'] for x in r['costs']['rows'] if x['category']=='GELU')
    assert len(gelu)==1 and gelu[0]['calls']==25 and captured==1
    sdpa=[x for x in r['native_cpu_operators'] if x['name']=='aten::_scaled_dot_product_flash_attention_for_cpu']
    assert len(sdpa)==1 and sdpa[0]['calls']==48 and r['attention_implementations']==['sdpa']
    assert not any(x['category'] in ('attention_QK','attention_AV','attention_softmax') for x in r['costs']['rows'])
    candidate=dict(name='MLP fc2 FP32 GEMM weight-layout component', status='SELECTED_NOT_IMPLEMENTED_OR_RUN',
        target='vision encoder M207 fc2 only, shape input[392,4096], weight[1024,4096]',
        single_change='after original dtype conversions, weight = weight.t().contiguous().t()',
        motivation='fc2 GEMM 12.343413664s; actual four-core computation already substantial',
        hypothesis='different physical weight layout may improve the existing addmm supply; overhead or floating-point differences may reject it',
        extra_weight_copy_bytes=16777216, permanent_cache_bytes=0, extra_DMA=0,
        preserve=['fixed two224 views','W4 bytes','BF16 rounding policy','FP32 GEMM','original functional.linear/bias/output conversion','thread settings','language kernel'],
        component_gate=['actual frozen forward with real Torch and same-shape operands',
                        'complete FP32 outputs bit-exact, including BF16 operand policy and nonzero bias',
                        'count contiguous copy in total Linear time; also separately record GEMM time',
                        'predeclare fixed warmup and bounded alternating component requests, no thread sweep',
                        'check buffer/owner release; only one extra16MiB temporary',
                        'numerical or net component performance failure closes this layout variant'],
        later='component PASS only permits fixed visual feature check; full video numerics and matched-cache complete-request performance remain required',
        performance_pass=False)
    value=dict(status='PASS_M406_COST_OBSERVATION_CLOSED_ONE_CANDIDATE_SELECTED',raw_sha256=a['raw_sha256'],
        raw_path=a['raw_path'],cost_table_sha256=sha(p.with_name('COST_TABLE.json')),
        same_fixed_input_visual_bit_exact=True,bindings_restored=True,sampler_joined=True,visual_owner_closed=True,
        CPU_GEMM_is_main_cost=True,GEMM_four_core_use_supported_by_process_and_system_samples=True,
        SDPA_QK_AV_softmax_individual_wall_times_not_recorded=True,
        GELU_python_hook_only_one_of_25_calls=True,other_24_GELU_remain_in_MLP_parent_wall=True,
        actual_aten_GELU_25_calls_cpu_operator_s=gelu[0]['inclusive_cpu_time_us']/1e6,
        actual_fused_SDPA_48_calls_cpu_operator_s=sdpa[0]['inclusive_cpu_time_us']/1e6,
        native_CPU_operator_times_not_additive_wall=True,backend_library_per_operator_unproven=True,
        candidate=candidate,scope='PS visual only, diagnostic not normal request performance',
        prior_M403_verdict_preserved=True,prior_hardware_40_81_percent_conclusion_preserved=True,
        production_or_service_changed=False,performance_pass=False,formal_promotion_allowed=False,
        source_sha256={n:sha(HERE/n) for n in ('m406_analyze.py','m406_close.py')})
    lines=['# M406 固定输入视觉成本与下一候选','',
           f'板端原始结果 SHA `{a["raw_sha256"]}`。固定原视频末帧两视图224，仅一次缓存预热、一次观察；没有语言前向、Overlay或DMA。',
           f'观察前向 **{a["visual_wall_s"]:.6f}秒**，98个Linear及24层覆盖，视觉输出完整SHA一致；采样线程退出、绑定恢复、原视觉对象关闭通过。观察带计时和native profiler，不能作为正常请求性能成绩。','',
           '| Linear类别 | 权重恢复秒 | 输入/权重转换秒 | 矩阵乘法秒 | 输出转换秒 |','|---|---:|---:|---:|---:|']
    labels={'QKV':'QKV','projection':'输出投影','MLP_fc1':'MLP fc1','MLP_fc2':'MLP fc2','Merger':'Merger'}
    for group,d in a['linear_group_seconds'].items():
        lines.append('|'+labels[group]+'|'+ '|'.join(f'{d.get(k,0):.6f}' for k in ('linear_weight_restore','linear_operand_conversion','linear_gemm','linear_output_conversion'))+'|')
    lines += ['',f'Linear GEMM累计 **{a["gemm_wall_s"]:.6f}秒（{a["exclusive_percent"]["linear_gemm"]:.2f}%）**；其中MLP两项 **{sum(a["linear_group_seconds"][g]["linear_gemm"] for g in ("MLP_fc1","MLP_fc2")):.6f}秒**。权重恢复 **5.808645秒**，所有输入/权重、输出及其他张量转换合计 **0.299187秒**。',
              '', '| 排他区间 | 秒 | 占比 |','|---|---:|---:|']
    for k,s in a['exclusive_seconds'].items():lines.append(f'|{k}|{s:.6f}|{a["exclusive_percent"][k]:.3f}%|')
    lines += ['', '上述排他区间合计严格等于同一次42.093409秒前向。Attention已排除QKV/输出投影；MLP父区间已排除两个Linear，避免重复计数。',
        '', '实际计算方式', '',
        'Torch 2.12.1+cpu，构建BLAS_INFO=open、ATen并行后端OpenMP；intraop/interop均4，CPU affinity 0–3，环境线程变量未设置。本次设置保持原值。实际98次Linear均有aten::addmm记录；具体每个addmm进入哪个BLAS内核仍未单独追踪，不能用构建标签替代分派证明。',
        f'GEMM窗口墙钟{a["gemm_wall_s"]:.6f}秒、进程CPU累计{a["gemm_process_cpu_s"]:.6f}秒，CPU/墙钟 **{a["gemm_cpu_to_wall"]:.3f}**。整个观察期间主线程CPU40.04秒，三个工作线程各33.98/33.99/34.01秒；另三个持久线程无CPU增量。支持这次GEMM确实在大量使用四核，不能指望单纯从1线程调到4线程获得新收益。',
        '', '| CPU | 全视觉系统忙碌% | GEMM重叠窗口系统忙碌%（100ms近似） |','|---|---:|---:|']
    for k,d in a['approximate_system_core_utilization'].items():lines.append(f'|{k}|{d["system_busy_percent"]:.2f}|{d["approximate_gemm_system_busy_percent"]:.2f}|')
    lines += ['', '逐核百分比来自系统/proc统计，GEMM归属采用100ms区间重叠近似，含其他进程；进程CPU窗口也包含观察线程开销。这两类证据一起解释实际使用规模。',
        '', 'Attention、GELU及其余成本的限制', '',
        '实际Attention为sdpa，native记录48次CPU flash attention；QK、AV及softmax融合执行，单独墙钟未记录，未为拆分计时改变原后端。排除Linear后的attention_other为1.590400秒，native fused SDPA算子CPU时间约1.107801秒；该CPU算子时间不能再次加到墙钟表。',
        'F.gelu钩子只捕获Merger的一次0.003659秒，视觉MLP原先绑定的24次GELU进入mlp_other父区间。native实际记录25次GELU、算子CPU时间0.222595秒；不能把0.003659秒称为全模型GELU时间。正常化墙钟0.092426秒；embeddings_other约1.644664秒，native对应一次slow_conv2d约1.642781秒。',
        '', '当前结论与一个候选', '',
        '视觉成本主要在真实FP32 Linear矩阵乘，MLP最大；解码约13.8%，转换和归一化不是主要成本。没有证据支持继续扫描线程数或降低输入/精度。',
        '下一候选限定为 **MLP fc2 的FP32权重物理布局组件**：在原操作数取整/转换之后，试一次 `weight = weight.t().contiguous().t()`，继续调用原functional.linear、bias和输出转换。仅改变一个供给布局，不改矩阵尺寸、输入、精度、语言核、线程或缓存策略。额外临时16MiB，退出释放；没有新增常驻缓存或DMA。',
        '它针对实测12.343414秒fc2 GEMM，但尚未实现/运行。连续化复制可能抵消收益，布局变化也可能改变BLAS浮点求和结果；不是已经找到根因或承诺提速。组件必须核对完整FP32输出逐位一致，把连续化时间计入总Linear耗时；任一数值/净耗时判据失败即结束这一布局变体。组件通过才扩大视觉/视频数值和完整请求验证。',
        '', 'M403末层跳批原裁决和此前硬件完整请求40.81%结论保持。生产服务、准入、稳定Overlay/回滚、boot/DTB/CMA均未改动；本次没有新增性能或晋级。','']
    out=p.with_name('INTERPRETATION.json');atomic(out,encoded(value),immutable=True)
    atomic(p.with_name('INTERPRETATION.md'),'\n'.join(lines).encode('utf-8'),immutable=True)
    sync('latest_m406_vision_cost_closure',dict(status=value['status'],sha256=sha(out),result=out.relative_to(ROOT).as_posix(),raw_sha256=a['raw_sha256'],performance_pass=False),
         f'## M406视觉成本闭合与单候选（2026-10-05）\n\n解读SHA {sha(out)}，原PASS SHA {a["raw_sha256"]}。'
         '同固定视觉42.093409s，98Linear/24层与完整视觉SHA、绑定/采样worker/owner释放通过；GEMM32.144678s（76.365%），MLP两GEMM21.939628s，权重恢复5.808645s。'
         'GEMM进程CPU/墙钟3.820928，主线程及3工作线程CPU增量、四核约92%系统窗口支持实际四核大量使用。'
         'SDPA融合QK/AV各自墙钟未记录；F.gelu仅1/25钩子，另24在MLP父区间，native25GELU CPU0.222595s不加入墙钟。'
         '下一步只准备MLP fc2 FP32权重预转置连续布局组件，额外临时16MiB；完整逐位与包含复制的总Linear净收益失败即结束。候选未实施/上板，禁止线程/缓存/精度一起改。'
         '本次0语言/Overlay/DMA/FPGA，计时含观察开销，无新正常请求性能/生产晋级；原40.81%与M403裁决保持。')
    print('M406_CLOSED',sha(out))

if __name__=='__main__':main()
