"""Fail closed on full-shell route, timing and actual design errors."""
import argparse
import json
import re
import zipfile
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
SHELL=ROOT/'tmp/m357_shell_01'
OUT=SHELL/'out'
def main(export_repair=False):
    exit_path=ROOT/'tmp/m357_shell_exit.json'
    if not exit_path.exists():raise RuntimeError('Implementation still running; inspect only')
    ev=BASE/('runs/M357-full-shell-'+('02' if export_repair else '01')+'/RESULT.json')
    if ev.exists():raise RuntimeError('Immutable shell verdict exists; inspect only')
    prerequisites=[]
    for name in ('M357-shell-preparation-01','M357-auxiliary-checkpoint-readback-01','M357-hwh-abi-01'):
        p=BASE/'runs'/name/'RESULT.json';sha=w.sha(p)
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
            assert sha in (ROOT/n).read_text(encoding='utf-8-sig')
        prerequisites.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha))
    result=dict(status='FAIL_FULL_SHELL_GATE',build_id='0x4D333537',board=False,promoted=False,
        prerequisites=prerequisites,errors=[],warnings=[],retained_startup_errors=[],resources={},artifacts=[])
    paths=[exit_path,ROOT/'tmp/m357_shell_mapping.json',ROOT/'tmp/m357_shell_console.log']
    try:
        rc=json.loads(exit_path.read_text(encoding='utf-8'))['vivado_rc'];result['vivado_rc']=rc
        export_error="ERROR: [Common 17-69] Command failed: Unable to get BIT file from implementation run. Please ensure implementation has been run all the way through Bitstream generation. Aborting write_hw_platform.."
        repair=ROOT/'tmp/m357_shell_export_02'
        if export_repair:
            prior=BASE/'runs/M357-full-shell-01/RESULT.json';prior_sha=w.sha(prior)
            for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
                assert prior_sha in (ROOT/n).read_text(encoding='utf-8-sig')
            assert json.loads(prior.read_text(encoding='utf-8'))['status']=='FAIL_FULL_SHELL_GATE' and rc==1
            input_spec=json.loads((repair/'INPUTS.json').read_text(encoding='utf-8'))
            assert input_spec['prior_failure_sha256']==prior_sha
            for row in input_spec['files']:assert w.sha(ROOT/row['path'])==row['sha256'],'Original routed/bit/HWH/project changed'
            assert json.loads((repair/'EXIT.json').read_text(encoding='utf-8'))['export_rc']==0
            assert json.loads((repair/'MAPPING.json').read_text(encoding='utf-8'))['removed'] is True
            repaired_log=(repair/'console.log').read_text(encoding='utf-8')
            assert 'M357_HARDWARE_DESCRIPTION_EXPORT_PASS_ORIGINAL_BIT_UNCHANGED' in repaired_log
            assert not re.search(r'^ERROR:|^CRITICAL WARNING:',repaired_log,re.M)
            result['original_export_failure_sha256']=prior_sha;result['export_repair_rc']=0
            result['export_repair_scope']='Only read-only hardware description export without embed-bit option. Original bit/DCP/HWH/project exact SHA unchanged; no synthesis/place/route/bitgen rerun. PYNQ package contains separate original bit and matching HWH.'
            paths.extend(p for p in repair.iterdir() if p.is_file())
            paths.append(prior)
        elif rc!=0:raise RuntimeError('Vivado original rc '+str(rc))
        prep=json.loads((BASE/'runs/M357-shell-preparation-01/RESULT.json').read_text(encoding='utf-8'))
        inputs=ROOT/prep['manifest_path'];assert w.sha(inputs)==prep['manifest_sha256']
        staged=json.loads(inputs.read_text(encoding='utf-8'))
        for row in staged['files']:assert w.sha(inputs.parent/row['path'])==row['sha256'],'Staged IP/BD changed'
        generated=list(SHELL.rglob('m89x_runtime_kernel.v'))
        assert len(generated)==1,'Actual shell computational top not unique'
        generated_dir=generated[0].parent;rtl_rows=[]
        for source in sorted((inputs.parent/'ip/hdl/verilog').iterdir()):
            if not source.is_file():continue
            target=generated_dir/source.name
            assert target.is_file() and w.sha(target)==w.sha(source),'Actual generated IP RTL differs: '+source.name
            rtl_rows.append(dict(path=target.relative_to(ROOT).as_posix(),sha256=w.sha(target)))
        assert len(rtl_rows)>=51
        result['actual_generated_ip_rtl']=rtl_rows
        assert json.loads(paths[1].read_text(encoding='utf-8'))['removed'] is True,'Temporary mapping not restored'
        log=paths[2].read_text(encoding='utf-8')
        if export_repair:
            assert 'Bitgen Completed Successfully.' in log and export_error in log
        else:assert 'M357_FULL_SHELL_ROUTED timing_pass=1 build=0x4D333537' in log
        affected={r['ip'] for r in json.loads((BASE/'runs/M357-auxiliary-checkpoint-readback-01/RESULT.json').read_text(encoding='utf-8'))['checkpoints']}
        for p in sorted(SHELL.glob('*.runs/*/runme.log'))+[paths[2]]:
            text=p.read_text(encoding='utf-8',errors='strict');paths.append(p)
            errors=re.findall(r'^ERROR:.*$',text,re.M)
            if export_repair and p==paths[2]:
                assert errors==[export_error] and text.index('Bitgen Completed Successfully.')<text.index(export_error)
                result['retained_export_error']=export_error
                errors=[]
            if errors:
                ip=p.parent.name.removesuffix('_synth_1')
                assert ip in affected and errors==["ERROR: [Common 17-354] Could not open 'C' for writing."]
                line=re.search(r'^source '+re.escape(ip)+r'\.tcl -notrace$',text,re.M)
                assert line and text.index(errors[0])<line.start()
                assert 'Synthesis finished with 0 errors, 0 critical warnings' in text
                result['retained_startup_errors'].append(dict(path=p.relative_to(ROOT).as_posix(),messages=errors))
            assert not re.search(r'^CRITICAL WARNING:',text,re.M),p
        values=(OUT/'shell_route_receipt.txt').read_text(encoding='utf-8')
        result['wns_ns']=float(re.search(r'WNS_NS=([^\s]+)',values)[1]);result['whs_ns']=float(re.search(r'WHS_NS=([^\s]+)',values)[1])
        result['unrouted_nets']=int(re.search(r'UNROUTED_NETS=(\d+)',values)[1])
        assert result['wns_ns']>=0 and result['whs_ns']>=0 and result['unrouted_nets']==0
        timing=(OUT/'impl_timing.rpt').read_text(encoding='utf-8')
        assert 'All user specified timing constraints are met.' in timing
        for check in ('no_clock','constant_clock','pulse_width_clock','unconstrained_internal_endpoints','no_input_delay','no_output_delay','multiple_clock','generated_clocks','loops','partial_input_delay','partial_output_delay','latch_loops'):
            found=re.findall(r'checking '+check+r' \((\d+)\)',timing)
            assert found and all(int(n)==0 for n in found),check
        clocks=re.findall(r'^(clk_pl_\d+)\s+\{[^}]+\}\s+([\d.]+)\s+([\d.]+)',timing,re.M)
        stable_timing=ROOT/'tmp/m120_m89x2_highddr/out/impl_timing_summary.rpt'
        stable_clocks=re.findall(r'^(clk_pl_\d+)\s+\{[^}]+\}\s+([\d.]+)\s+([\d.]+)',stable_timing.read_text(encoding='utf-8'),re.M)
        assert clocks and clocks==stable_clocks, 'Board clock constraints changed'
        result['clock_constraints']=clocks;result['no_unconstrained_endpoints']=True
        paths.append(stable_timing)
        util=(OUT/'impl_utilization.rpt').read_text(encoding='utf-8')
        for label in ('CLB LUTs','CLB Registers','Block RAM Tile','URAM','DSPs','Register as Latch'):
            match=re.search(r'^\|\s*'+re.escape(label)+r'\*?\s*\|\s*([\d.]+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([\d.]+)',util,re.M)
            assert match,label
            used,available=map(float,match.groups());assert used<=available
            result['resources'][label]=dict(used=used,available=available)
        assert result['resources']['Register as Latch']['used']==0
        drc=(OUT/'impl_drc.rpt').read_text(encoding='utf-8')
        assert not re.search(r'\|\s*(?:Error|Critical Warning)\s*\|',drc), 'DRC critical/error violations'
        result['warnings']=re.findall(r'^WARNING:.*$',log,re.M)
        hwh=json.loads((BASE/'runs/M357-hwh-abi-01/RESULT.json').read_text(encoding='utf-8'))
        assert w.sha(ROOT/hwh['candidate_path'])==hwh['candidate_hwh_sha256']
        for name in ('m357_t32.bit','m357_t32.xsa','candidate_routed.dcp'):
            p=(repair if export_repair and name.endswith('.xsa') else OUT)/name;assert p.is_file() and p.stat().st_size>0
            result['artifacts'].append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p)))
        result['matching_hwh_sha256']=hwh['candidate_hwh_sha256']
        if export_repair:
            with zipfile.ZipFile(repair/'m357_t32.xsa') as archive:
                assert not any(name.endswith('.bit') for name in archive.namelist())
                actual=archive.read('qwen25_mixed_gs.hwh')
                assert actual==(ROOT/hwh['candidate_path']).read_bytes()
            result['xsa_full_hwh_exact']=True;result['xsa_embeds_bit']=False
        result['status']='PASS_FULL_SHELL_ROUTED_TIMING'
    except BaseException as exc:result['errors'].append(type(exc).__name__+': '+str(exc))
    paths.extend(SHELL.glob('*.runs/*/runme.log'))
    paths.extend(p for p in OUT.iterdir() if p.is_file() and p.suffix in ('.rpt','.txt'))
    result['evidence']=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(set(paths)) if p.is_file()]
    result['limitation']='Complete board shell implementation only. No candidate board transaction, model/video correctness or measured speedup.'
    w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
    w.sync('M357_full_shell',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
        'M357 完整shell布局布线裁决 '+result['status']+'；资源/建立保持时序/路由/实际日志/HWH核对，原启动文件ERROR保留并绑定独立checkpoint读回。仅整机实现，无候选上板或性能/晋级。证据 '+sha)
    print(json.dumps(dict(status=result['status'],sha256=sha,errors=result['errors'])))
    return 0 if result['status'].startswith('PASS_') else 1
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--export-repair',action='store_true');args=ap.parse_args();raise SystemExit(main(args.export_repair))
