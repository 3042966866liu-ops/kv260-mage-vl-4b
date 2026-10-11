"""Preserve offline01; complete the changed-prefix residual screen before board work."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    old=BASE/'candidates/M420-layers12-13-full-visual-01';pkg=old.with_name('M420-layers12-13-full-visual-02');assert not pkg.exists();pkg.mkdir()
    for row in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        assert sha(old/row['path'])==row['sha256']
        if row['path']=='SHA256SUMS':continue
        data=(old/row['path']).read_bytes()
        if row['path']=='m420_gate.py':data=(HERE/'m420_gate.py').read_bytes()
        if row['path'] in ('m420_gate.py','m420_export.py','run_m420_mlp.sh'):data=data.replace(b'm420_combination_visual_01',b'm420_combination_visual_02')
        atomic(pkg/row['path'],data,immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(pkg/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    p=HERE/'m420_workflow.py';s=p.read_text(encoding='utf-8').replace('M420-layers12-13-full-visual-01','M420-layers12-13-full-visual-02');atomic(HERE/'m420_workflow02.py',s.encode('utf-8'),immutable=True)
    control=(HERE/'m419_control03.ps1').read_text(encoding='utf-8').replace('M419','M420').replace('m419','m420').replace('M420-layer13-complete-MLP-03','M420-layers12-13-full-visual-02').replace('m420_complete_mlp_candidate_03','m420_combination_visual_candidate_02').replace('tmp/m42003','tmp/m42001').replace('M420-complete-MLP-board-03','M420-combination-board-01').replace('m420_workflow03.py','m420_workflow02.py')
    start=control.index('foreach ($key in @(');end=control.index(' { VerifyEvidence $key }',start)
    control=control[:start]+"foreach ($key in @('latest_m419_complete_mlp_board03','latest_m419_complete_mlp_closure03','latest_m414_layer12_visual_closure','latest_m415_saved_feature_language_closure','latest_m420_combination_plan','latest_m420_combination_preparation02','latest_m420_combination_support'))"+control[end:]
    control=control.replace('latest_m420_complete_mlp_support03','latest_m420_combination_support').replace('latest_m420_complete_mlp_transfer03','latest_m420_combination_transfer')
    atomic(HERE/'m420_control.ps1',control.encode('utf-8'),immutable=True)
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m420_combination_preparation'];v=json.loads((ROOT/e['result']).read_bytes())
    v.update(status='PREPARED_M420_ACTUAL_CHANGED_RESIDUAL_SCREEN02',prior_offline_preparation_sha256=e['sha256'],manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),files=m['file_count'],bytes=m['total_bytes'],actual_changed_layer13_residual_included=True,result_directory='/home/ubuntu/m420_combination_visual_02')
    out=BASE/'runs/M420-combination-preparation-02/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m420_combination_preparation02',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=v['manifest_sha256']),f'## M420 改变前缀的实际残差筛选补齐02（2026-10-06）\n\nSHA {sha(out)}；上传前审计旧isolated compare的residual_sum沿用原前缀，组合13的实际残差也会改变；02另对真实candidate residual＋MLP和原版作同阈值筛选，原全特征/软件逐位规则保持。01离线包保留，0板端/资源；先完整入口/回收/控制检查再仅12＋13组合，未扩大24层。')
    print('M420_FREEZE02',sha(out),v['manifest_sha256'])
if __name__=='__main__':main()
