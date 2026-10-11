"""Keep every admission check; store stage/request points instead of each DMA point."""
from m369_light_policy import StagePolicy as OriginalPolicy


class StagePolicy(OriginalPolicy):
    def capture(self, label, check=False):
        if label.startswith(('before-visual-submit:', 'after-visual-submit:')):
            # The parent performs the unchanged snapshot/count/assess first.
            # Its existing physical-launch rule omits only duplicate storage.
            label = label.replace('visual-submit:', 'physical-launch:visual:', 1)
        return super().capture(label, check)
