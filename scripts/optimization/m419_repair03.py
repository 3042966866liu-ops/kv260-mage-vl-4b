"""Preserve the source-level failure; bind the actual lower chain before resources."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    closure=(HERE/'m412_close.py').read_text(encoding='utf-8').replace('M412','M419').replace('latest_m412_complete_mlp_board','latest_m419_complete_mlp_board02').replace('latest_m412_complete_mlp_closure','latest_m419_complete_mlp_closure02').replace('M419-complete-MLP-closure-01','M419-complete-MLP-closure-02').replace('第12层','第13层')
    atomic(HERE/'m419_close02.py',closure.encode('utf-8'),immutable=True)
    import importlib.util
    spec=importlib.util.spec_from_file_location('m419_closure02',HERE/'m419_close02.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.main()
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=board['latest_m419_complete_mlp_board02'];raw=json.loads((ROOT/e['result']).read_bytes())
    assert raw['phase']=='source' and not raw['allocations'] and not raw['overlay_loads'] and raw['physical_transactions_started']==0
    assert "PASS_M410_CHAIN" in raw['errors'][0]['traceback']
    review=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'
    note=f'\n\n## M419 前级状态名称绑定遗漏（2026-10-06）\n\n原失败 SHA {e["sha256"]}；读取的 M418 chain SHA 正确，但复制的 M412 入口仍要求 PASS_M410_CHAIN，在 source 阶段拒绝，0 Overlay/分配/事务。原失败已回收闭合。后续必须实际调用新包前级检查，接受冻结 M418 原结果，拒绝错误状态、返回码、层级、Build 与 SHA，并核对该调用位于所有资源分配之前；不能仅测试数学 binding 或模拟更早的包失败来声称已覆盖完整入口。旧结果和包不可覆盖。\n'
    assert e['sha256'] not in review.read_text(encoding='utf-8-sig');atomic(review,(review.read_text(encoding='utf-8-sig')+note).encode('utf-8'))
    old=BASE/'candidates/M419-layer13-complete-MLP-02';pkg=old.with_name('M419-layer13-complete-MLP-03');assert not pkg.exists();pkg.mkdir()
    helper='''def verify_prior_chain(prior,expected_sha):
    if digest(prior)!=expected_sha:raise RuntimeError('Prior chain SHA differs')
    previous=json.loads(prior.read_bytes())
    if (previous['status']!='PASS_M418_CHAIN' or type(previous['gate_return_code']) is not int or previous['gate_return_code']!=0
        or previous['gate_level']!='Chain' or previous['build_id']!='0x4D333537' or previous['errors']):
        raise RuntimeError('Prior M418 chain identity/status differs')
    return previous
'''
    for row in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        assert sha(old/row['path'])==row['sha256']
        if row['path']=='SHA256SUMS':continue
        data=(old/row['path']).read_bytes()
        if row['path'] in ('m419_gate.py','m419_export.py','run_m419_mlp.sh'):data=data.replace(b'm419_complete_mlp_02',b'm419_complete_mlp_03')
        if row['path']=='m419_gate.py':
            s=data.decode('utf-8');anchor="        prior=Path(plan['chain_result']);assert digest(prior)==plan['chain_raw_sha256']\n        previous=json.loads(prior.read_bytes());assert previous['status']=='PASS_M410_CHAIN' and previous['gate_return_code']==0"
            assert s.count(anchor)==1;s=s.replace(anchor,"        prior=Path(plan['chain_result']);previous=verify_prior_chain(prior,plan['chain_raw_sha256'])")
            assert s.count('def proc():')==1;s=s.replace('def proc():',helper+'def proc():');ast.parse(s,feature_version=(3,10));data=s.encode('utf-8')
        atomic(pkg/row['path'],data,immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(pkg/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    for src,dst in [('m419_workflow02.py','m419_workflow03.py'),('m419_control02.ps1','m419_control03.ps1'),('m419_support03.py','m419_support04.py')]:
        s=(HERE/src).read_text(encoding='utf-8').replace('M419-layer13-complete-MLP-02','M419-layer13-complete-MLP-03').replace('m419_complete_mlp_candidate_02','m419_complete_mlp_candidate_03').replace('m419_complete_mlp_02','m419_complete_mlp_03').replace('tmp/m41902','tmp/m41903')
        for kind in ('preparation','support','transfer','board'):s=s.replace('latest_m419_complete_mlp_'+kind+'02','latest_m419_complete_mlp_'+kind+'03')
        for kind in ('preparation','support','transfer','board'):s=s.replace('M419-complete-MLP-'+kind+'-02','M419-complete-MLP-'+kind+'-03')
        s=s.replace('m419_workflow02.py','m419_workflow03.py').replace('import m419_workflow02 as w','import m419_workflow03 as w').replace('m419_control02.ps1','m419_control03.ps1').replace('m419_support03.py','m419_support04.py')
        if dst=='m419_support04.py':
            # Binding payload is identical: retain its existing clean-staged proof.
            s=s.replace("cp=ROOT/'tmp/m41903/component/RESULT.json'","cp=ROOT/'tmp/m41902/component/RESULT.json'")
            anchor="    producer=load('m419_gate');exporter=load('m419_export');rejects=0"
            extra='''
    chain=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M418-visual-chain-board-01/BOARD_RESULT.json'
    assert producer.verify_prior_chain(chain,plan['chain_raw_sha256'])==json.loads(chain.read_bytes())
    with tempfile.TemporaryDirectory() as temporary:
        p=Path(temporary)/'BOARD_RESULT.json';value=json.loads(chain.read_bytes())
        for key,bad in [('status','PASS_M410_CHAIN'),('gate_return_code',1),('gate_return_code',False),('gate_level','Descriptor'),('build_id','0x4D395832'),('errors',['synthetic'])]:
            p.write_bytes(encoded(dict(value,**{key:bad})))
            try:producer.verify_prior_chain(p,sha(p))
            except RuntimeError:rejects+=1
            else:raise AssertionError('Invalid prior chain accepted')
        try:producer.verify_prior_chain(chain,'0'*64)
        except RuntimeError:rejects+=1
        else:raise AssertionError('Prior SHA ignored')
    tree=ast.parse((pkg/'m419_gate.py').read_bytes());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    calls=[n for n in ast.walk(main) if isinstance(n,ast.Call)]
    check=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='verify_prior_chain')
    constructor=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='M273LatestPSVisionRuntime')
    owner=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='WorkOwner')
    assert check.lineno<constructor.lineno<owner.lineno
'''
            assert s.count(anchor)==1;s=s.replace(anchor,anchor+extra)
        atomic(HERE/dst,s.encode('utf-8'),immutable=True)
    prior=json.loads((ROOT/board['latest_m419_complete_mlp_preparation02']['result']).read_bytes());prior.update(status='PREPARED_M419_PRIOR_CHAIN_FIX03',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),prior_source_failure_sha256=e['sha256'],board_run=False)
    out=BASE/'runs/M419-complete-MLP-preparation-03/RESULT.json';atomic(out,encoded(prior),immutable=True)
    sync('latest_m419_complete_mlp_preparation03',dict(status=prior['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=prior['manifest_sha256']),f'## M419 同级前级状态绑定修复03（2026-10-06）\n\nSHA {sha(out)}；原失败 {e["sha256"]} 在源码前级名称检查拒绝，0资源/事务，保留原结果。03核对真实M418状态/rc/层级/Build/SHA，检查位于PS/Overlay/DMA之前；结果目录03，原数学/七缓冲/计时边界/样本数不改。实际正负入口核对及配套检查后仅本级重试，不扩大视觉。')
    print('M419_REPAIR03_PREPARED',sha(out),prior['manifest_sha256'])

if __name__=='__main__':main()
