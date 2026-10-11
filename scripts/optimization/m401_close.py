"""Saved-only M401 full text closure. No board access or gate dispatch."""
import json
import re
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m401_collect import PKG,decode

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    e=board['latest_m401_tail_text_board'];p=ROOT/e['result']
    assert sha(p)==e['sha256']
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    log=ROOT/'tmp/m401/component_uart.log';text=log.read_text(encoding='utf-8-sig')
    digest,raw,r=decode(text)
    assert raw==p.read_bytes() and digest==e['sha256']
    assert r['status']=='PASS_M401_TAIL_TEXT_NUMERICAL' and not r['errors']
    assert r['common_runner_sha256']==sha(PKG/'m401_tail_text_gate.py')
    for key in ('latest_m401_tail_text_preparation','latest_m401_tail_text_support','latest_m401_tail_text_transfer'):
        evidence=board[key];assert sha(ROOT/evidence['result'])==evidence['sha256']
        assert evidence['manifest_sha256']==r['manifest_sha256']
        assert all(evidence['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    for row in json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']:
        assert sha(PKG/row['path'])==row['sha256'] and (PKG/row['path']).stat().st_size==row['bytes']
    v=r['layer_result'];parts=re.findall(r'(?m)^M401_RESULT_CHUNK=(\d+)/(\d+):',text)
    value=dict(status='PASS_FIXED30_FULL36_PREFILL_TAIL_NUMERICAL_ONLY',build_id=r['build_id'],raw_result=e['result'],raw_sha256=digest,
               manifest_sha256=r['manifest_sha256'],source_precheck=r['source_precheck_before_hardware_import'],layer_prerequisite_sha256=r['layer_prerequisite_sha256'],
               fixed_tokens=30,full_layers=36,language_families=len(v['families']),logits=v['logits'],token=v['token'],keys=v['keys'],values=v['values'],
               logical_calls=v['logical_calls'],physical_model_calls=v['host_calls'],total_with_minimal=r['fpga_transactions'],retry_count=v['retry_count'],retry_launches=v['retry_launches'],
               stage_bytes=v['stage_bytes'],tail_scope=r['tail_scope'],seven_original_DMA_released=True,scope_weakref_dead=True,stable_overlay_restored=True,
               production_policy_unchanged=True,production_threshold_would_admit=r['production_threshold_would_admit'],sampled_memory=r['sampled_memory'],
               exact_instantaneous_peak_proven=False,UART_chunks=len(parts),fixed_text_numerical_pass=True,candidate_full_model_executed=True,
               fixed159_video_pass=False,performance_pass=False,formal_promotion_allowed=False,
               next_step='Prepare separate fixed159 complete video numerical gate with full visual/features/KV/logits/reference and changed 766-call contract; no performance before numeric closure.')
    out=BASE/'runs/M401-tail-text-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    report=f'''# M401 末层候选完整固定文本数值验证

候选 Build `{r['build_id']}`，固定30-token输入，完整36层及完整151936词表LM head。原154个family的完整输入/输出SHA、151936 logits、全部36K/36V、Token17、缩放选档与三次保护重试严格等于冻结M344参考；物理事务身份及字节数等于已通过M366记录。

162次逻辑、165次模型物理调用，另有同Overlay合法最小事务，共166次。30-token只有一个原T32批次，末层选择起点0、保留30行，计算量没有减少；本级验证完整模型接入正确性，不衡量速度。

完整包/原M241 SHA、确定性完整Prefill提取、同解释器AST还原检查在硬件gate导入和资源分配之前通过。只加入一个末层选择边界，保持完整QKV/Attention和全部KV、原数学、打包、单解析worker与缩放重试；PS预读、SiLU工作缓冲关闭。

七块原DMA完整驻留后封锁新增分配，原owner安全逆序释放；候选scope/binding及observer关闭、弱引用消失、patch registry清空；稳定Overlay由固定环境预检后恢复。恢复后的初始DMA0是未提交生命周期，不当作已完成事务idle。原boot/DTB/CMA/服务/回滚及生产64MiB政策保持。

诊断使用既有1GiB普通RSS增长预算及64MiB普通可用余量，并逐family/物理提交检查CMA调用计数保持。20ms采样不能证明瞬时峰值或生产容量；加载、完整SHA和数值观察耗时不是正常推理性能。

原始结果SHA `{digest}`，{len(parts)}个900B以内分块严格回收；闭合SHA `{h}`。

下一步独立固定159视频完整数值门禁，核对视觉特征、全部KV/logits、最终判断、事务和释放。预期逻辑调用需按末层裁剪重新推导，当前计划766；真实重试及物理数以实际记录和同输入参考裁决。视频数值与三记录同步后才能做整体交错性能。本次没有新的性能或晋级结论。
'''
    atomic(out.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m401_tail_text_closure',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,raw_sha256=digest,fixed_text_numerical_pass=True,performance_pass=False,formal_promotion_allowed=False),
         f'## M401 固定文本完整模型闭合（2026-10-04）\n\nBuild0x4D333537，raw `{digest}`，闭合 `{h}`；原30token/36层/完整head，154family/151936logits/72KV/Token17及3重试精确一致，162逻辑/165模型物理加minimal166。scope/binding/weakref/observer和七DMA退出、稳定恢复核对。30token不裁剪批次，只有完整模型数值接入结论，无新性能；生产政策保持，下一步单独固定159视频数值预算/合同及新包。')
    print(json.dumps(dict(status=value['status'],raw_sha256=digest,closure_sha256=h)))

if __name__=='__main__':main()
