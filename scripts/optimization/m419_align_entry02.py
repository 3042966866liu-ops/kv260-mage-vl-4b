"""Unify three saved-result entry paths before any upload or resource allocation."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    old=BASE/'candidates/M419-layer13-complete-MLP-01';pkg=old.with_name('M419-layer13-complete-MLP-02')
    if pkg.exists():raise RuntimeError('Immutable staging exists')
    manifest=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes());pkg.mkdir()
    for row in manifest['files']:
        assert sha(old/row['path'])==row['sha256']
        if row['path']=='SHA256SUMS':continue
        raw=(old/row['path']).read_bytes()
        if row['path'] in ('m419_gate.py','m419_export.py'):
            assert raw.count(b'm419_layer13_complete_mlp_01')==1
            raw=raw.replace(b'm419_layer13_complete_mlp_01',b'm419_complete_mlp_02')
        if row['path']=='run_m419_mlp.sh':
            assert raw.count(b'm419_complete_mlp_01')==1
            raw=raw.replace(b'm419_complete_mlp_01',b'm419_complete_mlp_02')
        atomic(pkg/row['path'],raw,immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());new=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(pkg/'PACKAGE_MANIFEST.json',encoded(new),immutable=True)
    workflow=(HERE/'m419_workflow.py').read_text(encoding='utf-8').replace('M419-layer13-complete-MLP-01','M419-layer13-complete-MLP-02').replace('tmp/m41901','tmp/m41902').replace('M419-complete-MLP-transfer-01','M419-complete-MLP-transfer-02').replace('M419-complete-MLP-board-01','M419-complete-MLP-board-02').replace('latest_m419_complete_mlp_transfer','latest_m419_complete_mlp_transfer02').replace('latest_m419_complete_mlp_board','latest_m419_complete_mlp_board02')
    atomic(HERE/'m419_workflow02.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m419_control.ps1').read_text(encoding='utf-8').replace('M419-layer13-complete-MLP-01','M419-layer13-complete-MLP-02').replace('m419_complete_mlp_candidate_01','m419_complete_mlp_candidate_02').replace('tmp/m41901','tmp/m41902').replace('M419-complete-MLP-board-01','M419-complete-MLP-board-02').replace('m419_workflow.py','m419_workflow02.py').replace('latest_m419_complete_mlp_preparation','latest_m419_complete_mlp_preparation02').replace('latest_m419_complete_mlp_support','latest_m419_complete_mlp_support02').replace('latest_m419_complete_mlp_transfer','latest_m419_complete_mlp_transfer02')
    atomic(HERE/'m419_control02.ps1',control.encode('utf-8'),immutable=True)
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=board['latest_m419_complete_mlp_preparation'];assert sha(ROOT/e['result'])==e['sha256']
    value=json.loads((ROOT/e['result']).read_bytes());value.update(status='PREPARED_M419_RESULT_ENTRY_ALIGNED02',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
        prior_offline_preparation_sha256=e['sha256'],actual_gate_export_runner_result_directory='/home/ubuntu/m419_complete_mlp_02',entry_paths_equal=True,board_run=False)
    out=BASE/'runs/M419-complete-MLP-preparation-02/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m419_complete_mlp_preparation02',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
         f'## M419 完整段入口离线对齐02（2026-10-06）\n\nSHA {sha(out)}；上传前核对发现01 gate/export与runner的结果目录命名不同；尚无上传/板端失败或资源。02统一到/home/ubuntu/m419_complete_mlp_02，01离线准备保留，算法/缓冲/计时/参考合同不变。clean真实child和实际配套检查后才授权上传，本级未执行。')
    print('M419_ENTRY_ALIGNED02',sha(out),value['manifest_sha256'])

if __name__=='__main__':main()
