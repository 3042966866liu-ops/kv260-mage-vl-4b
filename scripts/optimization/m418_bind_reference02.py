"""Bind unexecuted lower gates to the repaired reference and allocation proof."""
from m351_workflow import HERE,atomic

def main():
    source=(HERE/'m418_prepare.py').read_text(encoding='utf-8')
    source=source.replace('latest_m417_reference_board','latest_m417_reference_board02').replace('latest_m417_reference_closure','latest_m417_reference_closure02').replace('m417_layer13_reference_01','m417_layer13_reference_02').replace("'m418_prepare.py'","'m418_prepare02.py'").replace("'m418_control.ps1'","'m418_control02.ps1'")
    anchor="    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())"
    assert source.count(anchor)==1
    check="""
    allocation_e=b['latest_m418_allocation_component']
    assert sha(ROOT/allocation_e['result'])==allocation_e['sha256']
    allocation=json.loads((ROOT/allocation_e['result']).read_bytes())
    assert allocation['source_sha256']==sha(HERE/'m418_probe.py') and allocation['status']=='PASS_M418_ACTUAL_OWNER_ALLOCATION_COMPONENT'
    assert all(allocation_e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
"""
    source=source.replace(anchor,anchor+check)
    source=source.replace('component=component,board_run=False','component=component,allocation_component=allocation,allocation_component_sha256=allocation_e[\'sha256\'],board_run=False')
    atomic(HERE/'m418_prepare02.py',source.encode('utf-8'),immutable=True)
    control=(HERE/'m418_control.ps1').read_text(encoding='utf-8').replace('latest_m417_reference_board','latest_m417_reference_board02').replace('latest_m417_reference_closure','latest_m417_reference_closure02')
    atomic(HERE/'m418_control02.ps1',control.encode('utf-8'),immutable=True)
    support=(HERE/'m418_support.py').read_text(encoding='utf-8').replace('m418_control.ps1','m418_control02.ps1').replace('m418_support.py','m418_support02.py')
    atomic(HERE/'m418_support02.py',support.encode('utf-8'),immutable=True)
    print('M418_BOUND_TO_REPAIRED_REFERENCE02_NOT_EXECUTED')

if __name__=='__main__':main()
