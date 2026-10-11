"""Exact candidate configuration before seven runtime buffers; retain unknown ownership."""
from pathlib import Path
from m443_configuration01 import Configuration


class LayerConfiguration:
    def __init__(self, result, candidate, manifest_sha, application, evidence, *, factory=Configuration):
        self.result = result
        self.bit = (Path(candidate)/'overlay/m120_m89x2_t32.bit').resolve()
        self.observer = factory(application, manifest_sha, evidence)
        self.accepted = False

    @property
    def retain_required(self):
        return self.observer.unknown

    def load(self, bit, loader, *args, **kwargs):
        if Path(bit).resolve() != self.bit or args or kwargs != {'download': True}:
            raise RuntimeError('Exact original runtime Overlay call required')
        try:
            overlay = self.observer.load(self.bit, loader)
            self.accepted = True
            return overlay
        finally:
            self.result['configuration_record'] = self.observer.record
            self.result['unknown_configuration_ownership'] = self.observer.unknown
            self.result['configuration_application_accepted'] = self.accepted

    def require_allocation_eligibility(self):
        if not self.accepted or self.retain_required:
            raise RuntimeError('Actual configuration proof required before original runtime buffers')
