"""Read only the exact saved integrated numerical result before resources."""
import json
from pathlib import Path
from m428_saved_features import read_owned


def verify(plan):
    saved = json.loads(read_owned(Path(plan['integrated_numerical_result']), plan['integrated_numerical_bytes'], plan['integrated_numerical_sha256']))
    if (saved['status'] != 'PASS_M432_INTEGRATED_VIDEO_NUMERICAL' or type(saved['gate_return_code']) is not int
            or saved['gate_return_code'] or saved['errors'] or saved['selected_layers'] != list(range(13, 24))):
        raise RuntimeError('M432 full numerical prerequisite differs')
    for name in ('numerical_pass', 'safe_buffers_released', 'stable_overlay_reloaded', 'visual_provider_disposed',
                 'visual_bindings_restored', 'borrowed_buffer_identity_preserved', 'visual_static_cache_invalidated'):
        if saved.get(name) is not True:
            raise RuntimeError('M432 complete prerequisite missing: ' + name)
    if saved['unsafe_buffers_retained'] or saved['borrowed_extra_DMA'] != 0 or saved['fpga_transactions'] != 1849 or saved['temperature_measurement_enabled'] is not False:
        raise RuntimeError('M432 completed numerical resource scope differs')
    return saved
