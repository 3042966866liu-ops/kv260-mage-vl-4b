"""Repository report from synchronized evidence; no board access."""
import json
from m351_workflow import ROOT,BASE,sha,atomic

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    entries={key:b[key] for key in ('latest_m398_tail_reference_closure','latest_m399_tail_chain_preparation','latest_m399_tail_chain_support','latest_m399_authorization_precheck')}
    for e in entries.values():
        assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    prep=json.loads((ROOT/entries['latest_m399_tail_chain_preparation']['result']).read_text(encoding='utf-8'))
    support=json.loads((ROOT/entries['latest_m399_tail_chain_support']['result']).read_text(encoding='utf-8'))
    auth=json.loads((ROOT/entries['latest_m399_authorization_precheck']['result']).read_text(encoding='utf-8'))
    assert support['collector_negative_checks']==85 and auth['sudo_return_code']==1
    report='''# M399 三个末批chain：准备完成，尚未上板

当前候选是：最后语言层35完整Q/K/V、RoPE和Attention完成后，`attention_out`、`gate_up`、`mlp_down`仅处理原最后T32批的31行。先核对三个独立chain，随后才单层、固定文本、固定159视频和完整请求性能。

M398已完成原路径的缺失参考捕获与闭合：原159视频全部输出、151936个logits和72份K/V与已有参考逐位一致，原778逻辑/781模型物理（3重试），七DMA安全释放并恢复稳定Overlay；12项参考NPY共10249216B。该结果是原参考，不能当作裁剪候选正确或更快的证明。

| chain | 输入FP32尺寸 | 核对输出 | chain序号 | 宏计数（原合同单位） | 原权重暂存B |
|---|---|---|---:|---:|---:|
| attention_out | 31×4096 | 31×2560完整o_proj | 151 | 5242880 | 5570560 |
| gate_up | 31×2560 | gate/up各31×9728 | 152 | 24903680 | 26468352 |
| mlp_down | 31×9728 | 31×2560完整down_proj | 153 | 12451840 | 13230080 |

前三个独立chain复用原M238打包、权重暂存、解析与重试算法，输入及四项输出来自M398的七个NPY。使用前后检查原raw SHA、完整文件SHA、形状/FP32/tensor SHA、设备/ inode/大小/mtime/ctime/权限/链接数。读取使用只读mmap；完整runtime驻留，七块DMA之外的PYNQ分配被封锁。解析worker保持1，PS预读、双parser、SiLU workspace关闭。

预期3逻辑/3物理chain，含同Overlay合法最小事务共4次；宏计数须为42598400，权重暂存45268992B。宏计数沿用原合同单位，不是FLOPs。若重试、事务数量、字节、任何完整输出或身份不同，拒绝本级；失败owner/参考map和原DMA/进程保留，禁止kill后释放。成功则关闭map、移除owner引用、逆序释放七DMA并恢复稳定Overlay。原生产64MiB准入及boot/DTB/CMA/服务/回滚保持。

离线检查通过：6项组件（真实尺寸自有NPY，Linear/DMA/内存明确替身）、4项实际生成gate region、85项回收负例、8项实际assembly，PS List/SelfTest、Python3.10语法及递归依赖missing0。47项同SHA硬件证据复用；没有新电路改动。本次还收紧了宏计数校验：两份计数相等但都写成100也会拒绝。冻结包未变，既有组件及硬件没有重跑。

## 目前的阻塞

COM3已确认shell，但上传前`sudo -n true`原rc1。M399尚未上传、未加载Overlay、未提交候选chain。失败UART原字节独立保存；人工续期后只检查一次，再执行manifest-first/900B传输、板端全部SHA、root bash-n，然后显式一次Run。已有run日志或result时只能Collect，不能重执行。

## 证据

'''
    for key,e in entries.items():report+=f"- {key}: `{e['result']}`，SHA `{e['sha256']}`。\n"
    report+=f"\n冻结包manifest SHA `{prep['manifest_sha256']}`，{prep['file_count']}个载荷、{prep['total_bytes']}B。\n"
    report+='\n下一步：仅三个末31 chain门禁。通过并同步三记录后才准备单层组合；尚无本候选完整数值或性能PASS，原并行硬件约40.81%收益结论保持。\n'
    out=BASE/'runs/M399-tail-chain-preparation-01/REPORT.md';atomic(out,report.encode('utf-8'),immutable=True)
    print('M399_PREPARATION_REPORT',sha(out))

if __name__=='__main__':main()
