"""Resolve actual generated names; preserve both rejected observer preparations."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    source=HERE/'m438_prepare.py'
    reject=BASE/'runs/M438-weight-wait-preparation-rejection-02/RESULT.json'
    if not reject.exists():
        r=dict(status='REJECTED_OFFLINE_OBSERVER_GENERATED_FORMAT',board=False,compile_started=False,simulation_started=False,
          source_sha256=sha(HERE/'m438_prepare02.py'),error='02 still expected space before instance opening parenthesis; actual generated RTL has no space. CPU-only precheck also found per-shard allocation counter suffixes1/4/3/2; resolve actual unique16-iteration comparison instead of guessing suffix.')
        atomic(reject,encoded(r),immutable=True)
        sync('latest_m438_preparation_rejection02',dict(status=r['status'],result=reject.relative_to(ROOT).as_posix(),sha256=sha(reject),board=False),
          f'## M438 观察器排版和自动命名核对（2026-10-07）\n\nSHA {sha(reject)}；02在复制/编译前正则检查拒绝。实际实例括号无空格，四shard token-pair计数后缀不同；03从真实生成模块唯一实例及16次退出比较解析，保留01/02，0板端/编译/仿真。')
    assert sha(source)==json.loads((BASE/'runs/M438-weight-wait-preparation-rejection-01/RESULT.json').read_bytes())['source_sha256']
    s=source.read_text(encoding='utf-8')
    s=s.replace("r'\\b(m89x_shard\\w*_Pipeline_VITIS_LOOP_80_6_fu_\\d+) \\('","r'\\b(grp_m89x_shard\\w*_Pipeline_VITIS_LOOP_80_6_fu_\\d+)\\s*\\('")
    s=s.replace('ap_sig_allocacmp_token_pair_1 ==','ap_sig_allocacmp_token_pair_\\d+ ==')
    s=s.replace('{q}.grp_{inst[0]}_ap_start','{q}.{inst[0]}_ap_start')
    assert s!=source.read_text(encoding='utf-8')
    ns={'__name__':'m438_actual_name_preparation','__file__':str(source)}
    exec(compile(s,str(HERE/'m438_prepare03.py')+':resolved-implementation','exec'),ns)
    ns['OUT']=ROOT/'tmp/m438_weight_wait_03'
    mon=ns['monitor']();assert mon.count('assign iter[')==4 and 'grp_grp_' not in mon
    ns['main']()
if __name__=='__main__':main()
