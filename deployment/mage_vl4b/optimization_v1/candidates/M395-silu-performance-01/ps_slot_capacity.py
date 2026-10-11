"""PS-only slot allocation probe; no PYNQ, worker or model imports."""
import os

PORT_BYTES = 6963200
SLOT_BYTES = 4 * PORT_BYTES
RESERVE_BYTES = 64 << 20


class CapacityRejected(MemoryError):
    pass


def eligibility(snapshot, *, before_slot):
    mem = snapshot['system_bytes']
    for key in ('CmaFree', 'MemAvailable'):
        if type(mem.get(key)) is not int or mem[key] < 0:
            raise ValueError('Missing/invalid real memory field: ' + key)
    required_ps = RESERVE_BYTES + (SLOT_BYTES if before_slot else 0)
    return dict(cma_free_bytes=mem['CmaFree'],mem_available_bytes=mem['MemAvailable'],
                required_cma_bytes=RESERVE_BYTES,required_mem_available_bytes=required_ps,
                before_slot=before_slot,meets_load_only_threshold=(mem['CmaFree'] >= RESERVE_BYTES and mem['MemAvailable'] >= required_ps),
                serving_after_vision_capacity_proven=False,numerical_or_performance_pass=False)


def require_capacity(snapshot, *, before_slot):
    result = eligibility(snapshot, before_slot=before_slot)
    if not result['meets_load_only_threshold']:
        raise CapacityRejected('PS slot memory reserve rejected: ' + repr(result))
    return result


def materialize_slot(slots, evidence, *, page_bytes=None, allocator=bytearray):
    """Caller owns slots even after allocation failure; no hidden cleanup."""
    if slots:
        raise ValueError('Fresh sole-owned slot list required')
    if page_bytes is None:
        page_bytes = os.sysconf('SC_PAGE_SIZE')
    if type(page_bytes) is not int or page_bytes <= 0:
        raise ValueError('Invalid actual OS page size')
    evidence.update(page_bytes=page_bytes,ports=[],payload_bytes=0)
    for port in range(4):
        slot = allocator(PORT_BYTES)
        slots.append(slot)  # Own allocation before any verification can fail.
        if type(slot) is not bytearray or len(slot) != PORT_BYTES:
            raise ValueError('PS bytearray geometry differs')
        offsets = range(0, PORT_BYTES, page_bytes)
        for offset in offsets:
            slot[offset] = 0xA5
        slot[-1] = 0x5A
        if any(slot[offset] != 0xA5 for offset in offsets) or slot[-1] != 0x5A:
            raise RuntimeError('Touch/readback failed')
        evidence['ports'].append(dict(port=port,bytes=len(slot),touched_pages=len(offsets),last_byte_touched=True,readback=True))
        evidence['payload_bytes'] += len(slot)
    if evidence['payload_bytes'] != SLOT_BYTES:
        raise RuntimeError('Maximum PS payload not materialized')
    evidence['all_ports_materialized'] = True


def never_submitted_release(snapshot, host_calls, logical_calls, blocked, allocation_count):
    """DMA zero accepted ONLY as never-submitted provenance, not completed idle."""
    return (type(host_calls) is int and type(logical_calls) is int and host_calls == logical_calls == 0
            and not blocked and allocation_count == 7
            and snapshot.get('ap_ctrl') == 4
            and snapshot.get('mm2s_dmasr') == 0 and snapshot.get('s2mm_dmasr') == 0
            and snapshot.get('mm2s_error') is False and snapshot.get('s2mm_error') is False
            and snapshot.get('ap_return') == 0
            and all(snapshot.get(k) == '' for k in ('kernel_read_error','return_read_error','dma_read_error')))
