"""OP01 raw four-second CFR video -> four real-PTS RGB frames -> prompt.

No inference, caching, or browser decode. This version deliberately rejects
missing/irregular PTS instead of inventing timestamps from frame indices.
"""
import math
from pathlib import Path
import numpy as np
from measurement import sha256

TARGET_TIMES = (0.5, 1.5, 2.5, 3.5)


def nearest_indices(timestamps, targets=TARGET_TIMES, max_error_s=0.1):
    times = np.asarray(timestamps, np.float64)
    if (times.ndim != 1 or times.size < 4 or not np.isfinite(times).all()
            or np.any(np.diff(times) <= 0)):
        raise ValueError('Missing, duplicate, or non-monotonic presentation timestamps')
    picked = [int(np.argmin(np.abs(times - target))) for target in targets]
    if len(set(picked)) != 4 or any(abs(times[i] - t) > max_error_s for i,t in zip(picked, targets)):
        raise ValueError('Four distinct target frames not available')
    return picked


def render_prompt(question, sample_times_s):
    question = question.strip()
    times = list(sample_times_s)
    if not question or len(question) > 3000:
        raise ValueError('Question length outside 1..3000')
    if len(times) != 4 or any(not math.isfinite(t) or not 0 <= t < 4 for t in times):
        raise ValueError('Four valid timestamps required')
    if any(a >= b for a,b in zip(times, times[1:])):
        raise ValueError('Frame order must be increasing')
    frames = ''.join(f'<{t:.3f} seconds><|vision_start|>' + '<|image_pad|>' * 196 + '<|vision_end|>' for t in times)
    return ('<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n'
            f'<|im_start|>user\n{frames}{question}<|im_end|>\n<|im_start|>assistant\n')


def decode_raw_video(path, expected_sha256):
    import cv2
    path = Path(path)
    if not path.is_file() or not 1 <= path.stat().st_size <= 32 * 1024 * 1024:
        raise ValueError('Raw video missing or size outside bounded 32MiB input')
    if sha256(path) != expected_sha256:
        raise ValueError('Raw input SHA-256 mismatch')
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError('Video codec could not open input')
    selected = [None] * 4
    distances = [float('inf')] * 4
    times, source_shapes = [], set()
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(fps) or not 5 <= fps <= 60 or not 4 <= count <= 240:
            raise ValueError('Invalid bounded CFR video metadata')
        if abs(count / fps - 4.0) > 0.001:
            raise ValueError('Input must be exactly four seconds (CFR count/rate)')
        for ordinal in range(count):
            ok, bgr = capture.read()
            if not ok:
                raise ValueError('Video ended before declared frame count')
            timestamp = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
            if (not math.isfinite(timestamp) or timestamp < 0
                    or (times and timestamp <= times[-1])):
                raise ValueError('Decoder did not provide increasing real presentation timestamps')
            # Validate CFR timestamps; never use nominal ordinal/fps as measured PTS.
            if abs(timestamp - ordinal / fps) > 0.002:
                raise ValueError('Non-CFR or nonzero-origin video is unsupported by this frozen adapter')
            if bgr.ndim != 3 or bgr.shape[2] != 3 or bgr.shape[0] * bgr.shape[1] > 1920 * 1080:
                raise ValueError('Unsupported source-frame geometry')
            times.append(timestamp)
            source_shapes.add(tuple(bgr.shape))
            for index, target in enumerate(TARGET_TIMES):
                distance = abs(timestamp - target)
                if distance < distances[index]:
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    if rgb.shape[:2] != (448, 448):
                        rgb = cv2.resize(rgb, (448, 448), interpolation=cv2.INTER_AREA)
                    selected[index] = np.ascontiguousarray(rgb)
                    distances[index] = distance
        if capture.read()[0]:
            raise ValueError('Video contains undeclared additional frames')
        indices = nearest_indices(times, max_error_s=0.5 / fps + 0.002)
        return np.stack(selected), dict(raw_sha256=expected_sha256, codec_backend=capture.getBackendName(),
            decoder_version=cv2.__version__, fps=fps, decoded_frame_count=len(times),
            duration_s=count/fps, duration_basis='validated_CFR_count_and_rate',
            target_times_s=list(TARGET_TIMES), actual_frame_times_s=[times[i] for i in indices],
            selected_frame_indices=indices, source_shapes=[list(x) for x in sorted(source_shapes)],
            all_presentation_timestamps_s=times, resized_shape=[4,448,448,3],
            actual_decode_location='caller_process', video_file_bytes=path.stat().st_size)
    finally:
        capture.release()
