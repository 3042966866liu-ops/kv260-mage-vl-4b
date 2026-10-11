"""Adjudicate already collected fixed-video waits; never execute a board gate."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m371_profile_summary import unpack
from m375_wait_validation import validate

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8-sig'))
    row=board['latest_m375_video_wait_board'];path=ROOT/row['result']
    if sha(path)!=row['sha256'] or not all(row['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md')):
        raise RuntimeError('Raw evidence/triad differs; recover only')
    raw=json.loads(path.read_text(encoding='utf-8'))
    out=BASE/'runs/M375-video-wait-closure-01'
    if out.exists():raise RuntimeError('Immutable interpretation already exists')
    passed=raw['status']=='PASS_M375_FIXED_VIDEO_WAIT'
    summary=None;answers=None
    if passed:
        if raw['gate_return_code'] or not raw['numerical_pass'] or raw['unsafe_buffers_retained'] or not raw['safe_buffers_released'] or not raw['stable_overlay_reloaded']:
            raise RuntimeError('Incomplete observed request PASS')
        if raw['fpga_transactions_total']!=782 or raw.get('ps_prefetch_enabled') is not False or not raw['wait_bindings_restored']:
            raise RuntimeError('Observation/request scope escaped')
        contract=json.loads((BASE/'candidates/M375-video-future-wait-01/WAIT_CONTRACT.json').read_text(encoding='utf-8'))['families']
        report,trace_raw=unpack(raw['packed_wait_trace'])
        summary=validate(report,contract)
        if summary!=raw['video_wait_summary']:raise RuntimeError('Wait summary changed')
        total=summary['summary']['parse']['condition_wait_s']
        family=summary['by_family'];gate=family['gate_up']['actual_wait_s']
        reuse=summary['parse_reuse_wait_s'];tail=summary['parse_tail_wait_s']
        answers=dict(parse_actual_wait_s=total,gate_up_wait_s=gate,
            gate_up_share_percent=100*gate/total if total else 0,
            largest_family=max(family,key=lambda k:family[k]['actual_wait_s']),
            reuse_wait_s=reuse,tail_wait_s=tail,
            reuse_share_percent=100*reuse/total if total else 0,
            tail_share_percent=100*tail/total if total else 0,
            parse_wait_percent_of_this_observed_prefill=100*total/summary['prefill_instrumented_s'])
        text=(f'# M375 原固定159-token视频窄等待结果\n\n解析实际等待累计 **{total:.6f}s**；gate_up **{gate:.6f}s**，占 **{answers["gate_up_share_percent"]:.2f}%**。最大等待family为 `{answers["largest_family"]}`。\n\n'
              f'缓冲复用等待 **{reuse:.6f}s（{answers["reuse_share_percent"]:.2f}%）**；family收尾等待 **{tail:.6f}s（{answers["tail_share_percent"]:.2f}%）**。\n\n'
              '| family | 解析实际等待/s | 复用/s | 收尾/s |\n|---|---:|---:|---:|\n')
        for name,value in family.items():
            text+=f'|{name}|{value["actual_wait_s"]:.6f}|{value["reuse_wait_s"]:.6f}|{value["tail_wait_s"]:.6f}|\n'
        text+=(f'\n原候选Build0x4D333537，778逻辑/781物理另1合法最小。原输入、视觉特征、logits、72KV和最终判断按原参考完整核对；七缓冲安全释放并重载稳定Overlay。pack实际等待{summary["summary"]["pack"]["condition_wait_s"]:.6f}s。\n\n'
              'Condition.wait含唤醒调度且嵌套于result墙钟；同步重试解析、LM head及其他同步点不在此钩子覆盖范围。本次一次请求带观察开销，不能套到M369轻量Prefill或算新提速，不与worker累计时间相加。\n\n'
              '下一步只根据暴露等待和复用/收尾分布判断一个具体调度方案是否值得做；若提出方案，先核对所有权、重试、输出槽复用和安全退出，再隔离候选做数值与完整请求验证。尚未自动修改调度或开启PS预读；不重复单层、大画像或旧八次性能。\n')
    else:
        if raw['gate_return_code']!=1 or not raw['errors']:raise RuntimeError('Invalid failed result')
        text='# M375 原视频窄等待未通过\n\n'+json.dumps(raw['errors'],ensure_ascii=False,indent=2)+'\n\n仅闭合已保存结果，不解读不完整等待、不重跑视频补收集。下一步留在当前失败级。\n'
    result=dict(status='PASS_FIXED_VIDEO_ACTUAL_WAIT_CLOSED' if passed else 'FAIL_FIXED_VIDEO_WAIT_CLOSED',
        build_id='0x4D333537',raw_sha256=row['sha256'],answers=answers,summary=summary,
        errors=raw['errors'],numerical_pass=passed,performance_pass=False,production_promotion=False,
        next_step='Judge one scheduling design from exposed waits; no automatic implementation' if passed else 'Diagnose current failure only; no hardware rerun for collection')
    atomic(out/'RESULT.json',encoded(result),immutable=True);digest=sha(out/'RESULT.json')
    text+='\n原结果SHA：`'+row['sha256']+'`；闭合SHA：`'+digest+'`。\n'
    atomic(out/'REPORT.md',text.encode('utf-8'),immutable=True)
    description=json.dumps(answers,ensure_ascii=False) if answers else json.dumps(raw['errors'],ensure_ascii=False)
    sync('latest_m375_video_wait_closure',dict(status=result['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,raw_sha256=row['sha256'],numerical_pass=passed,performance_pass=False),
        f'## M375 原固定视频实际等待裁决（2026-10-03）\n\nBuild0x4D333537，{result["status"]}；{description}。原SHA {row["sha256"]}，闭合SHA {digest}。只一次原视频窄观察，原数值/事务/释放按门禁，非新增性能；同步重试/head未覆盖、Condition.wait含唤醒调度。下一步据暴露等待判断一个具体调度改动，不自动改源码/启预取/晋级，不重复单层、大画像或旧八次性能。')
    print(json.dumps(dict(status=result['status'],sha256=digest,answers=answers,errors=raw['errors']),ensure_ascii=False))

if __name__=='__main__':main()
