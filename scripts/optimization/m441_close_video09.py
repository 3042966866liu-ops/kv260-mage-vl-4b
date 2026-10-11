"""Close the already recovered complete video; no board execution."""
import json
import m351_workflow as w
from m441_host_io08 import atomic
from m441_video_collect09 import check

def main():
    p=w.BASE/'runs/M441-fixed-video-board-09/BOARD_RESULT.json'
    r=check(json.loads(p.read_bytes()));d=w.sha(p)
    assert r['status']=='PASS_M441V_INTEGRATED_VIDEO_NUMERICAL'
    assert all(d in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    out=w.BASE/'runs/M441-fixed-video-closure-09'
    report=f'''# M441 固定159视频完整数值闭合（2026-10-09）

Build0x4D343431，原raw SHA {d}，1326个900B原字节分块；原gate/export/controller rc0。保持M437后11层视觉MLP、单parser、PS预读关闭、末帧两个视图、原159-token提示和完整词表。

完整24层视觉边界、286次视觉输入/输出、98×2560特征、154语言family、72份K/V、151936 logits、重试和最终判定逐位核对已接受的M428 sample1。778逻辑、781语言物理（3保护重试）、286视觉物理以及1次合法最小事务，合计1068。Token15／文本0／ABSENT，score0.4455295350395727。复用已保存原版参考，未重新跑CPU视觉A。

七块原DMA缓冲由原owner安全释放，稳定Overlay恢复且未提交恢复事务；活动DMA或worker没有被kill。固定64MiB CMA拒绝已取消，没有新增DMA、PS slot或CMA bank，没有清缓存、GC/trim、温度读取或生产修改。

422.736秒是含资产校验、逐family数值哈希及观察的诊断耗时，不能用作正常请求性能。下一项只冻结并执行一个完整请求对照：A原M357与B新M441都使用同一M437后11层视觉路径，4次ABBA预处理后8次ABBABAAB正式请求，保留自然I/O及全部样本。核切换和合法最小证明在计时之外，原请求边界内包含视觉、权重准备、语言、解析和LM head。没有稳定净收益则关闭本版，不改稳定服务。
'''
    atomic(out/'REPORT.md',report.encode('utf-8'),immutable=True)
    v=dict(status='PASS_M441_FIXED159_VIDEO_CLOSED',build_id=r['build_id'],raw_sha256=d,language_logical=778,language_physical=781,visual_physical=286,total_physical=1068,all_accepted_reference_fields_exact=True,seven_owned_buffers_released=True,performance_pass=False,promotion=False,report_sha256=w.sha(out/'REPORT.md'))
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);sha=w.sha(out/'RESULT.json')
    w.sync('latest_m441_fixed_video_closure',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=sha,raw_sha256=d),f'## M441 固定159视频解读09（2026-10-09）\n\nraw {d}，1326原字节块，完整24视觉边界/286视觉/778语言逻辑/781语言物理/72KV/151936logits及判定逐位既有接受参考，合计1068事务。七owner释放及稳定恢复；诊断计时不是请求性能。闭合SHA {sha}。下一步冻结原M357与新M441同M437视觉路径的完整请求4＋8自然I/O协议，不改生产。')
    npath=w.BASE/'runs/M441-completion-notification-08/NOTIFIED.json';n=json.loads(npath.read_bytes());n['stages']['fixed_video_pass09']=dict(evidence=p.relative_to(w.ROOT).as_posix(),sha256=d,closure_sha256=sha);atomic(npath,w.encoded(n))
    print(v['status'],d,sha)

if __name__=='__main__':main()
