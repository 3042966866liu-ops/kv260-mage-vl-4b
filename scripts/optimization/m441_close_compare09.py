"""Report the saved fixed comparison; never access the board."""
import json
import m351_workflow as w
from m441_host_io08 import atomic

def main():
    p=w.BASE/'runs/M441-compare-board-01/BOARD_RESULT.json';raw=p.read_bytes();r=json.loads(raw);sha=w.sha(p)
    assert sha=='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'
    assert all(sha in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    assert r['status']=='PASS_M441_COMPARE' and r['comparison']['all_cases_pass'] and r['safe_buffers_released'] and r['stable_restored']
    lines=['# M441 实板真实W4长链交错对照（2026-10-09）','','A Build0x4D333537；B Build0x4D343431；M9只用于安全恢复。原始证据SHA '+sha+'。','', '| 完整W4链 | A中位ms | B中位ms | 减少 | ABBA减少 | BAAB减少 |','|---|---:|---:|---:|---:|---:|']
    for name,c in r['comparison']['cases'].items():
        lines.append(f'| {name} | {c["original_median_ns"]/1e6:.6f} | {c["candidate_median_ns"]/1e6:.6f} | {100*c["gain_fraction"]:.4f}% | {100*c["balanced_blocks"][0]["gain_fraction"]:.4f}% | {100*c["balanced_blocks"][1]["gain_fraction"]:.4f}% |')
    lines+=['','固定ABBABAAB八块，每shape每块一primer及八正式样本，128正式事务全部保留；加16primer及1恢复事务，实际145次。全部输出逐位一致，两个平衡组都正，每条链所有B块中位均小于所有A块中位；实际PS时钟记录一致。','',r['comparison']['boundary'],'','上述是主机观测的完整链事务等待边界，非纯PL计算周期，不含权重暂存、输入打包、输出同步或数值哈希，不能称完整模型/视频请求减少72%。RTL零附加延迟模型27%左右与本次真实DDR链边界有不同条件，当前没有证据将差异定量归因给某一项。','','17组原所有者缓冲逆序释放，稳定M9恢复完成。旧Random02 FAIL、Random03重启中断及07监督失败全部保留；本次实板结果不覆盖旧裁决。下一步单层→固定文本→固定159视频全数值；通过后冻结完整请求交错性能。稳定服务未改变。','','冻结collector原闭合注释的日期2026-10-07是脚本模板日期；本次实际上板和结果解读为2026-10-09，原raw/collector均保留。']
    out=w.BASE/'runs/M441-compare-closure-09';atomic(out/'REPORT.md',('\n'.join(lines)+'\n').encode('utf-8'),immutable=True)
    v=dict(status='PASS_M441_BOARD_CHAIN_COMPARISON_ONLY',build_id='0x4D343431',raw_sha256=sha,comparison=r['comparison'],board_chain_performance_pass=True,complete_request_performance_proven=False,promotion=False,report_sha256=w.sha(out/'REPORT.md'))
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m441_chain_performance_closure09',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,raw_sha256=sha),f'## M441 真实长链性能解读09（2026-10-09）\n\n原M357→M441：gate_up82.683305→23.118739ms减少72.0394%，down41.465990→11.693419ms减少71.8000%；固定八块全部样本、ABBA/BAAB分别正且所有B块快于所有A块，同clock/完整输出/释放/恢复PASS。仅主机链事务边界，非完整请求提速或晋级。原raw SHA {sha}；解读SHA {digest}。下一步单层数值；稳定服务不改。')
    notified=w.BASE/'runs/M441-completion-notification-08/NOTIFIED.json';n=json.loads(notified.read_bytes());n['stages']['board_chain_comparison_pass09']=dict(evidence=p.relative_to(w.ROOT).as_posix(),sha256=sha,closure_sha256=digest)
    atomic(notified,w.encoded(n))
    print(v['status'],digest)

if __name__=='__main__':main()
