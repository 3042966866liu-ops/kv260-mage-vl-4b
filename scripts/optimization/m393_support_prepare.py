"""Generate text support from verified layer recovery, then actual checks run."""
from m351_workflow import HERE,atomic

def main():
    s=(HERE/'m392_support.py').read_text(encoding='utf-8').replace('M392','M393').replace('m392','m393')
    s=s.replace('M385-ps-layer-02','M386-ps-text-01').replace('M385-ps-layer-board-01','M386-ps-text-board-01')
    s=s.replace('M393-silu-layer','M393-silu-text').replace('latest_m393_silu_layer_','latest_m393_silu_text_')
    s=s.replace('m385_ps_layer_candidate_01','m386_ps_text_candidate_01').replace('m385_control.ps1','m386_control.ps1')
    s=s.replace('sealed-DMA-SiLU-workspace-single-layer-numerical','sealed-DMA-SiLU-workspace-fixed-text-numerical').replace('PASS_M393_SILU_LAYER_NUMERICAL','PASS_M393_SILU_TEXT_NUMERICAL')
    s=s.replace('component_prerequisite_sha256','silu_layer_prerequisite_sha256').replace('377ac2cf8b082eadbffad43c440ff32fcb24d377280a96e6e56f9d07f2efb5b4','8eb467882777edd2ff8d9b11e6b02077a58b72f20a1d401478ac67502b35a63d')
    s=s.replace('calls=1,closed=True','calls=36,closed=True').replace("events=['before-layer-workspace-scope','before-silu','after-mlp-down-before-reuse','before-workspace-close']","events=['before-layer-workspace-scope']+['before-silu','after-mlp-down-before-reuse']*36+['before-workspace-close']").replace('workspace_bytes=6187008','workspace_bytes=1167360')
    s=s.replace('test_m393_silu_scope.py','test_m393_silu_scope.py').replace('Ran 9 tests','Ran 6 tests').replace('actual_layer_gate_lifetime_tests=9','actual_full_prefill_gate_lifetime_tests=6')
    s=s.replace("'m393_silu_scope.py']","'m393_silu_scope.py','m393_silu_workspace.py']")
    s=s.replace('PASS_OFFLINE_SILU_LAYER_CONTROL_RECOVERY','PASS_OFFLINE_SILU_TEXT_CONTROL_RECOVERY')
    s=s.replace("rejected_draft_binding='Closed function initially raised NameError after callback removal; entry guard added before any family, tested before freeze',\n               rejected_package_01='Wrong remote prior package name, recorded and immutable; repaired02 only, no board command'","reused_layer_source_entry_guard=True,extended_only_fixed30_or159_workspace=True,actual_head_observer_same_SHA=True")
    a=s.index("         f'## M393");z=s.index("    print(json.dumps(value",a)
    s=s[:a]+"         f'## M393 SiLU固定文本实际调用/回收支持（2026-10-04）\\n\\n6项真实原36层Prefill/30与159尺寸激活数学/实际gate调用/晚层故障与head完成屏障检查、{negative}回收负例、8实际assembly及旧远程目录/PS选择；SHA {d}。Attention/PL/内存明确替身，非本级文本数值或性能。下一步同COM3 sudo后一次原固定30文本/完整head数值门禁。')\n"+s[z:]
    atomic(HERE/'m393_support.py',s.encode('utf-8'))
    print('M393_DRAFT_SUPPORT_GENERATED')

if __name__=='__main__':main()
