"""Exact saved-attempt startup-error classifier; no implementation entry point."""
import re

EXPECTED = {'qwen25_mixed_gs_mage_m120_m89x2_0_0': ('c38c091fa5369ea06f33777b58616f9114ef360815b8a900791dff721a93d3c9', 'b84c3b00c0fb05fe9f1e11ac5b2584fd19f881233525f8f856cb39e8d3657589'), 'qwen25_mixed_gs_reset_sync_0': ('40b3a3a68398f4c88b0d603faef986c20f18274337f0a237d2641b61904ac847', '6ce4c28fff54b1849c17849243c80ae6cfa0ff1b5e3518974c15499bfd685bce')}

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
