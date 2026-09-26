"""Pure guard predicates; an idle kernel alone cannot prove both DMA paths idle."""
def device_owner_blocks(target, driver=None):
    if target.startswith(('/dev/zocl', '/dev/xlnk')):
        return True
    if target.startswith('/dev/dri/'):
        # Only the independently observed PS display driver is excluded.
        # zocl-drm and unknown/unresolved DRM devices remain fail-closed.
        return driver != 'zynqmp-display'
    return False

def safe_to_release(snapshot):
    required = ('ap_ctrl', 'mm2s_dmasr', 's2mm_dmasr')
    if any(type(snapshot.get(k)) is not int or snapshot[k] < 0 for k in required):
        return False
    if not snapshot['ap_ctrl'] & 4:
        return False
    # DMASR halted (bit0) or idle (bit1); reject internal/slave/decode/SG errors.
    return all((snapshot[k] & 3) and not (snapshot[k] & 0x770)
               for k in required[1:])
