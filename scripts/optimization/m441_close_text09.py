"""Close immutable original fixed-text bytes; repair mislabeled host index keys."""
import json
import m351_workflow as w
from m441_host_io08 import atomic

def main():
    p=w.BASE/'runs/M441-fixed-text-board-09/BOARD_RESULT.json';r=json.loads(p.read_bytes());d=w.sha(p)
    assert r['status']=='PASS_M441T_FIXED_TEXT_DIAGNOSTIC' and all(r['exact_comparison'].values())
    assert r['safe_buffers_released'] and not r['unsafe_buffers_retained'] and len(r['released_buffers'])==7
    assert all(d in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    out=w.BASE/'runs/M441-fixed-text-closure-09';x=r['layer_result']
    report=f'''# M441 固定文本完整数值闭合（2026-10-09）

Build0x4D343431；原raw SHA {d}。1228个900B原字节分块严格回收，原gate/export/controller rc0。

原30token、36层、154 family、151936 FP32 logits和72份K/V及全部缩放重试记录逐位相同。162逻辑、165语言物理（3保护重试）、另1同Overlay合法最小事务；LM head的8次物理提交完整观察。

完整runtime七原DMA已分配后封锁新增分配；原owner各释放一次，末态AP_CTRL4、两DMASR4098，无错；稳定Overlay恢复后无事务，DMASR0仅未提交生命周期。没有固定64MiB CMA拒绝、清缓存、GC/trim、新PS槽或CMAbank。源码/head AST核对发生在Overlay/分配之前。

这轮数值诊断耗时含校验、哈希及导出，不证明视频或请求性能。下一步一次固定159视频：维持M437后11层视觉MLP、原单parser、PS预读关闭，原输入及量化合同；复用既有接受的完整视觉/语言参考。

主机准备脚本复制时，text支持/传输同步索引仍沿用single_layer键；原raw和文档事实不受影响。保留旧键的完整before副本，恢复single_layer原项并增设fixed_text对应项；未重跑硬件。
'''
    atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True)
    boardpath=w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    atomic(out/'BOARD_BEFORE_INDEX_REPAIR.json',boardpath.read_bytes(),immutable=True)
    board=json.loads(boardpath.read_bytes())
    for level in ('support','transfer'):
        board['latest_m441_fixed_text_'+level]=board['latest_m441_single_layer_'+level]
        original=w.BASE/f'runs/M441-single-layer-{level}-09/RESULT.json';o=json.loads(original.read_bytes())
        board['latest_m441_single_layer_'+level]=dict(status=o['status'],result=original.relative_to(w.ROOT).as_posix(),sha256=w.sha(original),manifest_sha256=o['manifest_sha256'])
    atomic(boardpath,w.encoded(board))
    v=dict(status='PASS_M441_FIXED_TEXT_CLOSED',build_id=r['build_id'],raw_sha256=d,logical_calls=162,language_physical_calls=165,total_physical_calls=r['fpga_transactions'],all_reference_fields_exact=True,seven_owned_buffers_released=True,video_proven=False,performance_pass=False,promotion=False,report_sha256=w.sha(out/'REPORT.md'),host_index_repaired_without_board_rerun=True)
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);sha=w.sha(out/'RESULT.json')
    w.sync('latest_m441_fixed_text_closure',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=sha,raw_sha256=d),f'## M441 固定文本解读09（2026-10-09）\n\nraw {d}，1228原字节块、162逻辑/165语言物理+1合法事务、3重试、151936logits/72KV全部逐位相同、七owner释放及稳定恢复。闭合SHA {sha}。主机text支持/传输索引误沿用layer键已独立保存before并修复，无硬件重跑。下一步M437后11层视觉同输入固定159视频数值，不称性能或晋级。')
    npath=w.BASE/'runs/M441-completion-notification-08/NOTIFIED.json';n=json.loads(npath.read_bytes());n['stages']['fixed_text_pass09']=dict(evidence=p.relative_to(w.ROOT).as_posix(),sha256=d,closure_sha256=sha);atomic(npath,w.encoded(n))
    print(v['status'],d,sha)

if __name__=='__main__':main()
