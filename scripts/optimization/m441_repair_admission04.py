"""Fix saved-preparation key mapping; preserve frozen04 and no RTL changes."""
import json
import difflib
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    folder=BASE/'runs/M441-W4-admission-repair-01';ev=folder/'RESULT.json'
    assert not ev.exists()
    prior=BASE/'runs/M441-W4-zero-continuation-04/RESULT.json'
    assert json.loads(prior.read_bytes())['status']=='STOP_M441_W4_ZERO04_AT_FAILED_LEVEL'
    sim=ROOT/'tmp/m441_long_A_mlp_down_04/verilog'
    assert not (sim/'compile.log').exists() and not (sim/'compile_exit.json').exists()
    prep=BASE/'runs/M441-long-A-mlp_down-RTL-preparation-04/RESULT.json'
    r=json.loads(prep.read_bytes());assert r['observer_revision']=='04' and r['variant']=='A'
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert board['latest_m441_long_A_mlp_down_RTL_preparation03']['sha256']==sha(prep)
    assert 'latest_m441_long_A_mlp_down_RTL_preparation04' not in board
    sync('latest_m441_long_A_mlp_down_RTL_preparation04',dict(status=r['status'],sha256=sha(prep),result=prep.relative_to(ROOT).as_posix(),board=False),
         '## M441 A/mlp_down04准备键名对账\n\nSHA '+sha(prep)+'；复用原04准备字节，纠正生成器03键名与执行器04键名不匹配。原尝试在xelab启动前拒绝，0编译/仿真，不放宽SHA检查。')
    source=HERE/'m441_continue04.py';text=source.read_text(encoding='utf-8-sig')
    text=text.replace("WORK=BASE/'runs/M441-W4-zero-continuation-04'","WORK=BASE/'runs/M441-W4-zero-continuation-04b'\nPOLICY=BASE/'runs/M441-W4-admission-repair-01/RESULT.json'")
    text=text.replace("def verified():\n", "def verified():\n    policy=json.loads(POLICY.read_bytes())\n    assert policy['status']=='PREPARED_M441_W4_ADMISSION_KEY_REPAIR_ONLY'\n    for f in policy['new_control_files']:assert sha(ROOT/f['path'])==f['sha256']\n")
    old="""            assert call('prepare_'+v,[PY,'-B',str(HERE/'m441_prepare_long_rtl04.py'),v,'mlp_down'])==0
            prep=BASE/f'runs/M441-long-{v}-mlp_down-RTL-preparation-04/RESULT.json';r=synced(prep)
"""
    new="""            prep=BASE/f'runs/M441-long-{v}-mlp_down-RTL-preparation-04/RESULT.json'
            if not prep.exists():
                assert call('prepare_'+v,[PY,'-B',str(HERE/'m441_prepare_long_rtl04.py'),v,'mlp_down'])==0
            else:
                assert v=='A' and sha(prep)==json.loads(POLICY.read_bytes())['reused_A_preparation_sha256'],'Only saved A preparation may be reused'
            r=synced(prep)
            sync('latest_m441_long_'+v+'_mlp_down_RTL_preparation04',dict(status=r['status'],sha256=sha(prep),result=prep.relative_to(ROOT).as_posix(),board=False),
                 '## M441 '+v+'/mlp_down04准备键名一致性闭合\\n\\nSHA '+sha(prep)+'；实际准备字节未变，执行器要求的04键名精确同步，非降低SHA准入。')
"""
    assert old in text;text=text.replace(old,new)
    text=text.replace('latest_m441_W4_zero04_running','latest_m441_W4_zero04b_running').replace('latest_m441_W4_zero04_result','latest_m441_W4_zero04b_result')
    text=text.replace('    final.update(preparation_sha256=',"    last_observation=observe()\n    held=[j for j in last_observation['jobs'] if j['identity']['status']=='ALIVE']\n    final.update(preparation_sha256=")
    target=HERE/'m441_continue04b.py'
    __import__('ast').parse(text,feature_version=(3,10));atomic(target,text.encode('utf-8'),immutable=True)
    atomic(folder/'CONTROL_DIFF.patch',''.join(difflib.unified_diff(source.read_text(encoding='utf-8-sig').splitlines(True),text.splitlines(True),fromfile=str(source),tofile=str(target))).encode('utf-8'),immutable=True)
    result=dict(status='PREPARED_M441_W4_ADMISSION_KEY_REPAIR_ONLY',board=False,RTL_changed=False,arithmetic_changed=False,
        parent_protocol_sha256=sha(BASE/'runs/M441-independent-protocol-04/PREPARATION.json'),
        prior_stop_sha256=sha(prior),reused_A_preparation_sha256=sha(prep),
        prior_precompile_wrapper_log_sha256=sha(BASE/'runs/M441-W4-zero-continuation-04/compile_A.log'),
        root_cause='Generator published correct revision04 bytes under preparation03 BOARD key; execution requires preparation04 key',
        original_xelab_started=False,prior_simulation_started=False,extra_samples=False,
        old_control_sha256=sha(source),new_control_files=[dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target))],
        final_owner_snapshot_fix='Record all currently alive jobs on failed stage; never kill/free them',
        next='Same untouched W4 Zero04 inputs; actual compile and collect once, then A/B simulation once; no pressure/board.')
    atomic(ev,encoded(result),immutable=True)
    sync('latest_m441_W4_admission_repair01',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         '## M441 W4版本键名准入修复（2026-10-08）\n\nSHA '+sha(ev)+'；03键名遗漏导致04执行器在xelab前拒绝，原失败及源码保留。保存准备文件按正确04键同步，独立控制器04b复用仅此A准备；原SHA/RTL/数学/固定次数不变，失败末态包括所有活跃owner。0旧仿真重跑/板端，下一步首次实际编译同一04输入。')
    print(result['status'],sha(ev))

if __name__=='__main__':main()
