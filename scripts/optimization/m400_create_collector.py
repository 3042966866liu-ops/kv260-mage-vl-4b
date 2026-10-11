"""Create scope-specific saved-result validator from the strict M399 envelope."""
from m351_workflow import HERE,atomic
from m400_prepare import change

VALIDATOR='''def validate_layer(r):
    pin=json.loads((PKG/'TAIL_LAYER_PREREQUISITE.json').read_text(encoding='utf-8'))
    c=r['layer_scope'];f=pin['reference_manifest']['fixtures']
    if r['original_reference_sha256']!=PRIOR or pin['raw_sha256']!=PRIOR or c['reference_sha256']!=PRIOR:raise ValueError('Original reference pin differs')
    if r['chain_prerequisite_sha256']!=pin['chain_raw_sha256'] or pin['chain_raw_sha256']!='924ae716e4e399b6f94f522d279b5f6472328bbb6049ebfb6d16004d5f95c992':raise ValueError('Prior three-chain pin differs')
    original=BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json'
    chain=BASE/'runs/M399-tail-chain-board-01/BOARD_RESULT.json'
    if sha(original)!=PRIOR or sha(chain)!=pin['chain_raw_sha256']:raise ValueError('Recovered prerequisite drift')
    if not c['closed'] or c['retained'] or not c['invoked'] or not c['reference_maps_released'] or not c['binding_callback_removed'] or not c['original_family_restored'] or c['reference_files_checked']!=11:raise ValueError('Layer owner/maps/binding closure differs')
    if c['extra_DMA'] or c['parser_workers']!=1 or c['PS_prefetch'] or c['SiLU_workspace'] or c['candidate_full_model_executed'] or c['performance_pass']:raise ValueError('Layer scope exceeded')
    expected=dict(families=pin['expected_families'],key=pin['expected_key'],value=pin['expected_value'],
                  attended_full=f['attended_full']['tensor'],hidden_tail=f['hidden_tail']['tensor'],final_norm=f['final_norm']['tensor'],
                  full_QKV_KV_SHA_equal=True,full_attention_and_tail_tensors_bitwise_equal=True,
                  last_layer=35,original_tokens=159,tail_start=128,tail_tokens=31,grouped_attention_calls=1,LM_head_executed=False)
    if r['layer_result']!=expected or c['layer_result']!=expected or c['family_rows']!=expected['families']:raise ValueError('Full layer numerical tensor contract differs')
    if r['transactions']!=pin['expected_transactions']:raise ValueError('Physical layer identities/byte counts differ')
    d=r['layer_call_delta']
    expected_counts=dict(logical_calls=8,host_calls=8,stage_bytes=53624832,scale_retry_count=0,pipeline_retry_launches=0,logical_expected_macros=81920000,expected_macros=81920000)
    if d!=expected_counts:raise ValueError('Layer calls/staging/macros/retry differs')
    e=r['layer_runtime_evidence']
    if any(e[k]!=v for k,v in expected_counts.items()) or e['scale_attempts']!=pin['expected_scale_attempts']:raise ValueError('Original runtime counters/scale choices differ')
    if r['isolated_layer_calls']!=1:raise ValueError('Independent layer count differs')

'''


def main():
    target=HERE/'m400_collect.py'
    if target.exists():raise RuntimeError('New collector already exists')
    s=change((HERE/'m399_collect.py').read_text(encoding='utf-8'))
    s=s.replace('sealed-DMA-isolated-last31-three-chains','sealed-DMA-isolated-layer35-fullAttention-last31')
    a=s.index('def validate_chains');z=s.index('def decode',a);s=s[:a]+VALIDATOR+s[z:]
    s=s.replace('validate_chains(r)','validate_layer(r)').replace('PASS_M400_LAST31_CHAIN_NUMERICAL','PASS_M400_TAIL_LAYER_NUMERICAL')
    s=s.replace("r['fpga_transactions']!=4 or r['logical_calls']!=3 or r['host_calls']!=3","r['fpga_transactions']!=9 or r['logical_calls']!=8 or r['host_calls']!=8")
    s=s.replace("r['chain_numerical_pass']","r['layer_numerical_pass']").replace('chain_numerical_pass=passed','layer_numerical_pass=passed')
    s=s.replace('三个原末31 chain完整输出精确一致、3逻辑/3物理加minimal4，七DMA与参考map安全释放/稳定恢复。只解锁独立单层准备，未完成候选模型或性能。','原layer35完整159QKV/Attention/KV及末31后三投影/hidden/norm精确一致，8逻辑/8层物理加minimal9，七DMA/reference maps/owner安全释放与稳定恢复。仅单层，未固定文本/候选视频或性能。')
    s=s.replace('本级失败，保持原返回码和资源状态；仅本级故障/保存结果回收，不解锁单层。','本级失败，保持原返回码和资源；只允许本单层级调试或保存结果回收，不解锁固定文本。')
    s=s.replace('M400 三个末31 chain板端结果','M400 末层组合板端结果')
    s=s.replace('Independent chain escaped scope','Independent layer escaped scope')
    atomic(target,s.encode('utf-8'))
    print('M400_COLLECTOR_CREATED')


if __name__=='__main__':main()
