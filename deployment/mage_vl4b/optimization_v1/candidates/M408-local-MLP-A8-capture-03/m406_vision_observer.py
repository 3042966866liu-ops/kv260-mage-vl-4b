"""Bounded, tensor-free CPU vision accounting. No Torch import at module load."""
import ast
from contextlib import contextmanager
import copy
import inspect
import os
from pathlib import Path
import threading
import time


class Clock:
    def __init__(self):
        self.owner = threading.get_ident()
        self.stack = []
        self.totals = {}
        self.gemm_windows = []
        self.events = 0

    @contextmanager
    def phase(self, name, category):
        if threading.get_ident() != self.owner:
            yield
            return
        if self.events >= 10000:
            raise RuntimeError('Observation event budget exceeded')
        frame = dict(name=name, category=category, child_ns=0, matmul_index=0)
        self.stack.append(frame)
        started = time.perf_counter_ns()
        cpu = time.process_time_ns()
        try:
            yield
        finally:
            ended = time.perf_counter_ns()
            process_cpu = time.process_time_ns() - cpu
            elapsed = ended - started
            assert self.stack.pop() is frame
            if self.stack:
                self.stack[-1]['child_ns'] += elapsed
            exclusive = elapsed - frame['child_ns']
            if exclusive < 0:
                raise RuntimeError('Nested accounting went negative')
            row = self.totals.setdefault((name, category), dict(calls=0, inclusive_ns=0,
                exclusive_ns=0, process_cpu_ns=0))
            row['calls'] += 1
            row['inclusive_ns'] += elapsed
            row['exclusive_ns'] += exclusive
            row['process_cpu_ns'] += process_cpu
            self.events += 1
            if category == 'linear_gemm':
                self.gemm_windows.append(dict(name=name, start_ns=started, end_ns=ended,
                                              process_cpu_ns=process_cpu))

    def current(self):
        return dict(self.stack[-1]) if self.stack else None

    def ancestor(self, category):
        return next((x for x in reversed(self.stack) if x['category'] == category), None)

    def evidence(self):
        if self.stack:
            raise RuntimeError('Unclosed observation span')
        rows = [dict(name=name, category=cat, **v) for (name, cat), v in self.totals.items()]
        root = next(x for x in rows if x['category'] == 'vision_total')
        exclusive = sum(x['exclusive_ns'] for x in rows)
        if exclusive != root['inclusive_ns']:
            raise RuntimeError('Exclusive accounting does not partition visual wall time')
        return dict(events=self.events, rows=rows, exclusive_sum_ns=exclusive,
                    vision_wall_ns=root['inclusive_ns'], gemm_windows=self.gemm_windows,
                    process_cpu_is_not_exclusive=True)


def instrument_forward(source, clock, original_globals):
    """Add With spans, then prove removal gives the exact original AST."""
    original = ast.parse(source)
    cls = next(x for x in original.body if isinstance(x, ast.ClassDef)
               and x.name == 'M207FP32GemmW4Linear')
    function = next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == 'forward')
    transformed = copy.deepcopy(function)
    transformed.decorator_list = []

    def wrap(statement, category):
        call = ast.Call(func=ast.Attribute(value=ast.Name(id='__m406_clock', ctx=ast.Load()),
                                           attr='phase', ctx=ast.Load()),
                        args=[ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()),
                                            attr='name', ctx=ast.Load()), ast.Constant(category)], keywords=[])
        return ast.With(items=[ast.withitem(context_expr=call)], body=[statement], type_comment=None)

    def convert(block):
        answer = []
        for node in block:
            if isinstance(node, ast.If):
                node.body = [wrap(x, 'linear_operand_conversion') for x in node.body]
                node.orelse = [wrap(x, 'linear_operand_conversion') for x in node.orelse]
                answer.append(node)
            elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                category = dict(weight='linear_weight_restore', output='linear_gemm').get(name)
                answer.append(wrap(node, category) if category else node)
            elif isinstance(node, ast.Return):
                answer.append(wrap(node, 'linear_output_conversion'))
            else:
                answer.append(node)
        return answer
    transformed.body = convert(transformed.body)
    class Remove(ast.NodeTransformer):
        def visit_With(self, node):
            assert len(node.items) == len(node.body) == 1
            assert isinstance(node.items[0].context_expr, ast.Call)
            return self.visit(node.body[0])
    restored = Remove().visit(copy.deepcopy(transformed))
    assert ast.dump(restored, include_attributes=False) == ast.dump(function, include_attributes=False)
    module = ast.fix_missing_locations(ast.Module(body=[transformed], type_ignores=[]))
    namespace = dict(original_globals, __m406_clock=clock)
    exec(compile(module, '<M406-exact-M207-timed-forward>', 'exec'), namespace)
    return namespace['forward']


class Observer:
    def __init__(self, runtime, linear_cls, source):
        self.runtime, self.linear_cls, self.source = runtime, linear_cls, source
        self.torch = runtime.torch
        self.clock = Clock()
        self.restore = []

    def patch(self, owner, attr, value):
        existed = attr in vars(owner)
        original = getattr(owner, attr)
        setattr(owner, attr, value)
        self.restore.append((owner, attr, original, existed))

    def wrap_module(self, module, name, category):
        original = module.forward
        def observed(*args, **kwargs):
            with self.clock.phase(name, category):
                return original(*args, **kwargs)
        self.patch(module, 'forward', observed)

    def __enter__(self):
        try:
            original = self.linear_cls.forward
            replacement = instrument_forward(self.source, self.clock, original.__globals__)
            self.patch(self.linear_cls, 'forward', replacement)
            for name, module in self.runtime.vision.named_modules():
                kind = type(module).__name__
                if kind == 'M206ProgressLayer':
                    self.wrap_module(module, name, 'encoder_layer_other')
                elif kind == 'MageVLVisionAttention':
                    self.wrap_module(module, name, 'attention_other')
                elif kind == 'SiglipMLP':
                    self.wrap_module(module, name, 'mlp_other')
                elif name in ('embeddings', 'merger', 'layernorm_pre', 'layernorm_post'):
                    self.wrap_module(module, name, name + '_other')
            torch = self.torch
            functional = torch.nn.functional
            for attr, category in (('layer_norm', 'normalization'), ('gelu', 'GELU'),
                                   ('softmax', 'attention_softmax')):
                old = getattr(functional, attr)
                def wrapper(*args, _old=old, _category=category, **kwargs):
                    parent = self.clock.current()
                    with self.clock.phase(parent['name'] if parent else 'outside', _category):
                        return _old(*args, **kwargs)
                self.patch(functional, attr, wrapper)
            old_matmul = torch.matmul
            def matmul(*args, **kwargs):
                parent = self.clock.ancestor('attention_other')
                if parent is None or threading.get_ident() != self.clock.owner:
                    return old_matmul(*args, **kwargs)
                category = 'attention_QK' if parent['matmul_index'] % 2 == 0 else 'attention_AV'
                parent['matmul_index'] += 1
                with self.clock.phase(parent['name'], category):
                    return old_matmul(*args, **kwargs)
            self.patch(torch, 'matmul', matmul)
            old_to = torch.Tensor.to
            def tensor_to(tensor, *args, **kwargs):
                if threading.get_ident() != self.clock.owner:
                    return old_to(tensor, *args, **kwargs)
                parent = self.clock.current()
                category = parent['category'] if parent and parent['category'] in (
                    'linear_operand_conversion', 'linear_output_conversion') else 'other_tensor_conversion'
                with self.clock.phase(parent['name'] if parent else 'outside', category):
                    return old_to(tensor, *args, **kwargs)
            self.patch(torch.Tensor, 'to', tensor_to)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *exc):
        for owner, attr, original, existed in reversed(self.restore):
            if existed:
                setattr(owner, attr, original)
            else:
                delattr(owner, attr)
            if getattr(owner, attr) != original:
                raise RuntimeError('Observer binding restoration differs')
        self.restore.clear()


def proc_snapshot(root=Path('/proc')):
    cpus = {}
    for line in (root / 'stat').read_text(encoding='utf-8').splitlines():
        words = line.split()
        if words and words[0].startswith('cpu') and words[0][3:].isdigit():
            values = list(map(int, words[1:9]))
            cpus[words[0]] = dict(total=sum(values), idle=values[3] + values[4])
    tasks = {}
    for path in sorted((root / 'self/task').glob('*/stat')):
        try:
            raw = path.read_text(encoding='utf-8')
            prefix, tail = raw.rsplit(')', 1)
            words = tail.split()
            tasks[path.parent.name] = dict(name=prefix.split('(', 1)[1],
                                           ticks=int(words[11]) + int(words[12]))
        except FileNotFoundError:
            pass
    io = {k: int(v) for k, v in (x.split(':', 1) for x in
          (root / 'self/io').read_text(encoding='utf-8').splitlines())}
    memory = {k: int(v.split()[0]) * 1024 for k, v in (x.split(':', 1) for x in
              (root / 'self/status').read_text(encoding='utf-8').splitlines())
              if k in ('VmRSS', 'VmHWM', 'RssAnon', 'RssFile')}
    return dict(time_ns=time.perf_counter_ns(), cpu=cpus, tasks=tasks, io=io, memory=memory)


class CpuSampler:
    def __init__(self, clock, interval=.1):
        self.clock, self.interval = clock, interval
        self.stop = threading.Event()
        self.samples, self.errors = [], []
        self.worker = threading.Thread(target=self.run, name='m406-proc-sampler', daemon=True)

    def run(self):
        try:
            while not self.stop.wait(self.interval):
                if len(self.samples) >= 900:
                    raise RuntimeError('CPU sample budget exceeded')
                row = proc_snapshot()
                row['phase'] = self.clock.current()
                self.samples.append(row)
        except BaseException as error:
            self.errors.append(repr(error))

    def __enter__(self):
        self.before = proc_snapshot()
        self.worker.start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        self.worker.join(2)
        if self.worker.is_alive():
            raise RuntimeError('CPU sampling worker still alive')
        self.after = proc_snapshot()
        if self.errors:
            raise RuntimeError('CPU sampling failed: ' + str(self.errors))

    def evidence(self):
        points = [self.before] + self.samples + [self.after]
        intervals = []
        for a, b in zip(points, points[1:]):
            row = dict(start_ns=a['time_ns'], end_ns=b['time_ns'], busy_percent={})
            for core in a['cpu']:
                total = b['cpu'][core]['total'] - a['cpu'][core]['total']
                idle = b['cpu'][core]['idle'] - a['cpu'][core]['idle']
                row['busy_percent'][core] = 100 * (total - idle) / total if total > 0 else None
            row['end_phase'] = b.get('phase')
            intervals.append(row)
        ticks = os.sysconf('SC_CLK_TCK')
        duration = (self.after['time_ns'] - self.before['time_ns']) / 1e9
        tasks = []
        for tid, end in self.after['tasks'].items():
            start = self.before['tasks'].get(tid)
            if start:
                delta = end['ticks'] - start['ticks']
                tasks.append(dict(tid=tid, name=end['name'], cpu_seconds=delta / ticks,
                                  one_core_percent=100 * delta / ticks / duration))
        return dict(intervals=intervals, before=self.before, after=self.after,
                    per_task_persistent_only=tasks, sample_interval_s=self.interval,
                    core_utilization_is_system_wide_not_exclusive_to_this_process=True,
                    sampling_overhead_included=True, worker_joined=not self.worker.is_alive())


def backend_evidence(torch):
    value = dict(torch_version=str(torch.__version__), torch_file=str(torch.__file__),
                 config=torch.__config__.show(), parallel_info=torch.__config__.parallel_info(),
                 intraop_threads=torch.get_num_threads(), interop_threads=torch.get_num_interop_threads(),
                 affinity=sorted(os.sched_getaffinity(0)),
                 thread_environment={k: os.environ.get(k) for k in (
                     'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                     'OMP_DYNAMIC', 'OMP_PROC_BIND', 'OMP_PLACES')},
                 settings_changed=False, backend_library_dispatch_per_operator_unproven=True)
    for key in ('config', 'parallel_info'):
        if len(value[key]) > 20000:
            raise RuntimeError('Backend field budget exceeded')
    return value
