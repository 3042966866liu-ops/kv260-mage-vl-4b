"""Bind the prepared chains to the exact previously verified visual layout."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m407_mlp_contract import chain_for

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior=b['latest_m407_visual_mlp_contract']
    assert sha(ROOT/prior['result'])==prior['sha256']
    original=json.loads((ROOT/prior['result']).read_bytes())
    audit=BASE/'runs/M405-vision-evidence-audit-01/RESULT.json'
    assert sha(audit)=='52c857bd41fd27b9190e089020d993fb3dc9c8ef3aac96e59ada17d81d3f4bf8'
    frozen=json.loads(audit.read_bytes())['current_input_layout']
    layout=ROOT/frozen['path'];assert sha(layout)==frozen['sha256']==original['layout_sha256']
    pkg=BASE/'candidates/M407-vision-MLP-isolated-01';assert sha(pkg/'PACKAGE_MANIFEST.json')==original['package_manifest_sha256']
    m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes())
    for x in m['files']:assert sha(pkg/x['path'])==x['sha256'] and (pkg/x['path']).stat().st_size==x['bytes']
    saved=json.loads((pkg/'MLP_CHAINS.json').read_bytes());modules={x['module']:x for x in json.loads(layout.read_bytes())['modules']}
    assert saved['layout_sha256']==frozen['sha256']
    assert [chain_for(modules[x['module']],i) for i,x in enumerate(saved['chains'])]==saved['chains']
    r=dict(status='PASS_M407_EXACT_PRIOR_LAYOUT_BINDING',prior_contract_sha256=prior['sha256'],manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
        exact_layout_sha256=frozen['sha256'],actual_48_chain_rederivation_equal=True,
        correction='replace missing prior-layout binding with independent strict M405 layout SHA check; preserve original script/result and full file/record checks',
        board_run=False,quality_pass=False,performance_pass=False,source_sha256=sha(HERE/'m407_layout_closure.py'))
    p=BASE/'runs/M407-vision-MLP-layout-closure-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m407_visual_mlp_layout_closure',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=r['manifest_sha256']),
         f'## M407视觉MLP精确layout绑定补充（2026-10-05）\n\nSHA {sha(p)}；M405原layout SHA {frozen["sha256"]}与实际manifest/全部48重推chain及原M407包完全一致。'
         '原审计脚本四文件/原record检查已过，但未严格绑定既有layout身份，本补充在任何上板前补齐，原记录保持。'
         '下一步仅真实输入PS捕获及局部A8筛选；M407只是离线矩阵/事务合同，无新硬件、质量或性能。')
    print('M407_LAYOUT_BOUND',sha(p))

if __name__=='__main__':main()
