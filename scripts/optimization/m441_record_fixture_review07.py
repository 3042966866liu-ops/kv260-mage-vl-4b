from m351_workflow import ROOT,BASE,atomic,sha,encoded
import json
p=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'
s=p.read_text(encoding='utf-8-sig')
marker='## M441 尾字压力钩子与实际VIP不匹配（2026-10-09）'
assert marker not in s
note=marker+'''

原压力06原始FAIL SHA `4f747b70e4ddb61b79d14dc782297b746d3396f2a9a1c51bca11060707a0eeb9`；四端口完整10880权重返回/MAC2560及队列排空，但最后输出停在327679。tail已打印128拍release，原vendor `svr_slave_driver.get_and_drive()`一次设置READY=1后等待握手；对logic变量force/release导致READY保留0。此前明确fake小组件每拍重写READY，未覆盖真实driver行为，不能据其PASS证明完整VIP兼容。

实际vendor driver/config/transfer/interface原字节小组件13 SHA `cc64a9e27602d4f581bf953545423a0417f3575aacb69e609c214c52348bfe1e`：原release复现words327679/ready0/held128；独立握手interposer在0和8请求延迟均完整接收。component11声明使用顺序编译FAIL、12直接连续调用跳过NBA调度边界FAIL均保留；13只调整fake请求调用时机，实际vendor代码不改。不能把fake producer小组件当作DUT门禁。

原现场先原子保存；独立提前停止协议只核对并停止精确PID/出生时间/完整工作区exe的本地xsim kernel，termination code7，证据SHA `2164fd49f58a71ed8684bfc5bbde698d6215a3b85406245a41b93a409d66810b`。这是显式外部本地fixture故障干预，不是预算超时或板端kill。原controller自身process_killed=False仅指它自身未kill，不能抹去外部干预；launcher与原gate_rc仍为0，严格collector返回1且FAIL，有限控制器停本级，0timeout/core/shell/COM3/DMA/板端。

防复发：尾停顿使用测试台握手interposer同时阻止DUT READY和VIP VALID的接收，保留真实VIP一次READY赋值和等待过程，不force/release接收变量，不强制DUT数据；实际VIP小组件先验证，声明放到首次使用之前。保留最大fixture/FIFO34与8192/完整字数/终态要求及原4M/4h，不加预算掩盖入口卡住。源/协议修复另立07，同级执行一次，旧FAIL及提前停止记录不改。
'''
title,rest=s.split('\n',1);atomic(p,(title+'\n\n'+note+'\n'+rest.lstrip('\n')).encode('utf-8'))
ev=BASE/'runs/M441-fixture-review-07/RESULT.json'
atomic(ev,encoded(dict(status='RECORDED_M441_TEST_HARNESS_FAILURE_AND_PREVENTION',review_sha256=sha(p),board=False)),immutable=True)
print('review saved',sha(p))
