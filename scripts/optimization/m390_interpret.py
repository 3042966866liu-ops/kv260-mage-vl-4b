"""Close saved bounded capture; do not execute or re-collect hardware."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
from m390_collect import decode,PKG

def main():
    p=BASE/'runs/M390-gate-up-capture-board-01/BOARD_RESULT.json'
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=board['latest_m390_capture_board'];assert sha(p)==prior['sha256']
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    digest,raw,r=decode((ROOT/'tmp/m390/component_uart.log').read_text(encoding='utf-8-sig'))
    assert digest==sha(p) and raw==p.read_bytes()
    passed=r['status']=='PASS_M390_ACTUAL_GATE_UP_CAPTURE' and r['capture_pass'] and not r['gate_return_code']
    value=dict(status='PASS_ACTUAL_FIXED159_GATE_UP_CAPTURE_ONLY' if passed else 'CLOSED_CAPTURE_FAILURE',
               raw_sha256=digest,raw_path=p.relative_to(ROOT).as_posix(),manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               build_id=r['build_id'],gate_return_code=r['gate_return_code'],errors=r['errors'],
               fixtures=r.get('actual_gate_up_fixtures',{}),source='Original fixed159 video layer0 projection outputs, untouched original SiLU has not run',
               language_logical_calls=r.get('logical_calls'),physical_including_minimal=r.get('fpga_transactions'),
               parser_workers=1,PS_prefetch=False,numerical_candidate_proven=False,component_performance_proven=False,
               stable_restored=r.get('stable_overlay_reloaded',False),safe_release_count=r.get('original_buffer_release_count',0),
               fixture_data_transfered_to_host=False,
               next_step='CPU-only actual fixture SHA + bit equality + balanced operator timing' if passed else 'Stop at capture failure; no component or full-model test')
    out=BASE/'runs/M390-capture-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    note=f'## M390 原视频第一层gate/up捕获闭合（2026-10-04）\n\nBuild{r["build_id"]}，裁决{value["status"]}，原SHA {digest}，闭合SHA {d}。原159视频输入/视觉与四family全输出身份、20逻辑/21物理（含最小）、原七DMA逆序释放/线程排空与稳定Overlay恢复核对。仅板端保存真实gate/up各159×9728 FP32，不是新SiLU/完整视频数值或性能PASS；下一步CPU-only逐文件/逐位/重复ABBA+BAAB组件，无稳定收益停止扩大。'
    sync('latest_m390_capture_closure',dict(status=value['status'],sha256=d,result=out.relative_to(ROOT).as_posix(),raw_sha256=digest),note)
    print(json.dumps(value|{'result_sha256':d}))

if __name__=='__main__':main()
