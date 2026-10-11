"""Repair only a collector metadata key using original saved video bytes."""
import ast,json,sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
def main():
    old=HERE/'m387_collect.py';new=HERE/'m387_collect_recovered.py'
    s=old.read_text(encoding='utf-8');assert s.count("'latest_m386_ps_video_board'")==1
    corrected=s.replace("'latest_m386_ps_video_board'","'latest_m387_ps_video_board'")
    ast.parse(corrected,feature_version=(3,10));atomic(new,corrected.encode('utf-8'),immutable=True)
    value=dict(status='PASS_SAVED_ONLY_METADATA_RECOVERY_PREPARATION',original_collector_sha256=sha(old),recovered_collector_sha256=sha(new),only_sync_key_changed=True,old_key='latest_m386_ps_video_board',new_key='latest_m387_ps_video_board',original_decoder_identical=True,original_gate_and_package_unchanged=True,hardware_rerun=False)
    p=BASE/'runs/M387-metadata-recovery-preparation-01/RESULT.json';atomic(p,encoded(value),immutable=True);d=sha(p)
    sync('latest_m387_metadata_recovery_preparation',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=d),f'## M387 回收元数据键核对\n\n最后离线复核发现collector同步键误沿用m386前缀，数值decode/原字节/SHA不受影响；原collector及支持保留。独立recovered仅将键改为latest_m387_ps_video_board，SHA {d}；硬件不重跑，原执行回收完成后才从保存UART原字节修复并同步三记录，修复前不解锁后级。')
    if sys.argv[1:]==['Collect']:
        assert (ROOT/'tmp/m387/component_uart.log').exists()
        import importlib.util
        spec=importlib.util.spec_from_file_location('saved_only_metadata_collector',new);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.collect(ROOT/'tmp/m387/component_uart.log')
        board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));actual=board['latest_m387_ps_video_board']
        assert sha(ROOT/actual['result'])==actual['sha256'] and all(actual['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        print('M387_SAVED_METADATA_RECOVERED',actual['sha256'])
    else:print('M387_METADATA_RECOVERY_READY',d)
if __name__=='__main__':main()
