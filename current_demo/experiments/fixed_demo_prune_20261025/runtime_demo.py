"""Same frozen arithmetic; whole encoder blocks may include endpoints."""
from demo_common import *
from runtime import Experiment
class DemoExperiment(Experiment):
    def set_active(self,v,l):
        assert v==sorted(set(v)) and l==sorted(set(l)) and v and l
        assert set(v)<=set(range(24)) and set(l)<=set(range(36))
        self.v=list(v);self.l=list(l);torch=self.torch
        self.vision.vision.encoder.layers=torch.nn.ModuleList([self.original_vision[i] for i in v])
        self.language.layers=torch.nn.ModuleList([self.original_language[i] for i in l])
        cfg=copy.deepcopy(self.text_config);cfg.num_hidden_layers=len(l);cfg.layer_types=[self.text_config.layer_types[i] for i in l]
        self.language.config=cfg;self.model.config.text_config=cfg;self.model.model.config.text_config=cfg
        for j,i in enumerate(l):self.original_language[i].self_attn.layer_idx=j
        assert len(self.language.layers)==len(l) and len(self.vision.vision.encoder.layers)==len(v)
