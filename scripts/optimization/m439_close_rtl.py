"""One deterministic two-format/two-model decision; no board speed claim."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync

def read(rel,status):
    p=BASE/rel;r=json.loads(p.read_bytes());assert r['status']==status
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert any(isinstance(v,dict) and v.get('sha256')==sha(p) for v in b.values()),p
    assert all(sha(p) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    return r,dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))

def main():
    rows=[];bindings=[]
    for bits in (2,4):
        for mode in ('zero','random'):
            if bits==2:
                a,ae=read(f'runs/M438-weight-wait-{mode}-01/RESULT.json','PASS_M438_UNCHANGED_RTL_WEIGHT_WAIT_OBSERVED')
                b,be=read(f'runs/M439-candidate_w2-{mode}-01/RESULT.json','PASS_M439_NARROW_RTL_NUMERICAL_AND_PROTOCOL')
            else:
                a,ae=read(f'runs/M439-baseline_w4-{mode}-02/RESULT.json','PASS_M439_NARROW_RTL_NUMERICAL_AND_PROTOCOL')
                b,be=read(f'runs/M439-candidate_w4-{mode}-02/RESULT.json','PASS_M439_NARROW_RTL_NUMERICAL_AND_PROTOCOL')
            assert a['output_sha256']==b['output_sha256']==a['reference_sha256']==b['reference_sha256']
            assert [x['mac_calls'] for x in a['metrics']]==[x['mac_calls'] for x in b['metrics']]==[160]*4
            assert [x['iterations'] for x in a['metrics']]==[x['iterations'] for x in b['metrics']]==[2560]*4
            ga=a['done']['cycles'];gb=b['done']['cycles'];sa=max(x['active'] for x in a['metrics']);sb=max(x['active'] for x in b['metrics'])
            rows.append(dict(bits=bits,mode=mode,A_transaction_cycles=ga,B_transaction_cycles=gb,transaction_gain_cycles=ga-gb,transaction_reduction_percent=100*(ga-gb)/ga,
              A_slowest_shard_cycles=sa,B_slowest_shard_cycles=sb,slowest_shard_reduction_percent=100*(sa-sb)/sa,
              A_requests_per_shard=[x['AR'] for x in a['metrics']],B_requests_per_shard=[x['AR'] for x in b['metrics']],
              A_return_beats_per_shard=[x['R'] for x in a['metrics']],B_return_beats_per_shard=[x['R'] for x in b['metrics']],
              B_burst_histogram=b['address_coverage'][0]['burst_histogram'],B_MAC_busy_cycles=[x['mac_busy'] for x in b['metrics']],
              no_next_record_prefetch=all(x['AR_during_MAC']==x['R_during_MAC']==0 for x in b['metrics']),full_output_exact=True))
            bindings.extend([ae,be])
    ok=all(x['transaction_gain_cycles']>0 and x['B_slowest_shard_cycles']<x['A_slowest_shard_cycles'] and all(v==x['B_requests_per_shard'][0] for v in x['B_requests_per_shard']) and x['B_requests_per_shard'][0]<x['A_requests_per_shard'][0] for x in rows)
    hls,he=read('runs/M439-record-load-hls-02/RESULT.json','PASS_M439_HLS_RESOURCE_REPORT');bindings.append(he)
    r=dict(status='PASS_M439_NARROW_BURST_AND_CYCLE_COMPARISON' if ok else 'CLOSED_M439_NARROW_NO_BENEFIT',build_id='0x4D343339',baseline_build_id='0x4D333537',
      rows=rows,source_evidence=bindings,resources_HLS=hls['resources'],HLS_clock_estimate_ns=hls['estimated_clock_ns'],
      single_current_record_only=True,extra_PS_slots=0,extra_CMA_banks=0,numerical_narrow=True,numerical_full_model=False,
      model='Original VIP seed356 Random 0..256 vs Zero added latency; synthetic driver delays, not actual DDR timing. Control/activation/output also use the selected delay model. Each condition once, no statistical board effect.',
      original_W2_A_reused=True,W4_A_source_exact_M357=True,implementation_timing=False,board=False,board_speed_proven=False,production_promotion=False,
      preserved_rejections=['01 HLS auto-flattened MAC pairs/token-pairs toII2; isolated02 guards original50cycleII1 nest',
                           'W4 A first fixture omitted pointer TV and failed time0; independent02 adds exact original pointer files',
                           'Saved-only W4 address coverage sorts intervals because original pair-word issue order can interleave; all original chronological addresses retained'],
      next_step='Same-constraint core-only OOC resource/routed timing; maximum FIFO/descriptor/backpressure/timeout RTL closure before full shell. No next-record pipeline or full model until first-version board single-chain benefit.' if ok else 'Stop this record-load version at narrow comparison. No core implementation/board/full-model expansion.')
    p=BASE/'runs/M439-record-load-narrow-closure-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    report='# M439 当前记录连续读取：第一版隔离结果\n\n候选 Build `0x4D343339`，原核 `0x4D333537`。只增加每 shard 单条17×128-bit片内记录缓冲；W2实际9字/W4实际17字。原解包/FP32累加顺序、4pair×16token-pair、四shard、FIFO与输出合同保持；没有下一条预取、PS slot或CMA bank。\n\n'
    report+='| 格式 | VIP延迟模型 | 原事务周期 | 候选事务周期 | 周期减少 | 每shard地址请求 A→B | 返回字数 |\n|---|---|---:|---:|---:|---|---:|\n'
    for x in rows:report+=f'| W{x["bits"]} | {x["mode"]} | {x["A_transaction_cycles"]} | {x["B_transaction_cycles"]} | {x["transaction_reduction_percent"]:.4f}% | {x["A_requests_per_shard"][0]}→{x["B_requests_per_shard"][0]} | {x["B_return_beats_per_shard"][0]} |\n'
    report+='\nW2为39个9字burst加4/5字边界拆分；W4为38个17字burst加1/16与2/15字拆分。所有字节地址严格无重复/无空洞覆盖，无跨4KiB非法burst；返回字数/RLAST/协议检查通过。原W4单字读取可交错发出，故按地址排序检查覆盖，并保存实际时间顺序。\n\n'
    report+='所有条件的512输出字/keep/strb/TLAST/Build逐位核对通过，四shard各160次MAC调用、2560次有效迭代、MAC忙7840周期。候选计算期间AR/R均0，确认没有把第二项“下一条提前加载”混入。W2复用M438原A，未重跑原完整Q；W4只补原真实权重fixture ordinal1/family5/G40/rows8/单descriptor，参考来自两种独立组织的原FP32逐组算术及既有FTZ。\n\n'
    report+='原七组真实权重CSim累计16384输出通过，header missing=0。02 HLS资源：'+json.dumps(hls['resources'])+'；同part、4.8ns目标、1.3ns HLS uncertainty，估计3.5ns。**尚未证明实现频率或板端收益。** 四shard周期并行不可相加；VIP延迟不是板端DDR，不把表中百分比套用到完整模型或M437请求。\n\n'
    report+='保留首版自动flatten的II2拒绝、W4时间0参数漏项失败和只读地址覆盖修正。稳定服务/Overlay/boot/DTB/CMA/回滚未改，原M437结果不变。\n\n下一步：同约束核心OOC布局布线，再补最大descriptor/FIFO/回压/超时门禁后才考虑完整shell和实板单链。单链实测收益后才与同一M437视觉/语言路径做完整请求，暂不加入下一条预取流水。\n'
    atomic(p.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m439_record_load_narrow_closure',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),
      f'## M439 第一版连续记录读窄RTL裁决（2026-10-07）\n\nSHA {sha(p)}；{r["status"]}；W2/W4、Random/Zero各一次，完整输出/所有MAC计数与数据量不变，AR按记录burst实际减少。仅仿真周期，非板端DDR/完整请求收益；资源为HLS估计。所有旧失败保留，无PS/CMA/下一条预取，M437基线不改。下一步 {r["next_step"]}')
    print('M439_NARROW_CLOSED',sha(p),r['status']);print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
