"""Freeze temperature-free protocol before collecting any request samples."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    old=board['latest_m424_warm_protocol'];assert sha(ROOT/old['result'])==old['sha256']
    prior=ROOT/old['result'];protocol=prior.with_name('PROTOCOL.json')
    assert sha(protocol)==old['protocol_sha256']
    plan=json.loads(protocol.read_bytes())
    for key in ('latest_m423_integrated_board','latest_m423_integrated_closure'):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert board['latest_m423_integrated_closure']['numerical_pass'] is True
    plan['schema']='m425-temperature-free-warm-request-protocol-v1'
    plan['supersedes_protocol_sha256']=old['protocol_sha256']
    plan['user_instruction']='以后都不需要再测量温度；继续下一步。'
    plan['temperature_measurement_enabled']=False
    plan.pop('missing_environment_evidence')
    c=plan['warm_conditions']
    for key in ('observable_temperature_required','paired_entry_temperature_difference_max_mC','observed_cooling_or_throttling_active_rejects'):c.pop(key)
    c.update(temperature_measurement_enabled=False,no_thermal_hwmon_IIO_cooling_reads=True,
             first_two_warmup_before_cache_may_be_empty_within_fixed_budget=True,
             after_every_request_cache_must_match=True,CPU_observed_frequency_must_match=True)
    folder=BASE/'runs/M425-warm-protocol-01';p=folder/'PROTOCOL.json'
    atomic(p,encoded(plan),immutable=True)
    result=dict(status='FROZEN_M425_TEMPERATURE_FREE_WARM_PROTOCOL',protocol_sha256=sha(p),
                supersedes_protocol_sha256=old['protocol_sha256'],source_sha256=sha(HERE/'m425_protocol.py'),
                temperature_measurement_enabled=False,board_run=False,performance_pass=False)
    out=folder/'RESULT.json';atomic(out,encoded(result),immutable=True)
    text=('## M425 无温度完整暖请求协议（2026-10-06）\n\nSHA '+sha(out)+'，协议'+sha(p)+'；'
          '用户明确以后不再测温，后续不读取thermal/hwmon/IIO/cooling，也不用温度准入。M424旧记录保持；'
          '在任何性能样本之前冻结新协议，仍4预热＋8正式ABBA/BAAB，原七DMA驻留/0新增、原complete计时及计时后数值核对。'
          '首两次预热前缓存可为空但在原预算内，之后精确26项/66699264B；读盘、CPU/PL时钟、内存和双组/95%判据保持。'
          '下一步轻量入口组件/严格回收检查，通过后一次完整请求对照，无新增层或生产晋级。')
    sync('latest_m425_warm_protocol',dict(result=out.relative_to(ROOT).as_posix(),sha256=sha(out),**result),text)
    atomic(folder/'REPORT.md',('# M425 完整请求对照\n\n'+text+'\n').encode('utf-8'),immutable=True)
    print('M425_PROTOCOL_SYNC',sha(out),sha(p))
if __name__=='__main__':main()
