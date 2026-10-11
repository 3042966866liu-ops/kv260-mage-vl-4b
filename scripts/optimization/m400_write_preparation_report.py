"""Write the current offline preparation report; never opens COM3."""
import json
from m351_workflow import ROOT,BASE,sha,atomic


def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    keys=('latest_m400_tail_layer_preparation','latest_m400_tail_layer_support','latest_m400_authorization_precheck')
    rows={}
    for key in keys:
        e=board[key];assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        rows[key]=(e,json.loads((ROOT/e['result']).read_text(encoding='utf-8')))
    prep,pr=rows[keys[0]];support,su=rows[keys[1]];auth,au=rows[keys[2]]
    assert prep['manifest_sha256']==support['manifest_sha256']
    assert not au['board_gate_started'] and au['sudo_return_code']==1
    report=f'''# M400 末层组合门禁准备

下一项验证将从 M398 保存的真实末层输入开始，重算第35层：159个 token 的 QKV、RoPE、Attention 和完整 K/V保持；Attention之后，后三个投影仅处理原最后T32批31行。前级 M399 三个独立末批chain已通过并闭合。

| 项目 | 本级范围 |
|---|---|
| 输入 | 原末层完整159×2560 residual_full |
| 完整计算 | QKV五个原T32批、全159 Attention、159×8×128的K和V |
| 末批计算 | attention_out、gate_up、mlp_down各31行 |
| 数值检查 | 完整QKV/KV SHA；Attention、末批投影输入输出、hidden和最终norm逐位一致 |
| 参考身份 | 11项NPY使用前后文件SHA、tensor SHA、类型/尺寸和七字段文件身份 |
| 调用 | 8逻辑/8层物理，加同Overlay最小事务共9次 |
| 原权重暂存 | 53,624,832字节；宏计数81,920,000，原合同单位，不是FLOPs |

原 M241 的单层计算由冻结源码提取，剥离尾批选择并恢复原循环范围后AST严格相同。原M238打包/解析、量化档位和保护重试保持；本输入保留的原批次没有重试，门禁核对全部8条原选档记录。

完整runtime、原七块DMA驻留并封锁新增DMA。使用已授权独立诊断规则：普通RSS增长上限1GiB，普通可用余量64MiB；原生产64MiB CMA准入不变。关闭PS预读、双parser和SiLU工作缓冲，原单parser及并行Build0x4D333537保持。异常保留scope/映射/原DMA和进程，不强杀后释放；成功核对scope弱引用消失、原family绑定恢复、七DMA安全逆序释放和稳定Overlay恢复。

离线结果：{su['component_checks']}项实际冻结loop、原NumPy数学和真实尺寸NPY检查；{su['actual_gate_region_checks']}项实际生成调用区检查；{su['collector_negative_checks']}项收集负例；{su['actual_assembly_checks']}项实际组装检查和PS List/SelfTest通过。Linear、DMA和内存为明确替身，合成收集元数据不构成板端数值。相同SHA通过检查复用，没有重跑旧硬件。

包共{pr['file_count']}载荷、{pr['total_bytes']}字节；递归missing=0，Python3.10语法通过，匹配硬件47项SHA证据复用。组装旧远程根由M399实际控制/传输证明，不由本地版本号推断。

manifest SHA：`{prep['manifest_sha256']}`。

准备结果SHA：`{prep['sha256']}`。控制/回收支持SHA：`{support['sha256']}`。

当前阻塞：COM3已确认在shell，但上传前sudo返回1，需要人工sudo-v续期。检查原字节独立保存，证据SHA `{auth['sha256']}`；尚未上传或执行M400，没有本级Overlay/模型/FPGA事务。原M399 PASS、已有硬件40.81%性能结论、生产准入及稳定回滚保持。

收到续期后只进行一次受控上传/逐SHA核验和本级单层门禁。已有run日志或结果只能收集；失败留在单层级，收集失败只回收原字节。全部数值和生命周期通过、原SHA及BOARD/CURRENT_STATE/docsMILESTONES同步后，才准备固定文本；完整视频候选和新性能尚未解锁。
'''
    out=BASE/'runs/M400-tail-layer-preparation-01/REPORT.md'
    atomic(out,report.encode('utf-8'),immutable=True)
    print(json.dumps(dict(report=out.relative_to(ROOT).as_posix(),sha256=sha(out))))


if __name__=='__main__':main()
