"""One bounded unchanged-model evaluation, no board operations."""
import sys, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_quality import *

def main():
    proto = RUNS / 'M540-campus03-demo-quality-protocol-01/RESULT.json'
    p = read(proto)
    for f, h in p['frozen'].items():
        assert sha(ROOT / f) == h
    out = RUNS / 'M540-campus03-demo-quality-host-01'
    out.mkdir(exist_ok=False)
    cmd = ['wsl.exe', '-d', 'Ubuntu-24.04', '--', '/home/lyy/projects/qwen_baseline/.venv/bin/python', '-I', '-B', '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/' + rel(HERE / 'quality.py')]
    save(out / 'START.json', dict(command=cmd, protocol_sha256=sha(proto)))
    with (out / 'stdout.raw').open('xb') as a, (out / 'stderr.raw').open('xb') as b:
        rc = subprocess.run(cmd, stdout=a, stderr=b, timeout=p['budget']['seconds'] + 120).returncode
    native = RUNS / 'M540-campus03-demo-software-quality-01/RESULT.json'
    v = dict(status=('COMPLETE' if rc == 0 else 'FAIL') + '_M540_SOFTWARE_HOST', host_rc=rc, native_sha256=sha(native) if native.exists() else None, stdout_sha256=sha(out / 'stdout.raw'), stderr_sha256=sha(out / 'stderr.raw'), board_commands=0)
    save(out / 'RESULT.json', v)
    sys.path.insert(0, str(ROOT / 'scripts/optimization'))
    from m455456_workflow02 import synchronized
    h = sha(out / 'RESULT.json')
    synchronized('latest_m539_campus03_quality_host01', dict(status=v['status'], result=rel(out / 'RESULT.json'), sha256=h, board=False, promoted=False), '## M540新演示五帧软件完整判断原执行\n\nRESULT SHA ' + h + '；实际host ' + str(rc) + '，原完整logits/参数/缓存/128双视图记录保全。0训练/板/heldout；软件判断不当Web/全片或KV260验收，待独立保存审计。')
    print(v)
    print((out / 'stdout.raw').read_text(encoding='utf8', errors='replace')[-4000:])
    if rc:
        print((out / 'stderr.raw').read_text(encoding='utf8', errors='replace')[-2000:])
    return rc
if __name__ == '__main__':
    raise SystemExit(main())
