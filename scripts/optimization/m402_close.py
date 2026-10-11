"""Saved-only numerical closure; no upload, Overlay or gate dispatch."""
import json
import re
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m402_collect import PKG,decode

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=board['latest_m402_tail_video_board'];p=ROOT/e['result']
    assert p==BASE/'runs/M402-tail-video-board-01/BOARD_RESULT.json' and sha(p)==e['sha256']
    for n in ('CURRENT_STATE.md','docsMILESTONES.md'):assert e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig')
    log=ROOT/'tmp/m402/component_uart.log';text=log.read_text(encoding='utf-8-sig')
    digest,raw,r=decode(text);assert raw==p.read_bytes() and digest==e['sha256']
    assert r['status']=='PASS_M402_TAIL_VIDEO_NUMERICAL' and not r['errors']
    assert r['common_runner_sha256']==sha(PKG/'m402_tail_video_gate.py')
    for key in ('latest_m402_tail_video_preparation','latest_m402_tail_video_support','latest_m402_tail_video_transfer'):
        item=board[key];assert sha(ROOT/item['result'])==item['sha256'] and item['manifest_sha256']==r['manifest_sha256']
        for n in ('CURRENT_STATE.md','docsMILESTONES.md'):assert item['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig')
    for item in json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        assert sha(PKG/item['path'])==item['sha256'] and (PKG/item['path']).stat().st_size==item['bytes']
    v=r['video_result'];parts=re.findall(r'(?m)^M402_RESULT_CHUNK=(\d+)/(\d+):',text)
    value=dict(status='PASS_FIXED159_FULL_VIDEO_LAST_LAYER_TAIL_NUMERICAL_ONLY',build_id=r['build_id'],raw_result=e['result'],raw_sha256=digest,manifest_sha256=r['manifest_sha256'],fixed_tokens=159,full_layers=36,families=len(v['families']),logits=v['logits'],token=v['token'],keys=v['keys'],values=v['values'],visual_features=r['visual_features'],semantic=r['candidate_semantic'],logical_calls=v['logical_calls'],model_physical_calls=v['host_calls'],total_with_minimal=r['fpga_transactions'],language_retries=v['language_retries'],head_retries=v['head_retries'],stage_bytes=v['stage_bytes'],tail_scope=r['tail_scope'],count_scope=r['count_scope'],seven_original_DMA_released=True,scope_weakrefs_dead=True,stable_overlay_restored=True,production_policy_unchanged=True,sampled_memory=r['sampled_memory'],exact_instantaneous_peak_proven=False,UART_chunks=len(parts),candidate_numerical_pass=True,performance_pass=False,formal_promotion_allowed=False,next_step='Prepare independent lightweight same-input balanced request timing only; preserve single parser/current kernel, prefetch/SiLU off; no raw numerical hashing inside performance timings.')
    out=BASE/'runs/M402-tail-video-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    report=f'''# M402 固定159视频末层裁剪数值闭合

Build `{r['build_id']}`，固定原最后帧两视图、224分辨率、98视觉token、159语言token、原提示/权重。前三十五层完整，末层QKV/RoPE/Attention及所有K/V完整；后三投影只处理原最后31行。原单解析worker，PS预读/SiLU工作缓冲关闭。

视觉特征、154个family（后三项采用同输入末31行参考）、完整36K/36V、151936 logits及Token15/ABSENT判断精确一致；全部保留物理事务/字节与尺度重试记录严格一致。766逻辑、767模型物理（一次语言保护重试），加同Overlay合法最小事务共768。少12个原T32逻辑批次及被省略区域的两次保护重试；权重暂存仍为2,034,890,752B。

原始计数没有修改，只在独立scope为固定159/单token绑定766检查合同。实际stream检查Build/真实宏数与计数；执行后恢复原778计算函数，两个scope/绑定/弱引用/采样关闭，七原DMA安全逆序释放并恢复稳定Overlay。新增DMA0；原生产64MiB准入与boot/DTB/CMA/服务/回滚保持。20ms采样不证明瞬时峰值或长期服务内存。

原raw SHA `{digest}`，{len(parts)}个≤900B分块，闭合SHA `{h}`。本级只证明候选完整固定视频数值与生命周期；带大量哈希/诊断的时间不能当性能。旧并行核约40.81%请求收益保持独立；本裁剪候选新增收益尚未测试。

下一步仅准备独立轻量计时的同输入交错整体请求对照。固定视频、原计时边界和缓存记录保持，数值观察不进入性能测量区间；若没有稳定净收益关闭变体。
'''
    atomic(out.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m402_tail_video_closure',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,raw_sha256=digest,candidate_numerical_pass=True,performance_pass=False,formal_promotion_allowed=False),f'## M402 固定159视频末层候选数值闭合（2026-10-04）\n\nBuild0x4D333537，raw `{digest}`，闭合 `{h}`；视觉/154family/完整72KV/151936logits/Token15/ABSENT与冻结同输入参考精确一致。766逻辑/767模型物理/一次语言重试加minimal768，weight stage2034890752B保持。双scope/原计数恢复/weakref/observer/七DMA及稳定恢复核对，新增DMA0。只固定视频数值，无裁剪性能或晋级；生产政策保持。下一步单独准备轻量同输入整体交错性能。')
    print(json.dumps(dict(status=value['status'],raw_sha256=digest,closure_sha256=h)))

if __name__=='__main__':main()
