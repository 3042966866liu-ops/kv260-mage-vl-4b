"""Interpret the saved exact software reference, without repeating computation."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=board['latest_m417_reference_board'];p=ROOT/e['result'];assert sha(p)==e['sha256']
    r=json.loads(p.read_bytes())
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    passed=r['status']=='PASS_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE' and r['gate_return_code']==0
    v=dict(status='CLOSED_M417_LOCAL_EXACT_ARITHMETIC_PASS' if passed else 'CLOSED_M417_REFERENCE_LEVEL_FAIL',raw_sha256=e['sha256'],
        local_exact_arithmetic_screen_pass=passed,quality_metrics=r.get('quality_metrics'),boundary_residual_bf16=r.get('boundary_residual_bf16'),
        logical_reference_calls=r.get('logical_reference_calls'),physical_reference_attempts=r.get('physical_reference_attempts'),
        bindings_restored=r.get('bindings_restored'),visual_owner_closed=r.get('visual_owner_closed'),errors=r['errors'],
        semantic_quality_proven=False,PL_hardware_proven=False,performance_pass=False,formal_promotion_allowed=False,
        next='Same unchanged Build legal minimal transaction then layer13 single descriptor, chain and full isolated MLP net-time; [12,13] combination stays locked' if passed else 'Remain at exact software-reference failed level; no hardware or 24-layer expansion')
    out=BASE/'runs/M417-layer13-reference-closure-01/RESULT.json';atomic(out,encoded(v),immutable=True)
    report='# M417 精确参考裁决\n\n'+v['status']+'；原结果 SHA '+e['sha256']+'。\n\n'
    report+='复用M416原真实输入，完整资产/源码身份校验，保持原Siglip GELU、bias和T32重试，顺序FP32 group、FP16/FTZ及逆缩放。仅软件参考，不是PL实测或语义识别质量。\n\n'
    if r.get('quality_metrics'):
        report+='| 输出 | 相对L2误差 | 余弦相似度 | 最低token余弦 |\n|---|---:|---:|---:|\n'
        for k,x in r['quality_metrics'].items():report+=f'| {k} | {x["relative_l2"]*100:.6f}% | {x["cosine"]:.10f} | {x["min_token_cosine"]:.10f} |\n'
        if r.get('boundary_residual_bf16'):
            x=r['boundary_residual_bf16'];report+=f'| 残差原BF16边界 | {x["relative_l2"]*100:.6f}% | {x["cosine"]:.10f} | {x["min_token_cosine"]:.10f} |\n'
    report+='\n'+v['next']+'。完整MLP净耗时及释放/三记录通过之前，不扩大24层。没有新的提速或生产晋级结论。\n'
    if r['errors']:report+='\n'+json.dumps(r['errors'],ensure_ascii=False,indent=2)+'\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync('latest_m417_reference_closure',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],local_exact_arithmetic_screen_pass=passed,performance_pass=False),
        f'## M417 精确软件参考闭合（2026-10-06）\n\nSHA {sha(out)}；原 {e["sha256"]}保持。{v["status"]}，仅第13层原保存输入的软件数学参考；0新视觉/语言/Overlay/DMA/PL，非语义或性能PASS。{v["next"]}；精度与完整MLP净时间/释放/三记录均成立前不扩24层。')
    print('M417_CLOSURE_SYNC',sha(out),v['status'])
if __name__=='__main__':main()
