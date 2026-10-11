"""Interpret immutable collected PS screen; no board command or computation."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=b['latest_m408_local_mlp_board04'];p=ROOT/e['result']
    assert sha(p)==e['sha256']=='8b15ddab005dfe1f8533ffd96b592739571f3719ae52a2cf53982d2d205a9c05'
    r=json.loads(p.read_bytes())
    assert r['gate_return_code']==0 and r['capture_exact'] and r['bindings_restored'] and r['visual_owner_closed']
    for n in ('CURRENT_STATE.md','docsMILESTONES.md'):assert e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig')
    v=dict(status='PASS_M408_LOCAL_A8_SCREEN_CLOSED_NOT_PL',raw_sha256=e['sha256'],
        capture_manifest=r['capture_manifest'],quality_metrics=r['quality_metrics'],
        visual_sha256=r['visual']['sha256'],original_MLP_replay_bit_exact=r['capture_exact'],
        bindings_restored=True,visual_owner_closed=True,PL_arithmetic_proven=False,
        semantic_quality_proven=False,performance_pass=False,formal_promotion_allowed=False,
        next='Same retained input, exact ordered FP32 group / FP16 / FTZ software oracle; then descriptor and chain before complete isolated MLP timing. No 24-layer expansion.',
        preserved_rejected_revisions=[b['latest_m408_local_mlp_board'+s]['sha256'] for s in ('','02','03')])
    out=BASE/'runs/M408-local-MLP-A8-closure-04/RESULT.json';atomic(out,encoded(v),immutable=True)
    text='# M408 局部A8筛选闭合\n\n'
    text+='真实第12层392行输入，原完整视觉SHA保持，原MLP局部回放逐位一致。原捕获/计算始终保持单batch三维，只保存NPY时去掉batch维。\n\n'
    text+='| 比较 | 相对L2误差 | 余弦相似度 |\n|---|---:|---:|\n'
    for k,x in r['quality_metrics'].items():text+=f'| {k} | {x["relative_l2"]*100:.6f}% | {x["cosine"]:.10f} |\n'
    text+='\n全部通过预定局部阈值，但仅原FP32 CPU数学中的A8 QDQ拒绝筛选；未证明PL FP16/FTZ误差、语义识别质量、24层或提速。没有Overlay/DMA/语言事务；原hooks恢复、视觉owner释放。\n\n原01/02/03插桩失败与原字节保留。下一步只使用已留存输入，准备精确PL数学软件参考，精度通过后按descriptor/chain顺序上板。\n'
    atomic(out.with_name('REPORT.md'),text.encode('utf-8'),immutable=True)
    sync('latest_m408_local_mlp_closure04',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),raw_sha256=e['sha256'],performance_pass=False),
        f'## M408 局部A8筛选闭合（2026-10-05）\n\nSHA {sha(out)}；原PASS {e["sha256"]}保持，原视觉SHA和MLP逐位回放一致，fc2相对L2 1.158217%、残差0.765758%，局部阈值通过。原hooks和PS owner释放，0Overlay/DMA/语言；不是PL FP16/FTZ、语义或性能PASS。只准备同已保存输入精确软件参考，之后descriptor/chain与完整MLP净时间；不扩24层。')
    print('M408_CLOSURE_SYNC',sha(out))
if __name__=='__main__':main()
