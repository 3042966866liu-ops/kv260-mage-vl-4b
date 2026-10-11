"""Saved-only first-record version closure after the one full-shell attempt."""
import json,re
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
names=['M439-record-load-csim-02','M439-record-load-schedule-guard-02','M439-record-load-narrow-closure-01','M439-record-load-core-OOC-closure-01','M439-max-protocol-rtl-01','M439-timeout-negative-01','M439-full-shell-01','M439-hwh-abi-01','M439-board-support-checks-01','M439-transfer-controls-checks-01','M439-overlay-selection-checks-01']
records={};bindings=[]
for name in names:
    p=BASE/'runs'/name/'RESULT.json';r=json.loads(p.read_bytes());digest=sha(p)
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert digest in (ROOT/n).read_text(encoding='utf-8-sig')
    records[name]=r;bindings.append(dict(path=p.relative_to(ROOT).as_posix(),status=r['status'],sha256=digest))
shell=records['M439-full-shell-01'];passed=shell['status']=='PASS_FULL_SHELL_ROUTED_TIMING'
receipt=ROOT/'tmp/m439_shell_01/out/shell_route_receipt.txt'
actual={}
if receipt.exists():
    text=receipt.read_text(encoding='utf-8')
    for k in ('WNS_NS','WHS_NS','UNROUTED_NETS'):actual[k]=float(re.search(r'^'+k+r'=([^\s]+)',text,re.M)[1])
narrow=records['M439-record-load-narrow-closure-01'];core=records['M439-record-load-core-OOC-closure-01']
r=dict(status='PASS_M439_FIRST_RECORD_OFFLINE_GATES_READY_FOR_BOARD' if passed else 'CLOSED_M439_FIRST_RECORD_FULL_SHELL_REJECTED',build_id='0x4D343339',baseline_build_id='0x4D333537',evidence=bindings,comparisons=narrow['rows'],core_timing=core['timing_summary'],core_resources=core['resources'],core_resource_delta=core['resource_delta'],full_shell_status=shell['status'],full_shell_errors=shell['errors'],actual_full_shell_route_receipt=actual,full_shell_resources=shell.get('resources',{}),maximum_protocol_pass=True,timeout_negative_pass=True,extra_PS_slots=0,extra_CMA_banks=0,next_record_prefetch=False,M437_unchanged=True,board=False,whole_request_speed_proven=False,promoted=False,next_step='Package then original COM3 Build-ID -> descriptor -> W2/W4 chain -> bounded M357/M439 comparison; no full model before real single-chain benefit.' if passed else 'Stop first version at failed full-shell timing/implementation level; preserve all evidence and original M357/M437. No board upload, no clock relaxation, no next-record pipeline or full model.')
p=BASE/'runs/M439-first-version-summary-02/RESULT.json';atomic(p,encoded(r),immutable=True)
report='# M439：单条记录连续读取第一版裁决\n\n'
report+=('离线数值、实际burst、最大协议、核心和整壳同约束时序均通过。尚未上板，不能称为新实板或完整请求提速。\n\n' if passed else '窄仿真请求数和周期改善，但完整板级实现未通过，本版停止在整壳级；尚未上板，不推进完整模型。\n\n')
report+='候选Build `0x4D343339`，对照为实际M357 `0x4D333537`。仅当前记录9/17个128位字连续读入17字片内缓冲；保留原MAC次数、FP32顺序及所有输出。无下一条预取、PS slot或CMA bank；M437后11层视觉及原语言路径保持。\n\n'
report+='| 格式 | 模型 | 原事务周期 | 候选周期 | 减少 | 每shard AR | 返回字 |\n|---|---|---:|---:|---:|---|---:|\n'
for x in narrow['rows']:report+=f'| W{x["bits"]} | {x["mode"]} | {x["A_transaction_cycles"]} | {x["B_transaction_cycles"]} | {x["transaction_reduction_percent"]:.4f}% | {x["A_requests_per_shard"][0]}→{x["B_requests_per_shard"][0]} | {x["B_return_beats_per_shard"][0]} |\n'
report+='\nW2主要9拍、W4主要17拍，跨4KiB边界拆分。每shard160次MAC调用、2560有效迭代、7840忙周期均保持，512输出完整位模式一致。随机VIP不是实际DDR；每种模型一次，不代替实板性能。\n\n'
report+='七组真实权重CSim累计16384输出通过，recursive headers missing=0。最大10 descriptor、实际FIFO占8192、地址等待10000周期和输出等待100000周期，完整327680字/TLAST1/ap_done/Build/AR/RLAST/RRESP通过。独立200周期超时负例在模拟器rc0时仍给gate rc1，验证fail-closed。\n\n'
report+='核心原4.8ns XDC逐字节SHA不变，原实际4.741ns、候选4.607ns（只核心，不代表改板频率）。候选核心LUT39175/FF46319/DSP1188/BRAM156/URAM64，原LUT40327/FF49325/DSP1184/BRAM156/URAM64。\n\n'
report+='完整板级裁决：`'+shell['status']+'`。原Vivado rc：`'+str(shell.get('vivado_rc'))+'`；实际route receipt：`'+json.dumps(actual)+'`。\n\n'
if shell['errors']:report+='原错误：\n\n'+''.join('- '+e+'\n' for e in shell['errors'])+'\n'
report+='保留首版HLS自动flatten拒绝、W4缺TV时间0失败、收集修正、原工具启动写入错误及同SHA辅助DCP读回；没有删日志或重跑门禁来清除错误。所有PASS范围按原始证据，原M437收益不变。\n\n'
report+='板测支持已完成16项fake设备/严格回收检查、本地传输6项检查与实际load函数A/B/R选择核对。固定ABBA＋BAAB，每形状每block1次primer+8正式次，全部正式样本保留；A/B同包M357/M439，R仅恢复稳定M9。用户取消固定64MiB检查保持，实际分配/地址/生命周期仍跟踪；活动DMA或未确认退出保留owner/锁/进程及全部缓冲。\n\n'
report+='下一步：'+r['next_step']+'\n\n证据：\n\n'+''.join('- ['+row['path'].split('/')[-2]+']('+str(ROOT/row['path']).replace('\\','/')+')：`'+row['sha256']+'`\n' for row in bindings)
atomic(p.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
sync('latest_m439_first_version_summary02',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),'## M439 单条记录第一版最新闭合（2026-10-07）\n\nSHA '+sha(p)+'；'+r['status']+'。W2/W4实际AR360→41/680→42、数据及MAC不变，最大协议/超时与核心PASS，完整shell='+shell['status']+'，实际route='+json.dumps(actual)+'。0上板/新完整请求收益/晋级，原M437保持。下一步 '+r['next_step'])
print(r['status'],sha(p))
