"""Freeze paired weak-teacher/strong-student training policy, no training yet."""
from common_recovery import *
def main():
    p=read(RUNS/(PREFIX+'-protocol-01/RESULT.json'))
    policy=dict(status='FROZEN_PAIRED_PHOTOMETRIC_AUGMENTATION_FOR_NEXT_RECOVERY',
        user_authorization='2026-10-25: give student harder-to-recognize versions of same videos while teacher learns same task',
        teacher='Frozen parent A on original sampled frame, cached targets unchanged',student='Same original frame index and geometry, deterministic photometric perturbation only',
        original_input_tokens=128,paired_layer_targets_spatially_aligned=True,
        initial_curriculum=[dict(stage=0,name='clean',gamma=[1,1],brightness=[1,1],JPEG_quality=[100,100],gaussian_noise_std_RGB255=[0,0]),
                            dict(stage=1,name='weak',gamma=[.95,1.05],brightness=[.95,1.05],JPEG_quality=[92,96],gaussian_noise_std_RGB255=[0,.5]),
                            dict(stage=2,name='moderate',gamma=[.90,1.10],brightness=[.90,1.05],JPEG_quality=[85,92],gaussian_noise_std_RGB255=[.5,1.5])],
        forbidden_initial_changes=['No spatial crop','No occlusion or cutout','No object removal','No timestamp shift','No teacher/student source mismatch','No forced Yes/No output'],
        training_scope=[r['id'] for r in p['train_requests']],reserved_cal_augmentation=False,test_heldout_augmentation=False,
        label_policy='Keep original registered labels. Augmented positives must retain visible object evidence; if not confirmed, do not use that view for positive CE. Original ambiguous cal02t1 is flagged, not silently relabeled or treated as independent evidence.',
        first_safe_augmentation_scope=['cal_00_t0','cal_00_t1','cal_04_t0','cal_04_t1'],
        next_experiment='Matched no-augmentation versus progressive-augmentation students, same initialization/optimizer/full-student objective; judge composed first-token answers, not only local MSE.',
        limitation='Local41-block KD short trial degraded composed answers; adding hard examples alone is not established as a fix. Need student-path targets/end-to-end decision loss and target-format comparison.',
        parameters_trained_now=0,board_actions=0,heldout_opened=False)
    out=RUNS/(PREFIX+'-augmentation-policy-01/RESULT.json');save(out,policy)
    print(policy['status'],sha(out),flush=True)
if __name__=='__main__':main()
