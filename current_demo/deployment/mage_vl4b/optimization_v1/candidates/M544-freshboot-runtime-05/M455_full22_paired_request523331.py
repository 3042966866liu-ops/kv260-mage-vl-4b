"""Explicit whole-request original/triple selection and native generation.

No allocation, Overlay, hidden retries, semantic promotion or automatic reruns.
The outer native runner persists each returned request before starting another.
"""
from M455_request_guard52354 import physical_bound,workers
class PairedRequestSession:
    def __init__(self,runtime,language_binding,visual_provider,guard,generate,idle,check_resources):
        if not all(callable(f) for f in (generate,idle,check_resources)):raise ValueError('Actual native capabilities required')
        idle();self.runtime=runtime;self.language=language_binding;self.visual=visual_provider;self.guard=guard;self.generate=generate
        self.idle_check,self.resources=idle,check_resources;self.failed_selection=False;self.original_language=tuple(runtime.language_contract.chains);self.original_head=tuple(runtime.head_contract.chains)
        if len(self.original_language)!=154 or len(self.original_head)!=8:raise ValueError('Actual complete original constructor required')
    def select(self,active):
        if type(active)is not bool or self.failed_selection or self.guard.request is not None:raise RuntimeError('Explicit idle original/triple selection only')
        self.idle_check()
        try:
            self.language.select(active);self.visual.select(active)
            chains=[]
            for c in self.original_language:
                key=(c['layer'],c['family'])
                chains.append(self.language.entries[key][0] if active and key in self.language.entries else c)
            self.guard.set_chains(chains+list(self.original_head))
        except BaseException:
            self.failed_selection=True;raise
        if any(a is not b for a,b in zip(self.runtime.language_contract.chains,self.original_language)) or any(a is not b for a,b in zip(self.runtime.head_contract.chains,self.original_head)):raise RuntimeError('Original154/head8 contract objects mutated')
    def checkpoint(self):
        if workers() or not self.guard.safe():raise RuntimeError('Actual native request boundary DMA/workers unresolved')
        self.resources()
    def run(self,*,label,active,language,prepare,tokenizer,prompt_tokens,mode,teacher_tokens=None,visual=True):
        if mode not in ('fixed','free'):raise ValueError('Explicit common fixed/free request only')
        count=32 if mode=='free' else len(teacher_tokens) if isinstance(teacher_tokens,list) else 0
        budget=physical_bound(prompt_tokens,count,visual=visual)
        self.select(active);self.guard.begin(label,budget)
        record,tensors,input_record=self.generate(language,prepare,tokenizer,mode=mode,teacher_tokens=teacher_tokens,checkpoint=self.checkpoint)
        if record['prompt_tokens']!=prompt_tokens or record['token_count']!=len(record['token_ids']) or record['cache_cleared_length']!=0:raise RuntimeError('Actual common workload or cache boundary differs')
        self.checkpoint();self.guard.end()
        record.update(candidate='current22_M455_checkpoint240' if active else 'original_M455',explicit_request_label=label,finite_physical_budget=budget,
            same_M455_build=True,extra_weight_reencoding=False,semantic_quality_pass=None)
        return record,tensors,input_record
