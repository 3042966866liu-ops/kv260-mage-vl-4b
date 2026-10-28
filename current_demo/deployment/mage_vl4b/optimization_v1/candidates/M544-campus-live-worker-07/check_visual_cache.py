"""Actual six frozen PS matrices and lossless evidence writer; zero model/device."""
import gc
import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from visual_cache_profiler import ObservedDecodeBudget
from compact_log_output import LogBudget, read_saved


def check(package, fixtures=None):
    package = Path(package)
    plan = json.loads((package / 'PS_NATIVE_PLAN.json').read_bytes())
    matrices = []
    files = []
    for row in plan['selected']:
        file = package / row['codes']['path']
        assert hashlib.sha256(file.read_bytes()).hexdigest() == row['codes']['sha256']
        files.append(dict(path=str(file), sha256=row['codes']['sha256']))
        with np.load(file, allow_pickle=False) as z:
            for part in ('fc1', 'fc2'):
                matrices.append((str(row['index']) + part, z[part+'_codes'].copy(), z[part+'_scales'].copy()))
    assert len(matrices) == 6 and all(c.size * 4 == 12 << 20 for _, c, _ in matrices)
    hashes = {}; arms = {}
    for arm, limit in [('A', 32 << 20), ('B', 80 << 20)]:
        budget = ObservedDecodeBudget(limit)
        requests = []
        for repeat in range(2):
            budget.events.clear()
            for key, codes, scales in matrices:
                dense = budget.obtain(key, codes, scales)
                direct = np.multiply(codes.astype(np.float32), scales.astype(np.float32)[..., None], dtype=np.float32).reshape(len(codes), -1)
                assert np.array_equal(dense.view(np.uint32), direct.view(np.uint32))
                digest = hashlib.sha256(dense.tobytes()).hexdigest()
                if key in hashes: assert hashes[key] == digest
                hashes[key] = digest
                del dense, direct
            hits = sum(e['hit'] for e in budget.events)
            assert hits == (6 if arm == 'B' and repeat == 1 else 0)
            requests.append(dict(hits=hits, misses=6-hits, resident_bytes=budget.bytes))
        assert budget.bytes == (24 << 20 if arm == 'A' else 72 << 20)
        arms[arm] = requests
        del budget; gc.collect()
    for limit in (0, 48 << 20, 81 << 20, True):
        try: ObservedDecodeBudget(limit)
        except AssertionError: pass
        else: raise AssertionError('Invalid capacity admitted')
    writer = {}
    def original(path, value):
        path.open('xb').write((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())
    with tempfile.TemporaryDirectory(dir='/tmp') as tmp:
        root = Path(tmp); budget = LogBudget(root, original, writer)
        for name, value in [('SAMPLE.json', dict(correct=True)), ('PHYSICAL_TRANSACTIONS.json', dict(rows=[dict(done=True, size=32)]*4000))]:
            budget.save(root/name, value)
            assert read_saved(root/name) == value
        for member in writer['persistent_log_budget']['members']:
            raw = (root/member['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == member['sha256']
            plain = gzip.decompress(raw) if member['gzip'] else raw
            assert hashlib.sha256(plain).hexdigest() == member['raw_sha256']
        try: budget.save(root.parent/'outside.json', {})
        except AssertionError: pass
        else: raise AssertionError('Outside path admitted')
        try: budget.save(root/'SAMPLE.json', {})
        except AssertionError: pass
        else: raise AssertionError('Overwrite admitted')
        with patch('compact_log_output.os.statvfs', return_value=type('FS', (), dict(f_bavail=1, f_frsize=4096))()):
            try: budget.save(root/'LOW_SPACE.json', {})
            except AssertionError: pass
            else: raise AssertionError('Reserve bypassed')
        assert not (root/'LOW_SPACE.json').exists()
        budget.limit = budget.used
        try: budget.save(root/'OVER_BUDGET.json', {})
        except AssertionError: pass
        else: raise AssertionError('Budget bypassed')
    sample_sizes = {}
    if fixtures:
        for name in ('PHYSICAL_TRANSACTIONS.json','STRICT_VISUAL_COMPLETION.json','PARSER_PROFILE.json','WEIGHT_STAGE_PROFILE.json'):
            raw = (Path(fixtures)/name).read_bytes()
            value = json.loads(raw); plain = (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
            packed = gzip.compress(plain,compresslevel=6,mtime=0)
            assert gzip.decompress(packed) == plain
            sample_sizes[name] = dict(raw=len(plain), compressed=len(packed))
    return dict(status='PASS_ACTUAL_SIX_CACHE_AND_LOSSLESS_WRITER_COMPONENT', model_forwards=0,
                board_commands=0, matrices=files, raw_FP32_sha256=hashes, arms=arms,
                full_uint32_equal=True, invalid_capacity_rejected=True, lossless_writer_roundtrip=True,
                path_overwrite_reserve_budget_rejected=True, historical_diagnostic_sizes=sample_sizes)
