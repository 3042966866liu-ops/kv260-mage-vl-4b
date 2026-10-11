"""Exact saved-attempt startup-error classifier; no implementation entry point."""
import re

EXPECTED = {
    'qwen25_mixed_gs_axi_dma_prefill_0': (
        '5258f80f5a505c3678354543b73b4fc9fa6ba33b9b17952dce82bbdac1797de1',
        '51614306719ecc5480ec3f7476628d95b5aa225cc296ceece0b0dd6693ddc0be'),
    'qwen25_mixed_gs_sc_s2mm_0': (
        'f89ae4a82b48d41c67420e3ffd5f794e02f57e7806a806b4dbab2c808d31d6c9',
        'ce9891f5501863cf52150c3f2858d8b1dd5a18ceb84726c91953766c6743ca0c'),
}
ERROR = "ERROR: [Common 17-354] Could not open 'C' for writing."


def classify(ip, text, log_sha, checkpoint_sha, completed):
    assert ip in EXPECTED, 'Unreviewed affected IP'
    assert (log_sha, checkpoint_sha) == EXPECTED[ip], 'Saved input SHA differs'
    assert re.findall(r'^ERROR:.*$', text, re.M) == [ERROR], 'Unexpected error set'
    assert not re.search(r'^CRITICAL WARNING:', text, re.M), 'Critical warning'
    source = re.search(r'^source ' + re.escape(ip) + r'\.tcl -notrace$', text, re.M)
    assert source and text.index(ERROR) < source.start(), 'Not startup-only error'
    assert 'Synthesis finished with 0 errors, 0 critical warnings' in text
    assert 'synth_design completed successfully' in text
    assert completed, 'Missing native completion receipt'
    return [ERROR]
