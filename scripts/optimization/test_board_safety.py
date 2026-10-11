import unittest
from board_safety import safe_to_release, device_owner_blocks

class SafetyTests(unittest.TestCase):
    def test_display_is_not_pl_but_unknown_stays_blocked(self):
        self.assertFalse(device_owner_blocks('/dev/dri/card0', 'zynqmp-display'))
        self.assertTrue(device_owner_blocks('/dev/dri/card1', 'zocl-drm'))
        self.assertTrue(device_owner_blocks('/dev/dri/renderD128', 'zocl-drm'))
        self.assertTrue(device_owner_blocks('/dev/dri/card0', None))
        self.assertTrue(device_owner_blocks('/dev/dri/card0', 'unknown'))
        self.assertTrue(device_owner_blocks('/dev/xlnk'))
        self.assertFalse(device_owner_blocks('/dev/null'))

    def test_idle_or_halted_only(self):
        for send in (1, 2):
            for recv in (1, 2):
                self.assertTrue(safe_to_release(dict(ap_ctrl=4, mm2s_dmasr=send, s2mm_dmasr=recv)))
    def test_busy_errors_or_missing_fail_closed(self):
        for item in ({}, dict(ap_ctrl=0, mm2s_dmasr=2, s2mm_dmasr=2),
                     dict(ap_ctrl=4, mm2s_dmasr=2, s2mm_dmasr=0),
                     dict(ap_ctrl=4, mm2s_dmasr=-1, s2mm_dmasr=2),
                     dict(ap_ctrl=4, mm2s_dmasr=0x12, s2mm_dmasr=2),
                     dict(ap_ctrl=4, mm2s_dmasr=2, s2mm_dmasr=0x102)):
            self.assertFalse(safe_to_release(item))
