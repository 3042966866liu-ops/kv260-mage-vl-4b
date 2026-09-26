"""Candidate smoke protocol, no imports of PYNQ or device side effects.

The kernel returns its identity AFTER a valid transaction, not at reset.
The first identity probe must therefore be a bounded zero-valued descriptor.
"""
import time

STABLE_BUILD = 0x4D395832
CANDIDATE_BUILD = 0x4F503131
DECODE_ONE_BIT = 1 << 24


def referenced_descriptor(*, decode_one):
    """Exact groups=1/W4/rows512/count1 case from tb_rtl.cpp.

    This reuses the already passed normal RTL test geometry and values.
    Result stream has two half values in two 32-bit slots per 64-bit word.
    """
    if type(decode_one) is not bool:
        raise ValueError('Explicit mode required')
    rows, blocks = 512, 64
    tag = (0x3800).to_bytes(2, 'little') * 8  # weight scale 0.5
    codes = bytes([0x99]) * 16               # signed offset code -> +1
    weights = (tag + codes * 16) * blocks
    descriptor = (rows << 32 | 4 << 42).to_bytes(8, 'little') + bytes(8)
    activation_group = bytes([1]) * 64 + (0x3000).to_bytes(16, 'little')
    packet = descriptor + activation_group * 32  # activation scale 0.125
    word = (0x4400 | (0x4400 << 32)).to_bytes(8, 'little')  # exact value 4.0
    per_block = b''.join((word if not decode_one or t == 0 else bytes(8)) * 16
                         for t in range(32))
    expected = per_block * blocks
    return dict(packet=packet, weights=weights, expected_output=expected,
                output_bytes=len(expected), expected_build=CANDIDATE_BUILD,
                config=1 | 4 << 8 | 1 << 16 | (DECODE_ONE_BIT if decode_one else 0),
                reference='hls/mage_decode_op01_one/tb_rtl.cpp:run count1 rows512')


def zero_transaction(*, build_id, decode_one=False):
    if build_id not in (STABLE_BUILD, CANDIDATE_BUILD):
        raise ValueError('Unknown build')
    if decode_one and build_id != CANDIDATE_BUILD:
        raise ValueError('Never set candidate config bit on stable kernel')
    descriptor = (8 << 32 | 2 << 42).to_bytes(8, 'little') + bytes(8)
    packet = descriptor + bytes(32 * 80)
    return dict(packet=packet, weight_bytes_per_shard=9 * 16,
                output_bytes=32 * 4 * 4 * 8,
                config=1 | 2 << 8 | 1 << 16 | (DECODE_ONE_BIT if decode_one else 0),
                expected_build=build_id)


class TransactionFailure(RuntimeError):
    def __init__(self, reason, evidence):
        super().__init__(reason)
        self.evidence = evidence


def wait_transaction(read_snapshot, *, expected_build, identity, input_bytes,
                     output_bytes, timeout_s=5.0, clock=time.monotonic,
                     sleep=time.sleep):
    """Latch clear-on-read ap_done; require both DMA idle and exact identity.

    read_snapshot is the existing MMIO snapshot callable bound to this kernel/DMA.
    Never resets hardware or releases buffers. Caller owns recovery/quarantine.
    """
    if expected_build not in (STABLE_BUILD, CANDIDATE_BUILD):
        raise ValueError('Unknown expected build')
    if not 0 < timeout_s <= 10 or input_bytes <= 0 or output_bytes <= 0:
        raise ValueError('Invalid bounded transaction contract')
    started = clock()
    done = False
    observed_return = None
    while True:
        state = read_snapshot()
        now = clock()
        proof = dict(identity=identity, expected_build=expected_build,
                     input_bytes=input_bytes, output_bytes=output_bytes,
                     wait_seconds=now-started, snapshot=state,
                     ap_done_seen=done, observed_return=observed_return)
        for key in ('ap_ctrl', 'ap_return', 'mm2s_dmasr', 's2mm_dmasr'):
            if type(state.get(key)) is not int or state[key] < 0:
                raise TransactionFailure('Missing or failed register read: '+key, proof)
        if any(state[k] & 0x770 for k in ('mm2s_dmasr', 's2mm_dmasr')) or state.get('mm2s_error') or state.get('s2mm_error'):
            raise TransactionFailure('DMA status error', proof)
        if state['ap_ctrl'] & 2:
            done = True
            observed_return = state['ap_return']
            proof.update(ap_done_seen=True, observed_return=observed_return)
            if observed_return != expected_build:
                raise TransactionFailure('Kernel Build-ID/return mismatch', proof)
        if done and state.get('mm2s_idle') is True and state.get('s2mm_idle') is True:
            proof.update(ap_done_seen=True, observed_return=observed_return)
            return proof
        if now-started >= timeout_s:
            raise TransactionFailure('Transaction timeout', proof)
        sleep(0.0001)
