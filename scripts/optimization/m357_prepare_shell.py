"""Stage a fresh board shell only after all new-circuit RTL gates are synchronized."""
import copy
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
OUT=ROOT/'tmp/m357_shell_inputs_01'
NS={'s':'http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009'}

def main():
    gates=[('M356-stable-q-rtl-02','PASS_FULL_FROZEN_Q_RTL'),
           ('M357-candidate-q-rtl-02','PASS_FULL_FROZEN_Q_RTL'),
           ('M357-max-fifo-rtl-03','PASS_MAX_DESCRIPTOR_FIFO_RTL'),
           ('M357-timeout-rtl-01','PASS_EXPECTED_RTL_TIMEOUT_NEGATIVE'),
           ('M357-core-ooc-01','PASS_ISOLATED_CORE_ROUTED_TIMING'),
           ('M357-activation-bank-csim-01','PASS_NUMERICAL_CSIM')]
    proof=[]
    for name,status in gates:
        p=BASE/'runs'/name/'RESULT.json'
        r=json.loads(p.read_text(encoding='utf-8'));sha=w.sha(p)
        # Preserve the exact CSim receipt's own PASS status rather than guessing it.
        if name.endswith('csim-01'):
            assert r['status'].startswith('PASS_') and r.get('board',False) is False
        else:assert r['status']==status,(name,r['status'])
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
            assert sha in (ROOT/n).read_text(encoding='utf-8-sig'),(name,n)
        proof.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha,status=r['status']))
    if OUT.exists():raise RuntimeError('Existing shell staging; inspect only')
    bd=ROOT/'tmp/m120_m89x2_highddr/mage_m120_m89x2_highddr.srcs/sources_1/bd/qwen25_mixed_gs/qwen25_mixed_gs.bd'
    original=json.loads(bd.read_text(encoding='utf-8'));candidate=copy.deepcopy(original)
    cell=candidate['design']['components']['mage_m120_m89x2_0']
    assert cell['vlnv']=='tellme.local:hls:m89x_runtime_kernel:1.0'
    ip=ROOT/'tmp/m357_hls_project_02/hls/impl/ip'
    xml=ET.parse(ip/'component.xml').getroot()
    assert [xml.find('s:'+n,NS).text for n in ('vendor','library','name','version')]==['xilinx.com','hls','m89x_runtime_kernel','1.0']
    cell['vlnv']='xilinx.com:hls:m89x_runtime_kernel:1.0'
    revision=next((e.text for e in xml.iter() if e.tag.endswith('}coreRevision')),None)
    if revision is None:raise RuntimeError('Candidate IP revision absent')
    cell['ip_revision']=revision
    normalized=copy.deepcopy(candidate)
    normalized['design']['components']['mage_m120_m89x2_0']['vlnv']=original['design']['components']['mage_m120_m89x2_0']['vlnv']
    normalized['design']['components']['mage_m120_m89x2_0']['ip_revision']=original['design']['components']['mage_m120_m89x2_0']['ip_revision']
    assert normalized==original,'Unexpected board topology/settings change'
    refs=sorted(set(e.text.replace('\\','/') for e in xml.findall('s:fileSets/s:fileSet/s:file/s:name',NS)))
    for rel in refs:
        p=(ip/rel).resolve();p.relative_to(ip.resolve())
        assert p.is_file() and not p.is_symlink(),rel
        assert '__pycache__' not in p.parts and p.suffix not in ('.pyc','.log','.jou'),rel
    # Export adds only synthesis-excluded deadlock observers to the tested top.
    source=ROOT/'tmp/m357_hls_project_02/hls/syn/verilog'
    same=[];instrumented=[]
    for p in sorted((ip/'hdl/verilog').glob('*.v')):
        q=source/p.name
        if not q.exists():
            assert p.name in ('m89x_runtime_kernel_hls_deadlock_detection_unit.v','m89x_runtime_kernel_hls_deadlock_idx0_monitor.v')
            continue
        if p.read_bytes()==q.read_bytes():same.append(p.name);continue
        assert p.name=='m89x_runtime_kernel.v'
        extra='''\nreg find_df_deadlock = 0;
// synthesis translate_off
`include "m89x_runtime_kernel_hls_deadlock_detector.vh"
// synthesis translate_on

reg find_kernel_block = 0;
// synthesis translate_off
`include "m89x_runtime_kernel_hls_deadlock_kernel_monitor_top.vh"
// synthesis translate_on
'''
        a=p.read_text(encoding='utf-8');b=q.read_text(encoding='utf-8')
        assert a.count(extra)==1
        # Export inserts blank lines around the exact observer block. Ignore
        # only empty lines; every computational/nonblank source line stays exact.
        assert [line for line in a.replace(extra,'').splitlines() if line.strip()]==[line for line in b.splitlines() if line.strip()]
        instrumented.append(p.name)
    assert len(same)==50 and instrumented==['m89x_runtime_kernel.v']
    OUT.mkdir();(OUT/'ip').mkdir()
    for rel in refs+['component.xml']:
        dest=OUT/'ip'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ip/rel,dest)
    w.atomic(OUT/'qwen25_mixed_gs.bd',w.encoded(candidate))
    manifest=dict(schema='m357-shell-inputs-v1',original_bd_sha256=w.sha(bd),
        changed_bd_fields=['kernel.vlnv','kernel.ip_revision'],unchanged_board_topology=True,
        candidate_ip_component_sha256=w.sha(ip/'component.xml'),
        identical_computational_rtl_modules=len(same),top_only_synthesis_excluded_observers=instrumented,
        prerequisites=proof,files=[dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()])
    manifest['file_count']=len(manifest['files']);manifest['total_bytes']=sum(r['bytes'] for r in manifest['files'])
    w.atomic(OUT/'INPUT_MANIFEST.json',w.encoded(manifest),immutable=True)
    result=dict(status='PREPARED_FRESH_SHELL_INPUTS_AFTER_RTL_GATES',build_id='0x4D333537',
        manifest_sha256=w.sha(OUT/'INPUT_MANIFEST.json'),manifest_path=(OUT/'INPUT_MANIFEST.json').relative_to(ROOT).as_posix(),
        board=False,shell_executed=False,promoted=False,prerequisites=proof,
        original_bd_sha256=manifest['original_bd_sha256'],same_computational_rtl=50,
        top_export_delta='Only unused simulation deadlock observer declarations/includes; no computational RTL change',
        file_count=manifest['file_count'],total_bytes=manifest['total_bytes'],
        rejected_preparation='Initial exact observer subtraction left export-only blank lines and correctly stopped before staging; compare nonblank lines exact after subtracting the one known synthesis-excluded observer block. No DUT/export change or hardware rerun.')
    ev=BASE/'runs/M357-shell-preparation-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
    w.sync('M357_shell_preparation',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
        'M357 新电路前级CSim/header/完整Q/最大FIFO背压/超时/核心时序证据闭合后准备独立shell输入，保留稳定BD全部连线/时钟/地址，仅替换候选IP身份及revision；干净白名单'+str(result['file_count'])+'文件。尚未shell实现/候选上板。证据 '+sha)
    print(json.dumps(dict(status=result['status'],sha256=sha,manifest_sha256=result['manifest_sha256'])))
if __name__=='__main__':main()
