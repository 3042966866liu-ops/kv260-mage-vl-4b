"""Draft text controller/receipt, reusing verified single-source machinery."""
from m351_workflow import HERE,atomic

def main():
    for src,dst in [('m392_control.ps1','m393_control.ps1'),('m392_workflow.py','m393_workflow.py')]:
        s=(HERE/src).read_text(encoding='utf-8-sig').replace('M392','M393').replace('m392','m393')
        s=s.replace('M393-silu-layer-02','M393-silu-text-01').replace('M385-ps-layer-02','M386-ps-text-01')
        s=s.replace('m393_silu_layer_candidate_02','m393_silu_text_candidate_01').replace('run_m393_silu_layer.sh','run_m393_silu_text.sh')
        s=s.replace('M393_ENABLE_SILU_LAYER','M393_ENABLE_SILU_TEXT').replace('latest_m393_silu_layer_','latest_m393_silu_text_')
        s=s.replace('M393-silu-layer-board-01','M393-silu-text-board-01').replace('M393-silu-layer-transfer-01','M393-silu-text-transfer-01')
        atomic(HERE/dst,s.encode('utf-8'))
    print('M393_DRAFT_CONTROL_READY')

if __name__=='__main__':main()
