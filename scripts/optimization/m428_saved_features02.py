"""Two immutable saved features, exact original and accepted M427 late half."""
import hashlib
import io
import json
import os
import stat
from pathlib import Path
import numpy as np


def read_owned(path, size, digest):
    p = Path(path)
    before = p.lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns,
                          s.st_ctime_ns, s.st_mode, s.st_nlink, s.st_uid)
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0
            or before.st_nlink != 1 or before.st_size != size or not 0 < size <= 2 << 20):
        raise ValueError('Saved feature ownership/type/size differs')
    raw = p.read_bytes()
    if identity(before) != identity(p.lstat()) or len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Saved feature identity/SHA differs')
    return raw


def load_features(plan, folders=None):
    dirs = folders or {k: Path(v) for k, v in plan['feature_directories'].items()}
    if plan['selected_layers'] != list(range(13, 24)) or plan['accepted_range'] != 'late_13_23':
        raise ValueError('Only frozen accepted late half allowed')
    original = json.loads(read_owned(dirs['original'] / 'BOARD_RESULT.json',
                         plan['M426_raw_bytes'], plan['M426_raw_sha256']))
    candidate = json.loads(read_owned(dirs['candidate'] / 'BOARD_RESULT.json',
                          plan['M427_raw_bytes'], plan['M427_raw_sha256']))
    if (original['status'] != 'REJECT_M426_ALL22_FEATURE_RANGE'
            or type(original['gate_return_code']) is not int or original['gate_return_code'] != 0
            or original['original_reference_pass'] is not True
            or original['visual_owner_closed'] is not True or original['bindings_restored'] is not True
            or original['overlay_loaded'] or original['dma_allocations'] or original['fpga_transactions']):
        raise ValueError('Original saved reference prerequisite differs')
    if (candidate['status'] != 'PASS_M427_HALF_FEATURES_TASK_PENDING'
            or type(candidate['gate_return_code']) is not int or candidate['gate_return_code'] != 0
            or candidate['software_screen_completed'] is not True
            or candidate['original_reference_pass'] is not True
            or candidate['baseline_source_sha256'] != plan['M426_raw_sha256']
            or candidate['visual_owner_closed'] is not True or candidate['bindings_restored'] is not True
            or candidate['overlay_loaded'] or candidate['dma_allocations'] or candidate['fpga_transactions']
            or candidate['language_forward_calls'] or candidate['temperature_measurement_enabled']
            or 'late_13_23' not in candidate['feature_pass_ranges']):
        raise ValueError('Accepted software feature prerequisite differs')
    matches = [r for r in candidate['ranges'] if r['name'] == 'late_13_23']
    if len(matches) != 1:
        raise ValueError('Unique accepted feature range required')
    row = matches[0]
    q = row['full_visual_quality']; m = q['metrics']
    if (row['selected_layers'] != list(range(13, 24)) or row['feature_screen_pass'] is not True
            or q['feature_screen_pass'] is not True
            or q['thresholds'] != {'maximum_relative_l2': .02, 'minimum_cosine': .999, 'minimum_token_cosine': .995}
            or not (m['relative_l2'] <= .02 and m['cosine'] >= .999 and m['min_token_cosine'] >= .995)):
        raise ValueError('Unchanged feature criteria prerequisite differs')
    original_saved = original['retained_features'][0]
    candidate_saved = row['saved_feature']
    expected = [dict(path=original_saved['path'], file_bytes=original_saved['bytes'],
                     file_sha256=original_saved['sha256'], tensor=original['original_visual'], source='original'),
                dict(path=candidate_saved['path'], file_bytes=candidate_saved['bytes'],
                     file_sha256=candidate_saved['sha256'], tensor=row['candidate_visual'], source='candidate')]
    if (expected != plan['features'] or [r['path'] for r in expected] !=
            ['original_visual.npy', 'late_13_23_candidate_visual.npy']
            or candidate['original_visual'] != original['original_visual']):
        raise ValueError('Saved feature manifest differs')
    arrays = []; identities = []
    for r in expected:
        p = dirs[r['source']] / r['path']
        if r['file_bytes'] != 1003648:
            raise ValueError('Full fixed feature file required')
        x = np.load(io.BytesIO(read_owned(p, r['file_bytes'], r['file_sha256'])), allow_pickle=False)
        if x.shape != (98, 2560) or x.dtype != np.float32 or tensor(x) != r['tensor']:
            raise ValueError('Complete saved feature tensor differs')
        x.flags.writeable = False
        arrays.append(x)
        identities.append(dict(path=str(p), file_sha256=r['file_sha256'], tensor=r['tensor']))
    return arrays, identities
