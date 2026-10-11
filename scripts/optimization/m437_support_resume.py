"""Record offline key-assertion rejection and resume saved fixture checks only."""
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m427_prepare import once


def main():
    folder=ROOT/'tmp/m43701'
    record=dict(status='REJECTED_M437_OFFLINE_FIXTURE_EXPECTED_OLD_BOARD_KEY',
        reason='Actual collector wrote latest_m437_natural_IO_board; fixture assertion retained latest_m437_warm_board.',
        source_sha256=sha(HERE/'m437_support.py'),
        actual_stream_component_complete=True,component_stdout_sha256=sha(folder/'component/stdout.bin'),
        component_stderr_sha256=sha(folder/'component/stderr.bin'),
        fixture_sha256=sha(folder/'component_stage/TRIALS_FIXTURE_RESULT.json'),
        board_run=False,performance_pass=False)
    out=BASE/'runs/M437-support-rejection-01/RESULT.json'
    atomic(out,encoded(record),immutable=True)
    sync('latest_m437_support_rejection',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),
        f'## M437 离线回收fixture键残留拒绝（2026-10-07）\n\nSHA {sha(out)}；实际原stream12次fake模型/DMA高I/O检查和真实collector保存已通过，fixture还断言旧latest_m437_warm_board，实际是latest_m437_natural_IO_board。0上传/板端。保留脚本/原stdout/stderr和fixture，只在新02支持复用已保存组件结果并改正确键，不重跑已通过组件或更改包。')
    source=(HERE/'m437_support.py').read_text(encoding='utf-8')
    start=source.index("    stage=ROOT/")
    end=source.index("    original=json.loads(",start)
    resume="""    stage=ROOT/'tmp/m43701/component_stage';out=ROOT/'tmp/m43701/component'
    lines=[x.split('=',1)[1] for x in (out/'stdout.bin').read_bytes().decode('utf-8').splitlines() if x.startswith('M437_COMPONENT=')]
    assert len(lines)==1
    component=json.loads(lines[0]);fixture=json.loads((stage/'TRIALS_FIXTURE_RESULT.json').read_bytes())
    assert component['trials']['actual_trials_12_sequence'] and all(s['io_delta']['read_bytes']>1048576 for s in fixture['samples'])
    language=json.loads((BASE/'runs/M428-saved-language-board-01/BOARD_RESULT.json').read_bytes())
"""
    source=source[:start]+resume+source[end:]
    source=source.replace("'latest_m437_warm_board'","'latest_m437_natural_IO_board'")
    source=source.replace('tmp/m43701/export_fixture','tmp/m43702/export_fixture')
    source=source.replace('M437-natural-IO-support-01','M437-natural-IO-support-02')
    source=source.replace("'m437_support.py','m437_sequence.py'", "'m437_support02.py','m437_sequence.py'")
    atomic(HERE/'m437_support02.py',source.encode('utf-8'),immutable=True)
    print('M437_OFFLINE_RESUME_READY')


if __name__=='__main__':main()
