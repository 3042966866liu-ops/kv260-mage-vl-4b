"""Preserve second host-fixture path rejection; finish support on saved fixtures."""
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m427_prepare import once


def main():
    r=dict(status='REJECTED_M437_OFFLINE_PREREQUISITE_FIXTURE_PATH',
           reason='Fixture import requested m437_prerequisite.py; actual unchanged dependency is m433_prerequisite.py.',
           source_sha256=sha(HERE/'m437_support02.py'),
           component_reused_without_rerun=True,actual_export_and_atomic_collect_passed=True,
           board_run=False,performance_pass=False)
    p=BASE/'runs/M437-support-rejection-02/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m437_support_rejection_02',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p)),
        f'## M437 离线前级fixture路径拒绝（2026-10-07）\n\nSHA {sha(p)}；actual export/collector与原字节目的地检查已过，但harness请求m437_prerequisite.py，实际包明确复用m433_prerequisite.py。0上传/板端，包/原数学未改。03只修实际fixture依赖路径及新输出目录；复用已完成stream，不重跑模型或已过provider组件。')
    source=(HERE/'m437_support02.py').read_text(encoding='utf-8')
    source=once(source,"w.PKG/'m437_prerequisite.py'","w.PKG/'m433_prerequisite.py'")
    source=source.replace('tmp/m43702/export_fixture','tmp/m43703/export_fixture')
    source=source.replace('M437-natural-IO-support-02','M437-natural-IO-support-03').replace("'m437_support02.py'","'m437_support03.py'")
    atomic(HERE/'m437_support03.py',source.encode('utf-8'),immutable=True)


if __name__=='__main__':main()
