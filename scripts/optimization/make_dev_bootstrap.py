"""Three controlled four-second development videos; not held-out evaluation.

Run in the existing WSL environment with OpenCV. Truth follows render state,
never model outputs. Only neutral input IDs and questions reach the model.
"""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw
from measurement import sha256, write_json
from sys_video_input import decode_raw_video, render_prompt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'deployment/mage_vl4b/optimization_v1/datasets/dev_bootstrap_v1'
FPS, COUNT = 12, 48
OUT.mkdir(exist_ok=False)
rows, truth, decode_checks = [], [], []
for ordinal, category in enumerate(('motion', 'order', 'detail'), 1):
    name = f'dev-{ordinal:04d}'
    path = OUT / (name + '.mp4')
    video = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), FPS, (448,448))
    if not video.isOpened():
        raise RuntimeError('Existing OpenCV encoder cannot create MPEG4; no substitute result')
    state = {'fps': FPS, 'frame_count': COUNT, 'duration_s': 4.0, 'category': category}
    try:
        for frame in range(COUNT):
            t = frame / FPS
            image = Image.new('RGB', (448,448), (240,240,240))
            draw = ImageDraw.Draw(image)
            if category == 'motion':
                x = round(60 + 328 * frame/(COUNT-1))
                draw.ellipse((x-32,192,x+32,256), fill=(210,35,35))
                state.update(initial_center_x=60, final_center_x=388, shape='red circle')
            elif category == 'order':
                if 0.2 <= t < 1.2:
                    draw.ellipse((120,160,232,272), fill=(35,65,210))
                if 2.1 <= t < 4:
                    draw.rectangle((240,160,352,272), fill=(230,205,20))
                state.update(blue_circle_onset_s=0.2, yellow_square_onset_s=2.1)
            else:
                draw.polygon([(64,278),(184,278),(124,160)], fill=(30,150,65))
                draw.ellipse((268,160,380,272), fill=(210,35,35))
                state.update(green_triangle_center_x=124, red_circle_center_x=324)
            video.write(cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR))
    finally:
        video.release()
    if category == 'motion':
        question = 'In which direction does the red circle move, left to right or right to left?'
        answer = 'left to right' if state['final_center_x'] > state['initial_center_x'] else 'right to left'
    elif category == 'order':
        question = 'Which appears first, the blue circle or the yellow square?'
        answer = 'blue circle' if state['blue_circle_onset_s'] < state['yellow_square_onset_s'] else 'yellow square'
    else:
        question = 'Which shape is to the left of the red circle?'
        answer = 'green triangle' if state['green_triangle_center_x'] < state['red_circle_center_x'] else None
    digest = sha256(path)
    frames, evidence = decode_raw_video(path, digest)
    evidence.update(sample_id=name, decoded_rgb_sha256=hashlib.sha256(frames.tobytes()).hexdigest())
    rows.append(dict(sample_id=name, file=path.name, sha256=digest, question=question,
                     provenance='controlled_render', split='dev'))
    truth.append(dict(sample_id=name, category=category, answer=answer, render_state=state,
                      provenance='deterministic_script_render_state', not_human_annotation=True))
    decode_checks.append(evidence)
    panel = Image.new('RGB', (448*4,448))
    for i,frame in enumerate(frames):
        panel.paste(Image.fromarray(frame), (448*i,0))
    panel.save(OUT / f'{name}_contact.png')
write_json(OUT / 'input_manifest.json', dict(schema_version=1, samples=rows,
    generator_sha256=sha256(__file__), decoder_sha256=sha256(Path(__file__).with_name('sys_video_input.py')),
    evaluated=False, use='OP01 development only; not formal or held-out quality'))
write_json(OUT / 'truth_dev.json', dict(samples=truth))
write_json(OUT / 'decode_validation.json', dict(status='PASS', location='WSL_CPU', records=decode_checks,
    board_executed=False, semantic_quality_evaluated=False))
print(json.dumps(dict(status='PASS', scope='three controlled dev inputs plus real-codec decode, not model/board',
                     directory=str(OUT), video_bytes=[(OUT/x['file']).stat().st_size for x in rows])))
