"""OP01 timing primitives. Synthetic tests are never board performance evidence."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    """Reject non-finite numbers before replacing any prior result."""
    path = Path(path)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}.partial')
    with tmp.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


@contextmanager
def exclusive_lock(path):
    """Fail closed on an existing lock; never silently steal a stale lock."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, json.dumps({'pid': os.getpid(), 'created_ns': time.time_ns()}).encode())
        os.fsync(fd)
        yield
    finally:
        os.close(fd)
        path.unlink()


class TokenTrace:
    """Call token_ready only AFTER device completion/sync and sampling.

    This records a contract, not proof that the caller actually synchronized.
    G01.1 still needs inspection of the real runner and board event evidence.
    All timestamps are from one monotonic clock in one process.
    """
    def __init__(self, eos_ids, pad_ids=(), clock=time.perf_counter_ns):
        self.clock = clock
        self.start_ns = clock()
        self.eos_ids = set(eos_ids)
        self.pad_ids = set(pad_ids)
        self.events = []
        self.stages = []
        self.finished = False
        self.last_ns = self.start_ns

    def _now(self):
        now = self.clock()
        if now < self.last_ns:
            raise ValueError('non-monotonic event clock')
        self.last_ns = now
        return now

    def token_ready(self, token_id, *, synchronized):
        if self.finished or (self.events and self.events[-1]['kind'] == 'eos'):
            raise ValueError('token after request/EOS completion')
        if synchronized is not True:
            raise ValueError('enqueue time is not token-ready time')
        if not isinstance(token_id, int) or isinstance(token_id, bool) or token_id < 0:
            raise ValueError('invalid token ID')
        kind = 'eos' if token_id in self.eos_ids else 'pad' if token_id in self.pad_ids else 'valid'
        self.events.append({'token_id': token_id, 'kind': kind, 'ready_ns': self._now()})

    def stage(self, name, start_ns, end_ns):
        if not name or not isinstance(start_ns, int) or not isinstance(end_ns, int):
            raise ValueError('stage needs a name and integer monotonic timestamps')
        if start_ns < self.start_ns or end_ns < start_ns:
            raise ValueError('invalid stage interval')
        self.stages.append({'name': name, 'start_ns': start_ns, 'end_ns': end_ns})

    def finish(self, reason, *, error=None, cpu_linear_fallback=False, finite=True):
        if self.finished:
            raise ValueError('request already finished')
        end = self._now()
        self.finished = True
        errors = []
        if reason not in ('eos', 'length', 'timeout', 'error'):
            errors.append('unknown finish reason')
        if reason in ('timeout', 'error'):
            errors.append(reason)
        if error:
            errors.append(str(error))
        if finite is not True:
            errors.append('non-finite or unverified numeric output')
        if cpu_linear_fallback is not False:
            errors.append('CPU Linear fallback or missing proof')
        if reason == 'eos' and (not self.events or self.events[-1]['kind'] != 'eos'):
            errors.append('EOS reason without EOS event')
        if reason == 'length' and any(x['kind'] == 'eos' for x in self.events):
            errors.append('length reason after EOS')
        valid = [x for x in self.events if x['kind'] == 'valid']
        if not valid:
            errors.append('no valid output token')
        first = valid[0]['ready_ns'] if valid else None
        last = valid[-1]['ready_ns'] if valid else None
        decode_tps = None
        if len(valid) >= 2:
            if last <= first:
                errors.append('non-positive decode interval')
            else:
                decode_tps = (len(valid) - 1) * 1e9 / (last - first)
        stages = sorted(self.stages, key=lambda x: x['start_ns'])
        cursor, covered = self.start_ns, 0
        for stage in stages:
            if stage['start_ns'] < cursor:
                errors.append('overlapping top-level stages')
            if stage['end_ns'] > end:
                errors.append('stage extends beyond request')
            cursor = stage['end_ns']
            covered += stage['end_ns'] - stage['start_ns']
        wall_s = (end - self.start_ns) / 1e9
        closure_error_s = abs(covered / 1e9 - wall_s)
        closure_pass = bool(stages) and closure_error_s <= max(.1, wall_s * .01)
        if not closure_pass:
            errors.append('top-level stage accounting incomplete')
        return {
            'start_ns': self.start_ns, 'end_ns': end, 'raw_token_events': self.events,
            'output_tokens': len(valid), 'raw_output_tokens': len(self.events),
            'ttft_s': None if first is None else (first - self.start_ns) / 1e9,
            'decode_tps': decode_tps,
            'answer_latency_s': None if last is None else (last - self.start_ns) / 1e9,
            'request_wall_s': wall_s, 'top_level_stages': stages,
            'stage_closure_error_s': closure_error_s, 'stage_closure_pass': closure_pass,
            'finish_reason': reason, 'cpu_linear_fallback': cpu_linear_fallback,
            'status': 'FAIL' if errors else 'PASS', 'errors': errors,
            'valid_128_tokens': len(valid) == 128 and not errors,
        }


def summarize_requests(records):
    """Retain failures; subset statistics never imply formal acceptance."""
    def aggregate(field):
        values = [r[field] for r in records if r.get('status') == 'PASS' and r.get(field) is not None]
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('invalid numeric metric')
        values.sort()
        return {'count': len(values), 'median': statistics.median(values) if values else None,
                'p90': values[math.ceil(.9 * len(values)) - 1] if values else None}
    return {'request_count': len(records),
            'failed_requests': sum(r.get('status') != 'PASS' for r in records),
            'valid_128_count': sum(r.get('valid_128_tokens') is True for r in records),
            'ttft_s': aggregate('ttft_s'), 'decode_tps': aggregate('decode_tps'),
            'formal_level': None}
