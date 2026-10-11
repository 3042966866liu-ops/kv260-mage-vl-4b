"""Preserve invalid fake-fixture failure; version only the component harness."""
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync


def main():
    original=HERE/'m441_protocol_support_checks.py';raw=original.read_text(encoding='utf-8-sig')
    fixture=ROOT/'tmp/m441_protocol_evidence_checks_01';assert fixture.is_dir()
    result=dict(status='REJECTED_M441_FAKE_POSITIVE_AR_CROSSES_4K',original_return_code=1,
                original_error='AssertionError at first positive fake-evidence acceptance check',
                original_source_sha256=sha(original),predicate_sha256=sha(HERE/'m441_protocol_evidence.py'),
                diagnostic='Saved fake full output/Build/sideband/MAC/FIFO checks pass; full_address_coverage rejects 17-beat requests crossing 4KiB. Predicate correctly fails closed.',
                fixture_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(fixture.glob('*.dat'))],
                RTL_run=False,board=False,ongoing_long_chain_changed=False)
    ev=BASE/'runs/M441-protocol-fixture-rejection-01/RESULT.json';atomic(ev,encoded(result),immutable=True)
    old="""    for i in range(4):
        lines.append(f'M441MAX_METRIC shard={i} active=1 mac_busy=1 mac_calls=2560 iterations=40960 AR=640 R=10880 return_gap=0 RSTALL=0 ARSTALL=10 AR_during_MAC=0 R_during_MAC=0 pending=0 bad_RLAST=0 bad_RRESP=0')
        lines.append(f'M441MAX_PROTOCOL shard={i} descriptors=10 FIFO_MAX=8192 queue_writes=10880 queue_reads=10880 queue_high=34 queue_full=100 queue_final=0 AR_STABLE=9')
        for _ in range(10):
            for address in range(0,1088,17):lines.append(f'M441MAX_AR shard={i} address={address*16:x} len=16 size=4 burst=1')
"""
    new="""    bursts=[]
    for record in range(0,1088,17):
        address=record;remaining=17
        while remaining:
            length=min(remaining,256-address%256)
            bursts.append((address,length));address+=length;remaining-=length
    assert len(bursts)==68 and sum(length for _,length in bursts)==1088
    for i in range(4):
        lines.append(f'M441MAX_METRIC shard={i} active=1 mac_busy=1 mac_calls=2560 iterations=40960 AR={len(bursts)*10} R=10880 return_gap=0 RSTALL=0 ARSTALL=10 AR_during_MAC=0 R_during_MAC=0 pending=0 bad_RLAST=0 bad_RRESP=0')
        lines.append(f'M441MAX_PROTOCOL shard={i} descriptors=10 FIFO_MAX=8192 queue_writes=10880 queue_reads=10880 queue_high=34 queue_full=100 queue_final=0 AR_STABLE=9')
        for _ in range(10):
            for address,length in bursts:lines.append(f'M441MAX_AR shard={i} address={address*16:x} len={length-1} size=4 burst=1')
"""
    assert raw.count(old)==1
    updated=raw.replace(old,new).replace('m441_protocol_evidence_checks_01','m441_protocol_evidence_checks_02').replace('m441_protocol_support_checks.py','m441_protocol_support_checks02.py').replace('M441-protocol-evidence-support-checks-01','M441-protocol-evidence-support-checks-02')
    atomic(HERE/'m441_protocol_support_checks02.py',updated.encode('utf-8'),immutable=True)
    sync('latest_m441_protocol_fixture_rejection',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441 明确fake协议夹具拒绝（2026-10-07）\n\nSHA {sha(ev)}；首组件正例构造17拍AR跨4KiB，被实际验收函数正确拒绝，rc1；0新RTL/板端，原fixture/源保持。02仅将fake AR按256字边界拆分并更新请求数，不弱化实际边界/覆盖判据，不修改正运行的长链。下一步实际原验收组件检查。')
    print(result['status'],sha(ev),'harness02 prepared')


if __name__=='__main__':main()
