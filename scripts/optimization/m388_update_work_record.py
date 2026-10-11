"""Add verified latest evidence to the user's existing work record, preserving history."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
def link(label,relative):return '['+label+']('+ROOT.as_posix()+'/'+relative+')'
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));latest=board['latest_m388_ps_performance_closure'];closure=json.loads((ROOT/latest['result']).read_text(encoding='utf-8'))
    assert sha(ROOT/latest['result'])==latest['sha256'] and all(latest['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    path=ROOT/'KV260_本轮优化完整工作记录_2026-10-01.md';previous=path.read_text(encoding='utf-8-sig');prior_sha=sha(path);header='## 2026-10-03 补充：普通PS预读逐级数值与完整请求对照'
    if header in previous:raise RuntimeError('Supplement already exists')
    rows=[];sources={}
    specs=[('M382','latest_m382_sealed_ps_slot_closure','完整runtime/原七DMA、封锁新增DMA，slot分配—逐页触写—释放，0forward'),('M383','latest_m383_ps_descriptor_closure','同核原暂存/PS暂存单descriptor，完整wire FTZ和权重字节'),('M384','latest_m384_ps_chain_closure','完整Q双descriptor chain，全输出/权重字节与生命周期'),('M385','latest_m385_ps_layer_closure','原layer0五family/hidden/KV，159重复文本embedding，连续五窗口'),('M386','latest_m386_ps_text_closure','原30-token固定文本，36层/完整head，151936logits/72KV，162窗口'),('M387','latest_m387_ps_video_closure','原159-token固定视频，视觉/语言/151936logits/72KV/最终判断，162窗口'),('M388','latest_m388_ps_performance_closure','同并行核/单parser，A原暂存/B普通PS预读，ABBABAAB完整请求对照')]
    for milestone,key,scope in specs:
        meta=board[key];assert sha(ROOT/meta['result'])==meta['sha256'];sources[key]=meta
        rows.append('| '+milestone+' | '+scope+' | '+meta['status']+' | '+link('证据',meta['result'])+' |')
    text=[header,'','**最新裁决：'+closure['status']+'。**','', '本节更新此前停在M355的报告；后文均保留为当时历史快照。以下新结果均在板端完成、原始结果SHA回收后核对，并同步BOARD/CURRENT_STATE/docsMILESTONES。','', '本次继续使用已经验证的并行硬件Build **0x4D333537**，并未再修改RTL。原硬件调整得到的约 **40.81%** 完整请求下降保持独立结论；这一补充测量的是在该硬件上叠加普通PS预读的增量效果。双解析worker此前M381因稳定净收益未证明已关闭，本次两组均为原单parser。','', '| 步骤 | 实际范围 | 裁决 | 原始闭合索引 |','| --- | --- | --- | --- |',*rows,'', '预读复用原M350/M351实现：一个四端口普通PSslot合计 **27,852,800B（26.5625MiB）**、一个后台读取worker，零额外PYNQ/DMA；当前family及全部T32/解析/缩放重试完成后，前景复制并同步到原四权重DMA缓冲。只有四端口复制/同步完成才开始下一窗口读取。旧双CMA bank路线与O_DIRECT路线没有恢复。','', '容量条件已经明确区分：**原生产64MiB CMA门槛保持**。独立诊断在真实七块原DMA全部成功分配后，封锁公共及捕获分配入口，检查CMA API计数不变，使用实际普通内存增长停止预算和64MiB普通可用余量。单层/文本256MiB、完整视频1GiB RSS停止上限包含PSslot。这是独立、固定输入、有界诊断规则；不是提高了CmaFree、正式降低生产门槛、无内存压力或任意输入/长期服务准入证明。','', 'M387视频中PS检查最小CmaFree约20.539MiB，20ms采样最低8.578MiB；采样最小MemAvailable约2540.738MiB，最大观测RSS增长约609.602MiB。逐阶段检查与采样极值不同，不能混用，采样也不能证明精确native瞬时峰值。视频原778逻辑/781物理调用和三次语言重试保持，另有同Overlay合法最小事务，总782次；原始SHA `'+board['latest_m387_ps_video_board']['sha256']+'`。slot/session/fd/views/worker及原七DMA安全释放，稳定Overlay恢复。','']
    if closure['numerical_pass']:
        t=closure['overall']['total_ms'];text += [f'M388完整请求均值：A **{t["A"]["mean_ms"]/1000:.3f}s**，B **{t["B"]["mean_ms"]/1000:.3f}s**，平均差 **{t["saved_ms"]/1000:.3f}s（{t["reduction_percent"]:.2f}%）**。采用全部八次ABBABAAB；收益裁决沿用两种顺序差超过组内波动、A最小值仍高于B最大值的保守标准。平均差本身不等于净收益已成立。','']
    else:text += ['M388未完成八次门禁，因此不产生新的预读性能结论。','']
    text += [link('M388完整测量与裁决报告','deployment/mage_vl4b/optimization_v1/runs/M388-ps-performance-closure-01/REPORT.md')+'。B的slot分配、首窗口等待、路径身份检查、前景复制/同步和关闭都在原请求计时内；计划组装、资产SHA、Overlay/构造和完整数值哈希在计时外。原PS视觉缓存预热、自然文件缓存、逐请求I/O/缓存/内存记录保持；不是冷启动性能。','', '本轮操作拒绝也保留：M385首包离线遗漏层binder，未上传，另建02；M387两源传输选择在离线最后核对中被拒绝，另建recovered02；M387collector同步键误沿用m386，独立saved-only修复只重读原UART字节，同SHA闭合后才解锁M388，没有重跑视频。所有sudo过期只停在上传前，人工恢复后使用新日志确认，未猜密码或反复探测。','', '**后续：'+closure['next_step']+'。** 稳定服务、源码、rollback、boot/DTB/CMA均未替换，自动化保持此前暂停状态；没有正式晋级。','', '本次使用的原始结果/闭合SHA：','']
    for key,meta in sources.items():text.append('- '+key+'：`'+meta['sha256']+'`。')
    text+=['', '---','', '以下为此前报告的历史快照：','']
    title,rest=previous.split('\n',1);atomic(path,(title+'\n\n'+'\n'.join(text)+rest.lstrip('\n')).encode('utf-8'));report_sha=sha(path)
    receipt=dict(status='PASS_EXISTING_WORK_RECORD_SUPPLEMENT',previous_report_sha256=prior_sha,updated_report_sha256=report_sha,report=path.relative_to(ROOT).as_posix(),sources=sources,performance_closure_sha256=latest['sha256'],historical_content_preserved=True,hardware_rerun=False)
    out=BASE/'runs/M388-work-record-update-01/RESULT.json';atomic(out,encoded(receipt),immutable=True);d=sha(out)
    sync('latest_m388_work_record_update',dict(status=receipt['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,report=receipt['report'],report_sha256=report_sha),f'## M388 用户完整工作记录补充\n\n原报告历史保留，新增M382—M388完整容量/数值/性能进展、独立生产准入边界和拒绝记录，引用已同步SHA；报告SHA {report_sha}，核对SHA {d}。没有硬件重跑/服务变更；当前实验裁决以latest_m388_ps_performance_closure为准。')
    print('M388_WORK_RECORD_UPDATED',report_sha,str(path))
if __name__=='__main__':main()
