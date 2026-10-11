"""Preserve preparation01; correct observer's generated instance-name matching."""
import json,hashlib
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    original=HERE/'m438_prepare.py'
    reject=BASE/'runs/M438-weight-wait-preparation-rejection-01/RESULT.json'
    if not reject.exists():
        r=dict(status='REJECTED_OFFLINE_OBSERVER_INSTANCE_MATCH',source_sha256=sha(original),
          partial_directory='tmp/m438_weight_wait_01',board=False,compile_started=False,simulation_started=False,
          error='Regex word boundary before m89x missed actual grp_m89x instance prefix. Reuse immutable original inputs into independent02, preserve partial01.',
          source=original.relative_to(ROOT).as_posix())
        atomic(reject,encoded(r),immutable=True)
        sync('latest_m438_preparation_rejection',dict(status=r['status'],result=reject.relative_to(ROOT).as_posix(),sha256=sha(reject),board=False),
          f'## M438 离线观察路径匹配拒绝（2026-10-07）\n\nSHA {sha(reject)}；原RTL/fixture字节复制后观察器正则word-boundary遗漏实际grp_前缀，0编译/仿真/板端。保留原脚本及partial01，独立02仅修正观测实例提取和层级，原DUT/数学/参考不改。')
    r=json.loads(reject.read_bytes());assert sha(original)==r['source_sha256']
    source=original.read_text(encoding='utf-8')
    source=source.replace("r'\\b(m89x_shard", "r'(m89x_shard")
    source=source.replace("child=q+'.'+inst[0]", "child=q+'.grp_'+inst[0]")
    assert source!=original.read_text(encoding='utf-8')
    ns={'__name__':'m438_preparation02_implementation','__file__':str(original)}
    exec(compile(source,str(HERE/'m438_prepare02.py')+':corrected-implementation','exec'),ns)
    ns['OUT']=ROOT/'tmp/m438_weight_wait_02'
    # Hierarchical names and all four actual child loop signals must resolve before copying.
    mon=ns['monitor']()
    assert mon.count('assign iter[')==4 and mon.count('internal_AR_during_MAC=')==1
    ns['main']()

if __name__=='__main__':main()
