"""Saved-only closure branches using explicitly synthetic measurement fixtures."""
import copy,json
from pathlib import Path
import m437_close as closure
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    source=ROOT/'tmp/m43703/export_fixture/collected/BOARD_RESULT.json'
    original=json.loads(source.read_bytes())
    root=ROOT/'tmp/m43701/closure_fixture'
    assert not root.exists(), 'Immutable fixture already exists'
    outcomes=[]
    for name,expected in [('benefit','PASS_NATURAL_IO_FULL_REQUEST_BENEFIT'),('no_gain','NET_BENEFIT_NOT_RELIABLY_MEASURED_CLOSE_THIS_EXPERIMENT'),('failure','CLOSED_M437_ORIGINAL_GATE_FAILURE')]:
        case=root/name;case.mkdir(parents=True)
        r=copy.deepcopy(original)
        if name=='failure':
            r.update(status='FAIL',gate_return_code=1,errors=['Explicit synthetic gate failure'],numerical_pass=False,samples=[],warmup_samples=[],formal_samples=[])
        else:
            for s in r['samples']:
                s['timing']['total_ms']=105000 if name=='benefit' and s['variant']=='B' else 108000
            r['warmup_samples']=r['samples'][:4];r['formal_samples']=r['samples'][4:]
        raw=case/'RAW.json';atomic(raw,json.dumps(r,separators=(',',':'),ensure_ascii=False).encode(),immutable=True)
        digest=sha(raw);entry=dict(result='RAW.json',sha256=digest)
        atomic(case/'deployment/mage_vl4b/BOARD_GATE_RESULT.json',encoded({'latest_m437_natural_IO_board':entry}),immutable=True)
        for n in ('CURRENT_STATE.md','docsMILESTONES.md'):atomic(case/n,digest.encode(),immutable=True)
        closure.ROOT=case;closure.BASE=case/'optimization';seen=[]
        def local_sync(key,value,note):
            assert key=='latest_m437_natural_IO_closure'
            assert value['status']==expected and value['production_promoted'] is False
            assert sha(case/value['result'])==value['sha256']
            assert value['raw_sha256']==digest
            seen.append(value)
        closure.sync=local_sync
        closure.main()
        out=closure.BASE/'runs/M437-natural-IO-closure-01/RESULT.json'
        result=json.loads(out.read_bytes())
        assert len(seen)==1 and result['status']==expected
        assert result['performance_pass'] is (name=='benefit')
        if name=='benefit':assert result['paired_95percent_CI_ms']==[3000,3000]
        if name=='no_gain':assert result['paired_95percent_CI_ms']==[0,0]
        assert sha(raw)==digest
        report=out.with_name('REPORT.md');assert report.exists()
        outcomes.append(dict(case=name,status=expected,result=out.relative_to(ROOT).as_posix(),sha256=sha(out),report_sha256=sha(report)))
    result=dict(status='PASS_M437_SAVED_ONLY_CLOSURE_SUPPORT',synthetic_measurements=True,real_board_requests=0,performance_evidence=False,fixture_source_sha256=sha(source),cases=outcomes,source_sha256=sha(HERE/'m437_closure_support.py'),closure_source_sha256=sha(HERE/'m437_close.py'))
    out=BASE/'runs/M437-natural-IO-closure-support-01/RESULT.json';atomic(out,encoded(result),immutable=True)
    sync('latest_m437_closure_support',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),closure_source_sha256=result['closure_source_sha256'],performance_evidence=False),f'## M437 保存结果裁决器离线检查（2026-10-07）\n\nSHA {sha(out)}；实际保存结果裁决器的正收益、零收益、原门禁失败三个分支以显式合成计时检查通过，原字节不变，报告/原子保存/同步参数核对。0板端请求，非性能证据，冻结协议和实际包未改。')
    print('M437_CLOSURE_SUPPORT_SYNC',sha(out))

if __name__=='__main__':main()
