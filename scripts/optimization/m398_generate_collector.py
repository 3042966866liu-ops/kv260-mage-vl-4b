"""Generate a saved-only collector from exact proven full-video validation."""
from m351_workflow import HERE,atomic
from m398_prepare import change

def main():
    s=change((HERE/'m394_collect.py').read_text(encoding='utf-8'))
    s=s.replace("PRIOR='5f304889c48969a259297b56dfc4d7e361f19ed434208b4e8ae8a154c33785b3'","PRIOR='17817f223700a901e924af4c01dd30b1497b1052c6df03acd9bbfef5e4b96250'")
    a=s.index('def expected_scope():');z=s.index('\ndef decode(text):',a)
    function='''def validate_capture(r,expected):
    from m398_reference_capture import SHAPES,PAYLOAD_BYTES
    c=r['reference_capture']
    if not c['closed'] or c['retained'] or not c['binding_callback_removed'] or c['additional_dma_allocations'] or c['source_hooks']!=3 or not c['removed_hooks_ast_equals_original'] or not c['candidate_tail_not_executed']:raise ValueError('Original capture scope differs')
    if c['last_families']!=['attention_out','gate_up','mlp_down'] or c['steps']!=['full-attention','full-hidden','original-final-norm']:raise ValueError('Capture ordering differs')
    if c['file_count']!=12 or set(c['fixtures'])!=set(SHAPES) or c['payload_bytes']!=PAYLOAD_BYTES or c['file_budget_bytes']!=16<<20:raise ValueError('Fixture inventory/budget differs')
    sizes=0
    for name,shape in SHAPES.items():
        f=c['fixtures'][name];t=f['tensor'];size=4
        for d in shape:size*=d
        if t['shape']!=list(shape) or t['dtype']!='float32' or t['bytes']!=size or not re.fullmatch('[0-9a-f]{64}',t['sha256']):raise ValueError('Fixture tensor identity differs')
        if f['path']!='/home/ubuntu/m398_tail_reference_01/B1/'+name+'.npy' or not re.fullmatch('[0-9a-f]{64}',f['file_sha256']) or not size<f['file_bytes']<=size+512:raise ValueError('Fixture file identity differs')
        start=128 if name.endswith('_tail') or name in ('gate_tail','up_tail','hidden_tail') else 158 if name in ('final_norm','logits') else 0
        if f['original_token_start']!=start:raise ValueError('Fixture token mapping differs')
        sizes+=f['file_bytes']
    if sizes!=c['file_bytes'] or sizes>16<<20:raise ValueError('Fixture sizes differ')
    if c['fixtures']['logits']['tensor']!=expected['logits'] or c['fixtures']['attended_full']['tensor']!=expected['families'][-3]['input']:raise ValueError('Captured original outputs differ')

'''
    s=s[:a]+function+s[z:]
    original="        if r['silu_text_prerequisite_sha256']!=PRIOR or r['ps_prefetch_enabled'] or r['worker_started'] or not r['scope_weakref_dead'] or not r['silu_workspace_enabled'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1:raise ValueError('Variant/lifetime differs')\n        if r['silu_scope']!=expected_scope():raise ValueError('36 borrowed-result scopes differ')"
    assert s.count(original)==1
    s=s.replace(original,"        if r['tail_capture_prerequisite_sha256']!=PRIOR or r['ps_prefetch_enabled'] or r['worker_started'] or not r['scope_weakref_dead'] or r['silu_workspace_enabled'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1 or r['tail_candidate_executed'] or r['candidate_numerical_pass'] or not r['reference_capture_pass']:raise ValueError('Original-only variant/lifetime differs')\n        validate_capture(r,expected)")
    a=s.index("    sync('latest_m398_tail_reference_board'");z=s.index('\nif __name__',a)
    s=s[:a]+'''    sync('latest_m398_tail_reference_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,reference_capture_pass=r.get('reference_capture_pass',False),candidate_numerical_pass=False,performance_pass=False),
         f'## M398 原末层参考捕获结果（2026-10-04）\\n\\nBuild0x4D333537，原rc{r["gate_return_code"]}，{r["status"]}，原SHA `{d}`。同固定159视频原完整778逻辑/781物理、全family/72KV/logits/视觉与判断核对，缺失末层12项NPY板端原子保存/身份核验，七DMA释放及稳定恢复。只完成原参考捕获，裁剪候选未执行、无新性能。下一步只做独立参考身份/生命周期闭合，再准备三个末批chain门禁；失败仅saved收集。')
    print(json.dumps(dict(status=r['status'],sha256=d,errors=r['errors'],capture=r.get('reference_capture'))))

'''+s[z:]
    atomic(HERE/'m398_collect.py',s.encode('utf-8'))
    print('M398_SAVED_COLLECTOR_GENERATED')

if __name__=='__main__':main()
