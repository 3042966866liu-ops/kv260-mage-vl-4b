"""Pure host policy for the isolated Decode-one kernel; no device operations.

Not connected to stable runtime. Packet lengths and retry behavior stay unchanged.
"""
CANDIDATE_BUILD_ID = 0x4F503131
DECODE_ONE_BIT = 1 << 24
LEGACY_FIELDS = 0xFF | (7 << 8) | (15 << 16)

def execution_config(config, *, build_id, phase, valid_tokens):
    if type(config) is not int or not 0 <= config <= 0xFFFFFFFF:
        raise ValueError('config must be uint32')
    if type(build_id) is not int or build_id != CANDIDATE_BUILD_ID:
        raise ValueError('candidate Build identity required; never set bit on stable kernel')
    if config & ~LEGACY_FIELDS:
        raise ValueError('caller must supply unmodified legacy config')
    groups=config & 255; bits=(config >> 8) & 7; descriptors=(config >> 16) & 15
    if not 1 <= groups <= 152 or bits not in (2,4) or not 1 <= descriptors <= 10:
        raise ValueError('invalid kernel geometry')
    if phase not in ('prefill','decode') or type(valid_tokens) is not int or not 1 <= valid_tokens <= 32:
        raise ValueError('explicit phase and valid token count required')
    if phase == 'decode':
        if valid_tokens != 1:
            raise ValueError('Decode-one discards all rows except row0; reject multi-token decode')
        return config | DECODE_ONE_BIT
    return config
