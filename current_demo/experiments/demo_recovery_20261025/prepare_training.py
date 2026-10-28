from common_recovery import *
def main():
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'));capture=RUNS/(PREFIX+'-teacher-capture-01/RESULT.json');c=read(capture)
    assert c['original_rc']==0 and len(c['teacher_requests'])==8
    for name in ('train_local.py','training_host.py','train_entry.py'):compile((HERE/name).read_text(encoding='utf-8'),name,'exec')
    value=dict(status='FROZEN_41_BLOCK_LOCAL_LORA_SHORT_TRAINING',teacher_capture_sha256=sha(capture),training_source_sha256=sha(HERE/'train_local.py'),source_sha256=sha(__file__),blocks=41,steps_per_block=8,scope=p['first_phase'],
        precision='FP32 differentiable GPU block surrogate on current dequantized/cropped weights; local teacher-forced targets. No claim identical to M455 forward or full end-to-end training.',
        export='Merge A/B once; existing mixed-bit full-range quantizer, per-module original2/3/4 bits, G64 and FP16 scales/orientation; chunk64 rows, real code packing roundtrip. Refit scales/orientations permitted new version, no inference adapter branch. Lowering/CSim and board gates still pending.',
        data='Only8 fit requests. Local loss changes do not prove composed student decisions or independent quality.',heldout_opened=False,board_actions=0)
    save(RUNS/(PREFIX+'-training-protocol-01/RESULT.json'),value);print(value['status'],sha(HERE/'train_local.py'),flush=True)
if __name__=='__main__':main()
