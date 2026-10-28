"""Preserve interface rejection; correct M273 three-argument NumPy interface."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def main():
    old=read(PREP/'RESULT.json');failed=read(FIT/'RESULT.json')
    assert failed['original_rc']==1 and failed['prefix_forwards']==0 and not failed['requests']
    assert 'merged_visual_tokens' in failed['traceback']
    newprep=R/(PREFIX+'-protocol-02');assert not newprep.exists()
    additions={}
    s=(H/'fit.py').read_text(encoding='utf-8')
    anchor='from common import *\n'
    replacement=anchor+"PREP=R/(PREFIX+'-protocol-02');FIT=R/(PREFIX+'-fit-02')\n"
    assert s.count(anchor)==1;s=s.replace(anchor,replacement)
    assert s.count('try:runtime(**arrays)')==1
    s=s.replace('try:runtime(**arrays)',"try:runtime(arrays['pixel_values'].numpy(),arrays['image_grid_thw'].numpy(),arrays['patch_positions'].numpy())")
    additions['fit02.py']=s
    s=(H/'features.py').read_text(encoding='utf-8')
    s=s.replace(anchor,anchor+"PREP=R/(PREFIX+'-protocol-02');FIT=R/(PREFIX+'-fit-02')\n")
    oldcall='output=runtime(**x).detach().float().numpy().copy()'
    assert s.count(oldcall)==1
    s=s.replace(oldcall,"output=runtime(x['pixel_values'].numpy(),x['image_grid_thw'].numpy(),x['patch_positions'].numpy()).copy()")
    additions['features02.py']=s
    s=(H/'quality.py').read_text(encoding='utf-8');s=s.replace('M523-PS-V2-V3-V6-3072-protocol-01/RESULT.json','M523-PS-V2-V3-V6-3072-protocol-02/RESULT.json')
    additions['quality02.py']=s
    s=(H/'host.py').read_text(encoding='utf-8')
    s=s.replace(anchor,anchor+"PREP=R/(PREFIX+'-protocol-02');FIT=R/(PREFIX+'-fit-02')\n")
    s=s.replace("'-host-01'","'-host-03'").replace("+'_host01'","+'_host03'").replace("target=H/(stage+'.py')","target=H/(stage+'02.py')")
    additions['host03.py']=s
    for name,s in additions.items():compile(s,name,'exec');assert not (H/name).exists()
    for name,s in additions.items():(H/name).write_bytes(s.encode())
    frozen=dict(old['frozen'])
    for file in [H/'prepare02.py']+[H/n for n in additions]:frozen[relative(file)]=sha(file)
    rejected=[PREP/'RESULT.json',FIT/'RESULT.json',R/(PREFIX+'-fit-host-01')/'RESULT.json',R/(PREFIX+'-fit-host-02')/'RESULT.json']
    for file in rejected:frozen[relative(file)]=sha(file)
    p=dict(old,frozen=frozen,interface_fix='Explicit original three arguments, preprocess metadata not forwarded; actual original NumPy result retained.',
        rejected_fit_sha256=sha(FIT/'RESULT.json'),original_contract_sha256=sha(PREP/'CONTRACT.json'),source_sha256=sha(__file__),
        correction_before_first_prefix_forward=True,no_completed_model_answer_rerun=True)
    save(newprep/'RESULT.json',p)
    from m455456_workflow02 import synchronized
    h=sha(newprep/'RESULT.json');synchronized('latest_m523_PS_V236_3072_protocol02',dict(status=p['status'],result=relative(newprep/'RESULT.json'),sha256=h,board=False),
        '## M523 PS三层调用接口拒绝及本级修正\n\nRESULT SHA '+h+'；原fit01在首个前向前因多传merged_visual_tokens拒绝，原码切片已精确保存、0训练捕获/0完成模型回答。host01 WSL准入拒绝、host02原1与raw均保全；独立fit02仅显式原三参数/NumPy返回接口，组/算术/R1/任务/门不变。0完成模型重跑/0板命令，42676保持。')
    print('FROZEN_INTERFACE_REPAIR_BEFORE_FIRST_FORWARD',h,flush=True)
if __name__=='__main__':main()
