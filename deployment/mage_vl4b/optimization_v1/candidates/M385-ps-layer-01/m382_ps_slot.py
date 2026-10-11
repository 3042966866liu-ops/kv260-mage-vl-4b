"""Independent sealed-DMA load-only PS-slot probe; no model or PL imports."""
import os
import sys
import threading
import time
import weakref

PORT_BYTES = 6963200
SLOT_BYTES = 4 * PORT_BYTES
GROWTH_LIMIT = 64 << 20
AVAILABLE_MARGIN = 64 << 20


class RetainedSlotError(RuntimeError):
    pass


class SlotOwner:
    def __init__(self, data):
        self.data = data


def assess(snapshot, baseline_rss, counts, initial_counts):
    system = snapshot['system_bytes']; process = snapshot['process_bytes']
    for value in (system['CmaFree'], system['MemAvailable'], process['VmRSS'], baseline_rss):
        if type(value) is not int or value < 0:
            raise ValueError('Invalid actual memory field')
    if not counts or counts != initial_counts:
        raise RuntimeError('Global CMA API counter changed; stop, ownership unknown')
    growth = max(0, process['VmRSS'] - baseline_rss)
    required = max(0, GROWTH_LIMIT - growth) + AVAILABLE_MARGIN
    if growth > GROWTH_LIMIT or system['MemAvailable'] < required:
        raise MemoryError('Load-only PS-slot budget/reserve exceeded')
    return dict(observed_rss_growth_bytes=growth, required_available_bytes=required,
                cma_free_bytes=system['CmaFree'], mem_available_bytes=system['MemAvailable'],
                production64MiB_would_admit=system['CmaFree'] >= AVAILABLE_MARGIN,
                additional_explicit_cma_requests=0)


def touch(data, page_bytes):
    if type(data) is not bytearray or len(data) != PORT_BYTES:
        raise ValueError('Exact ordinary PS bytearray required')
    if type(page_bytes) is not int or page_bytes <= 0:
        raise ValueError('Invalid OS page size')
    pages = range(0, PORT_BYTES, page_bytes)
    for offset in pages:
        data[offset] = 0xA5
    data[-1] = 0x5A
    if any(data[offset] != 0xA5 for offset in pages) or data[-1] != 0x5A:
        raise RuntimeError('Page touch/readback failed')
    return dict(bytes=len(data), touched_pages=len(pages), last_byte_touched=True, readback=True)


def release(owners, references):
    # Check every data buffer before removing any owner. No ndarray/memoryview
    # or caller alias may survive. CPython refcount includes this temporary arg.
    if sys.implementation.name != 'cpython':
        raise RetainedSlotError('Object lifetime probe requires actual CPython')
    for owner in owners:
        if sys.getrefcount(owner.data) != 2:
            raise RetainedSlotError('PS bytearray has an external alias; retain slot')
        if sys.getrefcount(owner) != 3:
            raise RetainedSlotError('PS owner has an external alias; retain slot')
    if owners:
        del owner
    count = len(owners)
    owners.clear()
    if any(reference() is not None for reference in references):
        raise RetainedSlotError('PS owner remains live after release')
    return dict(released_ports=count, bytearrays_sole_owned_before_release=True,
                all_owner_weakrefs_dead=True, explicit_gc_or_trim=False)


def run_probe(owners, evidence, snapshot, counters, mark, retained_identity,
              *, allocator=bytearray, touch_fn=touch, settle_s=2.0, page_bytes=None):
    if owners:
        raise ValueError('Fresh sole-owned PS owners list required')
    if page_bytes is None:
        page_bytes = os.sysconf('SC_PAGE_SIZE')
    references = []
    before = snapshot(); baseline = before['process_bytes']['VmRSS']; initial = counters()
    evidence.update(slot_bytes=SLOT_BYTES, ordinary_bytearray_ports=4, page_bytes=page_bytes,
                    budget_growth_bytes=GROWTH_LIMIT, available_margin_bytes=AVAILABLE_MARGIN,
                    baseline_before_slot=before, initial_cma_counts=initial, ports=[], checkpoints=[],
                    observer_stopped=False, objects_released=False, worker_started=False,
                    exact_native_peak_proven=False, rss_return_to_baseline_required=False)
    stop = threading.Event(); lock = threading.RLock(); reason = []; samples = [0]; extrema = {}

    def check(name):
        if not retained_identity():
            raise RuntimeError('Complete runtime/seven DMA resident identity differs')
        memory = mark(name); counts = counters()
        decision = assess(memory, baseline, counts, initial)
        with lock:
            if reason:
                raise RuntimeError('Latched observer stop: ' + reason[0])
        evidence['checkpoints'].append(dict(name=name, memory=memory, decision=decision,
                                             cma_counts=counts, retained_identity=True))
        return memory

    def observe():
        while not stop.wait(.02):
            try:
                memory = snapshot(); counts = counters()
                assess(memory, baseline, counts, initial)
                point = dict(rss=memory['process_bytes']['VmRSS'], hwm=memory['process_bytes']['VmHWM'],
                             available=memory['system_bytes']['MemAvailable'], cma=memory['system_bytes']['CmaFree'])
                with lock:
                    samples[0] += 1
                    if not extrema:
                        extrema.update(max_rss=point['rss'], max_hwm=point['hwm'],
                                       min_available=point['available'], min_cma=point['cma'])
                    else:
                        extrema['max_rss'] = max(extrema['max_rss'], point['rss'])
                        extrema['max_hwm'] = max(extrema['max_hwm'], point['hwm'])
                        extrema['min_available'] = min(extrema['min_available'], point['available'])
                        extrema['min_cma'] = min(extrema['min_cma'], point['cma'])
            except BaseException as exc:
                with lock:
                    reason.append(type(exc).__name__ + ': ' + str(exc))
                return

    thread = None
    try:
        check('PS-slot:before-allocation-complete-runtime-retained')
        thread = threading.Thread(target=observe, name='m382-memory-observer', daemon=True)
        thread.start()
        for port in range(4):
            check('PS-slot:before-port-' + str(port))
            owners.append(SlotOwner(allocator(PORT_BYTES)))
            references.append(weakref.ref(owners[-1]))
            check('PS-slot:after-allocation-port-' + str(port))
            row = touch_fn(owners[-1].data, page_bytes)
            evidence['ports'].append(dict(port=port, **row))
            check('PS-slot:after-touch-readback-port-' + str(port))
        check('PS-slot:all-four-touched-runtime-retained')
        time.sleep(settle_s)
        check('PS-slot:all-four-retained-after-settle')
    except BaseException as exc:
        # Preserve scalar failure evidence without storing another traceback
        # or buffer reference. Existing traceback aliases must still retain.
        evidence['original_error_type'] = type(exc).__name__
        evidence['original_error'] = str(exc)
        raise
    finally:
        stop.set()
        if thread is not None:
            thread.join(2)
            if thread.is_alive():
                raise RetainedSlotError('Observer remains active; retain owners and process')
        evidence['observer_stopped'] = True
        evidence['sampled_memory'] = dict(interval_s=.02, sample_count=samples[0],
                                          extrema=extrema, stop_reason=reason[0] if reason else None)
        evidence['release'] = release(owners, references)
        evidence['objects_released'] = True
        # These snapshots keep the full runtime/DMA objects alive. Heap RSS may
        # remain high even though slot object lifetime has ended; never trim.
        if not retained_identity():
            raise RuntimeError('Runtime changed during PS release')
        memory = mark('PS-slot:released-complete-runtime-still-retained')
        evidence['after_release_runtime_retained'] = memory
        assess(memory, baseline, counters(), initial)
        time.sleep(settle_s)
        memory = mark('PS-slot:released-runtime-retained-after-settle')
        evidence['after_release_settled_runtime_retained'] = memory
        assess(memory, baseline, counters(), initial)
    if reason:
        raise RuntimeError('Observer latched a stop before final release: ' + reason[0])
    evidence['load_only_slot_pass'] = True
