"""Run known local framing/path/cleanup negatives on the actual new transport."""
import json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
files=[]
for name in ['test_m357_transfer.py','test_m357_transfer_collection.py']:
    s=(HERE/name).read_text(encoding='utf-8').replace('m357','m439').replace('M357','M439').replace('tempfile.TemporaryDirectory()',"tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parents[2]/'tmp'))")
    p=HERE/name.replace('m357','m439');atomic(p,s.encode(),immutable=True);files.append(p)
checks=[]
for p in files:
    r=subprocess.run([sys.executable,'-B',str(p)],capture_output=True,cwd=ROOT,timeout=30)
    checks.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),rc=r.returncode,stdout=r.stdout.decode('utf-8',errors='replace'),stderr=r.stderr.decode('utf-8',errors='replace')))
    assert r.returncode==0,checks[-1]
r=dict(status='PASS_M439_LOCAL_TRANSFER_AND_NETWORK_CLEANUP_NEGATIVES',build_id='0x4D343339',checks=checks,tests_run=6,transfer_sha256=sha(HERE/'m439_transfer.py'),collection_sha256=sha(HERE/'m439_transfer_collection.py'),board=False,actual_local_framing=True,fake_network_cleanup=True,extra_real_network_config=False,rejected_first_sandbox_attempt='Local socket framing harness exceeded bounded 30s subprocess budget in sandbox; no board/real-peer connection. No transport implementation change before native local rerun.')
p=BASE/'runs/M439-transfer-controls-checks-01/RESULT.json';atomic(p,encoded(r),immutable=True)
sync('latest_m439_transfer_controls_checks',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),'## M439 传输控制离线检查（2026-10-07）\n\nSHA '+sha(p)+'；6项新实际transport本地socket完整多块/尾块/空文件、路径计数/短读EOF/超时、错误对端地址回收及收集破坏负例PASS。0板端/真实网络改动，不代替板端逐文件SHA或网络回读；包已授权采用指定对端有界文件传输，COM3仍唯一控制/授权/结果通道。')
print(r['status'],sha(p))
