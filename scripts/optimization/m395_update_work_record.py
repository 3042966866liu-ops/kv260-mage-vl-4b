"""Publish the completed SiLU experiment using synchronized saved evidence."""
import json
from m351_workflow import ROOT,BASE,sha,atomic

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));e=b['latest_m395_silu_performance_closure'];p=ROOT/e['result']
    assert sha(p)==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    final=json.loads(p.read_text(encoding='utf-8'))
    keys=['latest_m390_gate_up_capture_board','latest_m391_silu_component_board','latest_m392_silu_layer_board','latest_m393_silu_text_board','latest_m394_silu_video_board','latest_m395_silu_performance_board']
    # Existing historical key spellings are resolved by exact result directory.
    directories=['M390-gate-up-capture-board-01','M391-silu-component-board-01','M392-silu-layer-board-01','M393-silu-text-board-01','M394-silu-video-board-01','M395-silu-performance-board-01']
    rows=[]
    for stage,directory in zip(range(390,396),directories):
        file=BASE/'runs'/directory/'BOARD_RESULT.json';h=sha(file)
        assert any(v.get('sha256')==h for v in b.values() if isinstance(v,dict))
        assert all(h in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        r=json.loads(file.read_text(encoding='utf-8'));rows.append((stage,file,h,r['status']))
    report=(p.parent/'REPORT.md').read_text(encoding='utf-8')
    report+='\n证据索引（原始文件均通过完整SHA和三份记录同步）：\n\n| 阶段 | 状态 | 原始结果 | SHA-256 |\n| --- | --- | --- | --- |\n'
    for stage,file,h,status in rows:report+=f'| M{stage} | {status} | [BOARD_RESULT]({file.as_posix()}) | `{h}` |\n'
    report+='\nM389为离线默认关闭组件与原源码/旧尝试核查；M390从原视频第一层捕获真实gate/up，不执行SiLU以后计算。M391只做CPU组件。M392为单层重复固定文本embedding，M393为原30-token文本，M394才是原159-token视频。所有门禁的计时边界不同，诊断耗时不能用于跨级比较。\n\n离线拒绝：M392准备01错误推断旧远程目录，上传前拒绝，保留旧包和拒绝SHA `6271a1be1de132d4cf679713cfaeab78f9c4a3e001108485de80562e414e06ed`；新02按实际旧控制器修正后验证。没有硬件重跑试目录。\n'
    dest=ROOT/'KV260_SiLU工作缓冲验证记录_2026-10-04.md';atomic(dest,report.encode('utf-8'),immutable=True)
    old=ROOT/'KV260_本轮优化完整工作记录_2026-10-01.md';text=old.read_text(encoding='utf-8-sig');marker='<!-- M389_M395_SILU_COMPLETED -->'
    if marker not in text:
        extra=f'\n\n{marker}\n## 2026-10-04补充：M389—M395 SiLU工作缓冲\n\n真实159视频输入CPU组件平均112.395ms→100.617ms，约10.48%算子延迟下降，逐位一致；单层、原30文本、原159视频数值/生命周期门禁全部通过。同并行Build0x4D333537/原单parser，PS预读和双parser关闭，新增普通工作缓冲5.900390625MiB，0新DMA。\n\n完整请求裁决：**{final["status"]}**；独立于此前硬件约40.81%收益，不改变旧裁决或服务。全部八次原请求计时、ABBA/BAAB、组内波动、实际读盘与明确下一步见[本轮详细记录]({dest.as_posix()})。原始结果、闭合SHA和严格判据保留。\n'
        atomic(old,(text.rstrip()+extra).encode('utf-8'))
    print(json.dumps(dict(report=str(dest),report_sha256=sha(dest),work_record_sha256=sha(old),status=final['status'])))

if __name__=='__main__':main()
