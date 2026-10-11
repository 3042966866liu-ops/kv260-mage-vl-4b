"""Record actual bounded controllers and autonomous follow-up, no tool launch."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
refs=[]
for name,file in [('M441-boundary-rtl-07','RESULT.json'),('M441-boundary-timeout-07','RESULT.json'),
                  ('M441-boundary-core-continuation-07','PREPARATION.json'),('M441-shell-continuation-07','PREPARATION.json'),
                  ('M441-board-support-checks-07','RESULT.json'),('M441-transfer-controls-checks-07','RESULT.json')]:
    p=BASE/'runs'/name/file;digest=sha(p);r=json.loads(p.read_bytes())
    for doc in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        assert digest in (ROOT/doc).read_text(encoding='utf-8-sig')
    refs.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=digest,status=r['status']))
progress=json.loads((BASE/'runs/M441-boundary-core-continuation-07/PROGRESS.json').read_bytes())
shell=json.loads((BASE/'runs/M441-shell-continuation-07/PROGRESS.json').read_bytes())
r=dict(status='ACTIVE_M441_AUTHORIZED_CONTINUOUS_EXECUTION07',build_id='0x4D343431',automation_id='m441',
  user_authorization='Continue autonomously until the user goal is completed; ask only for necessary password/login, never infer success.',
  prerequisites=refs,current_core_controller=progress,current_shell_controller=shell,
  package_builder=dict(path=(HERE/'m441_prepare_board_package07.py').relative_to(ROOT).as_posix(),sha256=sha(HERE/'m441_prepare_board_package07.py'),executed=False),
  board=False,performance_proven=False,production_changed=False,
  gates='Pressure and expected-timeout PASS; running core -> guarded one shell -> clean package -> COM3 authorization -> Build/descriptor/chain/W4 compare -> model/video only after prior PASS.',
  fail_policy='Preserve original evidence; stop enlargement at failed level. No constraint relaxation, repeated samples to PASS, active resource kill/free or unproven promotion.')
run=BASE/'runs/M441-continuous-execution-07';ev=run/'RESULT.json';atomic(ev,encoded(r),immutable=True)
report='''# M441 持续执行状态（2026-10-09）

本轮目标继续执行，尚未完成真实板端／完整请求性能裁决。

- 有界压力门禁已完整通过：327,680 个输出字、867,668 RTL 周期；覆盖 FIFO8192／FIFO34 满、背压、排空，四端口 4 KiB burst 拆分，以及最后 TLAST 停顿 128 拍后完成。
- 同编译快照的 200 周期超时负例通过：原工具返回 0，门禁按实际 Fatal／不完整结果返回 1，未把工具零返回当作 PASS。
- 上一轮尾拍测试台 READY 保持 0 的问题已由实际 VIP 驱动独立复现。只修测试台双侧握手，旧 FAIL 与受控停止记录保留，没有改候选 DUT。
- 核心同原 4.8 ns 约束的实现已实际启动。综合完成不等于布局布线时序通过；以原子保存的最终资源、setup／hold／pulse／route 结果为准。
- 等待核心 PASS 后执行一次独立整壳的有限控制器已启动。整壳仍需实际资源、时序、全树 HWH 和原日志错误核查；预算超限保留工具及映射，不自动终止。
- 真实完整 W4 gate_up／mlp_down 板端支持已准备，16 项离线安全／回收检查、6 项本地传输负例通过。使用已核对的同一真实权重窗口、非零 T32 输入与全输出参考；这不代替板端验证。
- 候选包构建器已准备，只有整壳及全部前级通过后才能执行。尚未打包、上传或访问 COM3。
- 后台跟进 m441 已启用，每 10 分钟检查实际证据并推进必要步骤；健康未变时安静，实质结果／失败／人工需求才通知。

板端比较提前固定为原 M357 对新 M441，两条完整 W4 长链，ABBA 与 BAAB 共八个 block，每条链每 block 一次 primer 与八次正式事务。先全输出与资源生命周期一致，再判断两个平衡组是否均有收益、候选 block 中位数是否与原版分离、时钟是否相同。没有净收益就关闭本版，不加样本求通过。

真实长链收益成立后才能扩展单层、固定文本与固定159-token视频数值，再进行测前冻结的整体请求性能。RTL 周期、协议压力 PASS 和离线 fake 检查均不称板端／请求提速。原 M437 视觉选择、单 parser、关闭 PS 预读及原输入合同保持；生产服务、稳定回滚、boot／DTB／CMA 均未改动。

必要密码／登录只检查一次并请求人工恢复；未获恢复不反复探测。输出解析临时数组建议仍排在 M441 闭合之后。
'''
for row in refs:report+='\n证据：`'+row['path']+'`，SHA `'+row['sha256']+'`，'+row['status']+'。\n'
atomic(run/'REPORT.md',report.encode('utf-8'),immutable=True)
sync('latest_m441_continuous_execution07',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False,automation_id='m441'),
 f'## M441 用户授权持续执行07（2026-10-09）\n\nSHA {sha(ev)}；已启动有限核心/整壳续行及m441自动跟进，完整有界压力与timeout闭合，真实W4支持离线检查完成。当前核心实现运行，整壳/包/板端未PASS；只在每级原证据SHA三同步后推进，密码必要时请求人工，不因健康运行终止目标。详细边界与停止规则见同目录REPORT.md，未声称硬件或请求提速。')
print(r['status'],sha(ev))
