"""Bounded saved-only B0 collection. No device, model or network operations."""
import base64
import hashlib
import json
import math
from pathlib import Path
import re

REQUESTS = ('first_process_request', 'warm_01', 'warm_02')
SHA = re.compile(r'[0-9a-f]{64}')
MAX_JSON = 8 << 20
MAX_FILES = 64 << 20


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-finite JSON: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def decode(text):
    require(len(text) <= 32 << 20, 'UART envelope bound exceeded')
    hashes = re.findall(r'(?m)^M523_B0_RESULT_SHA256=([0-9a-f]{64})\r?$', text)
    chunks = re.findall(r'(?m)^M523_B0_RESULT_PART=(\d+)/(\d+):([A-Za-z0-9+/=]+)\r?$', text)
    require(len(hashes) == 1 and 0 < len(chunks) <= (MAX_JSON + 479)//480, 'Missing/duplicate envelope')
    require([int(row[0]) for row in chunks] == list(range(len(chunks))), 'Chunk sequence differs')
    require(all(int(row[1]) == len(chunks) for row in chunks), 'Chunk total differs')
    pieces = [base64.b64decode(row[2], validate=True) for row in chunks]
    require(all(len(piece) == 480 for piece in pieces[:-1]) and 0 < len(pieces[-1]) <= 480, 'Chunk size differs')
    raw = b''.join(pieces)
    require(0 < len(raw) <= MAX_JSON and digest(raw) == hashes[0], 'Saved result SHA/size differs')
    return loads(raw), raw


def array_shapes():
    shapes = {name+'/logits.npy': (151936,) for name in REQUESTS}
    first = REQUESTS[0]+'/'
    shapes[first+'input_embeddings.npy'] = (159, 2560)
    for kind in ('keys', 'values'):
        shapes.update({first+kind+str(i)+'.npy': (159, 8, 128) for i in range(36)})
    return shapes


def saved_whitelist(result):
    """Environment is a single fixed child bound by its parent's SHA field."""
    shapes = array_shapes()
    rows = result['raw_files']
    require(isinstance(rows, list) and len(rows) == 76, 'Complete 76-array export required')
    require(len({row['path'] for row in rows}) == 76 and {row['path'] for row in rows} == set(shapes), 'Exact saved array names required')
    total = 0
    for row in rows:
        require(set(row) == {'path', 'bytes', 'sha256'}, 'Unexpected saved array descriptor')
        require(SHA.fullmatch(row['sha256']) is not None, 'Array SHA malformed')
        elements = math.prod(shapes[row['path']])
        require(type(row['bytes']) is int and elements*4 < row['bytes'] <= elements*4+4096, 'NPY extent differs')
        total += row['bytes']
    require(total <= MAX_FILES, 'Saved-only byte budget exceeded')
    require(SHA.fullmatch(result['environment_sha256']) is not None, 'Parent-bound environment SHA missing')
    return [dict(row) for row in rows] + [dict(path='environment.json', max_bytes=65536, sha256=result['environment_sha256'])]


def verify_saved(result, directory, np):
    root = Path(directory).resolve()
    rows = saved_whitelist(result)
    shapes = array_shapes()
    arrays = {}
    for row in rows:
        p = root/row['path']
        require(p.resolve().is_relative_to(root) and p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1, 'Plain saved child required')
        raw = p.read_bytes()
        require(digest(raw) == row['sha256'], 'Saved child SHA differs')
        if row['path'] == 'environment.json':
            require(0 < len(raw) <= row['max_bytes'], 'Environment bound exceeded')
            env = loads(raw)
            require(env['status'] == 'PASS' and env['euid'] == 0 and env['xilinx_xrt'] == '/usr' and env['tmpdir'] == '/dev/shm', 'Original fixed environment rejected')
            require(env['xcl_probe_count'] == env['pynq_device_count'] == 1, 'Device identity differs')
            require(env['xclbinutil'] == '/usr/local/share/pynq-venv/bin/xclbinutil', 'PYNQ tool identity differs')
            require(env['package_manifest_sha256'] == '406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f', 'Stable manifest differs')
        else:
            require(len(raw) == row['bytes'], 'Saved array length differs')
            array = np.load(p, allow_pickle=False)
            require(array.shape == shapes[row['path']] and array.dtype == np.float32 and np.isfinite(array).all(), 'Saved array numerical contract differs')
            arrays[row['path']] = array
    h = hashlib.sha256()
    first = REQUESTS[0]+'/'
    order = [first+'input_embeddings.npy', first+'logits.npy'] + [first+kind+str(i)+'.npy' for kind in ('keys', 'values') for i in range(36)]
    for name in order:
        h.update(arrays[name].tobytes())
    require(all(row['complete_output_digest'] == h.hexdigest() for row in result['requests']), 'Full native output digest differs')
    require(all(np.array_equal(arrays[first+'logits.npy'], arrays[name+'/logits.npy']) for name in REQUESTS), 'Saved original logits are not repeatable')
    return dict(files=77, array_files=76, total_bytes=sum((root/row['path']).stat().st_size for row in rows), full_output_digest=h.hexdigest())


def validate_pass(result, manifest_sha, application_sha):
    from b0_configuration523 import validate_record
    from b0_transaction_guard523 import completed, METHODS
    from b0_owners523 import SHAPES
    require(result['manifest_sha256'] == manifest_sha and result['build_id'] == '0x4D395832', 'B0 provenance differs')
    require(result['status'] == 'PASS_B0_ORIGINAL_REQUEST_BASELINE_ONLY' and result['primary_rc'] == result['inference_rc'] == 0, 'Not a successful baseline')
    require(result['safe_cleanup_complete'] is True and result['unsafe_retained'] is False and not result['errors'] and result['monitor_error'] is None, 'Final lifecycle incomplete')
    require(result['overlay_loads'] == 1 and result['model_forward_calls'] == result['original_request_attempts'] == 3, 'Original attempt counts differ')
    require(result['cold_cache_claim'] is False and result['pruning_candidate'] is False and result['candidate_promotion'] is False and result['performance_pass'] is False, 'Unsupported promotion/performance claim')
    require(result['protected_initial'] == result['protected_final'] and result['clock_initial'] == result['clock_final'] and result['stable_remained_same_bit'] is True, 'Protected state differs')
    validate_record(result['configuration_record'], application_sha, manifest_sha)
    allocations = result['allocations']
    require(len(allocations) == 7 and allocations == result['resident_owner_identity'], 'Resident owners differ')
    for i, row in enumerate(allocations):
        require(row['index'] == i and row['bytes'] == SHAPES[i] and 0 < row['address'] and row['address'] % 4096 == 0 and row['address']+row['bytes'] <= 0x80000000, 'Original low DDR owner differs')
        require(all(row['address'] >= p['address']+p['bytes'] or p['address'] >= row['address']+row['bytes'] for p in allocations[:i]), 'Aliased owner')
    require(result['releases'] == list(reversed(allocations)), 'Original reverse release differs')
    requests = result['requests']
    require([row['request_id'] for row in requests] == list(REQUESTS), 'Fixed request sequence differs')
    expected = [('vision', i) for i in range(24)] + [('language', i) for i in range(36)]
    for row in requests:
        require(row['logical_calls'] == 778 and type(row['scale_retries']) is int and row['scale_retries'] >= 0 and row['physical_calls'] == 778+row['scale_retries'], 'Physical/logical/retry accounting differs')
        require([(x['branch'], x['layer']) for x in row['MLP_rows']] == expected and all(x['passed'] is True and math.isfinite(x['wall_ms']) and x['wall_ms'] >= 0 for x in row['MLP_rows']), 'Incomplete60MLP trace')
        require(all(math.isfinite(row[k]) and row[k] > 0 for k in ('consumer_first_token_ms', 'consumer_total_ms')), 'Invalid consumer timings')
        done = row['original_complete']
        require(done['status'] == 'PASS' and done['prompt_tokens'] == 159 and done['generated_tokens'] == 1 and done['decode_calls'] == 0, 'Original request contract differs')
        require(done['proof']['result'] == 'PASS' and str(done['proof']['build_id']).lower() == '0x4d395832' and done['proof']['language_cpu_linear_fallback'] is False, 'Original FPGA completion proof differs')
    transactions = result['transactions']
    count = sum(row['physical_calls'] for row in requests)
    require(len(transactions) == result['fpga_transactions'] == result['fpga_transactions_started'] == count and all(row['completed'] is True for row in transactions), 'Physical transaction trace incomplete')
    for row in transactions:
        require(row['method'] in METHODS and completed(row['snapshot']), 'Physical snapshot/dispatch differs')
        require(all(type(row[k]) is int and row[k] > 0 for k in ('input_bytes', 'output_bytes')), 'Physical byte counts differ')
        require(type(row['submitted_boundary_ns']) is int and row['completed_boundary_ns'] >= row['submitted_boundary_ns'], 'Physical boundary order differs')
    require(completed(result['final_snapshot_before_cleanup']), 'Final physical completion differs')
    saved_whitelist(result)
    return dict(logical_calls=2334, physical_calls=count, retries=count-2334, MLP_rows=180, scope='B0 baseline only; no candidate speedup or quality verdict')
