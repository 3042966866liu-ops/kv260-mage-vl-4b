"""Close the saved layer13 PS capture without repeating board computation."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=board['latest_m416_local_mlp_board04'];p=ROOT/e['result']
    assert sha(p)==e['sha256']
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(p.read_bytes())
    passed=r['status']=='PASS_M416_PS_LOCAL_MLP_CAPTURE_A8_SCREEN' and r['gate_return_code']==0
    if passed:
        from m416_workflow import decode
        import base64
        raw=p.read_bytes();parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        stream='M416_RESULT_SHA256='+sha(p)+'\n'+''.join(f'M416_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(x).decode('ascii')+'\n' for i,x in enumerate(parts))+'M416_DONE gate_rc=0 export_rc=0\n'
        assert decode(stream)[2]==r
    value=dict(status='CLOSED_M416_LAYER13_LOCAL_A8_PASS_NOT_PL' if passed else 'CLOSED_M416_PS_CAPTURE_LEVEL_FAIL',
               raw_sha256=e['sha256'],selected_layer=13,original_visual=r.get('visual'),
               original_MLP_replay_bit_exact=r.get('capture_exact',False),capture_manifest=r.get('capture_manifest'),
               quality_metrics=r.get('quality_metrics'),component_isolation=r.get('component_isolation'),
               bindings_restored=r.get('bindings_restored'),visual_owner_closed=r.get('visual_owner_closed'),errors=r['errors'],
               overlay_loads=0,DMA_allocations=0,PL_transactions=0,language_forward_calls=0,
               PL_arithmetic_proven=False,combined_12_13_proven=False,semantic_quality_proven=False,performance_pass=False,
               formal_promotion_allowed=False,
               next='Prepare exact ordered FP32/FP16/FTZ software oracle from these six saved tensors; then descriptor/chain/full isolated layer13 MLP. Combination [12,13] remains locked.' if passed else 'Stay at PS capture failed level; inspect saved evidence, no PL or combination.')
    out=BASE/'runs/M416-layer13-PS-closure-01/RESULT.json'
    atomic(out,encoded(value),immutable=True)
    report='# M416 第13层原输入捕获与局部A8筛选\n\n'+value['status']+'。原始结果 SHA：'+e['sha256']+'。\n\n'
    if passed:
        report+='原固定末帧两视图完成一次原版视觉，最终特征与冻结原版逐位一致。第13层六张量已保存，原MLP局部回放逐位一致；组件在独立进程执行，父进程Torch状态保持。\n\n| 比较 | 相对L2误差 | 余弦相似度 | 最低token余弦 |\n|---|---:|---:|---:|\n'
        for k,v in r['quality_metrics'].items():
            report+=f'| {k} | {v["relative_l2"]*100:.6f}% | {v["cosine"]:.10f} | {v["min_token_cosine"]:.10f} |\n'
        report+='\n通过的是原CPU数学中的A8 QDQ局部拒绝筛选，尚未包含PL的FP16/FTZ误差，不是第12+13层组合、语义识别质量或性能证明。原hooks已恢复，视觉owner已释放。\n'
    else: report+='\n失败记录：\n```json\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n```\n'
    report+='\n本步无Overlay、DMA、FPGA或语言事务。诊断计时不用于提速结论。下一步：'+value['next']+'\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m416_local_mlp_closure',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],local_A8_screen_pass=passed,performance_pass=False),
         f'## M416 第13层原输入局部A8筛选闭合（2026-10-06）\n\nSHA {sha(out)}；原raw {e["sha256"]}；{value["status"]}。原视觉SHA及原MLP逐位回放以raw为准，保存六张量；0Overlay/DMA/PL/语言，原hooks和PS owner释放以raw为准。只涉及第13层原输入，未证明12+13组合、PL FP16/FTZ、语义质量或性能；诊断时间非性能。{value["next"]}')
    print('M416_CAPTURE_CLOSURE_SYNC',sha(out),value['status'])

if __name__=='__main__':main()
