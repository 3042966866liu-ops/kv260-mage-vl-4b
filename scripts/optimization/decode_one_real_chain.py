"""Read the frozen, previously CSim-tested real Gate/Up transaction."""
import hashlib
from pathlib import Path
import struct
from decode_one_board_protocol import CANDIDATE_BUILD

FIXTURE_SHA = 'e4ec996a6c6cda9c0e890948258157bd9c77a98f95249a8435d8eae265fdef69'
FIXTURE_BYTES = 29061304


def load_real_chain(path):
    path = Path(path)
    if path.stat().st_size != FIXTURE_BYTES:
        raise ValueError('Real fixture byte count mismatch')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError('Real fixture SHA mismatch')
    if raw[:8] != b'OP1REAL1':
        raise ValueError('Real fixture magic mismatch')
    size, input_size, output_size, config = struct.unpack_from('<IIII', raw, 8)
    if 24 + 4*size + input_size + output_size != len(raw) or config != 0x10a0428:
        raise ValueError('Real fixture layout/config mismatch')
    shards = tuple(raw[24+i*size:24+(i+1)*size] for i in range(4))
    start = 24+4*size
    return dict(packet=raw[start:start+input_size], weight_shards=shards,
                weights=shards[0], expected_output=raw[start+input_size:],
                output_bytes=output_size, config=config, expected_build=CANDIDATE_BUILD,
                reference='Frozen REPLAY01 layer0 Gate/Up, same M120+A8 quantization')
