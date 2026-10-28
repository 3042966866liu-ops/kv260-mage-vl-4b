"""Discard only this experiment's completed software cache; never reuse it."""
def discard_completed_cache(torch,cache):
    # DynamicLayer.reset() zeros inference tensors and retains their shapes.
    # Reset in the creating execution mode, then release references so the
    # completed instance is empty. Each next group constructs a new instance.
    with torch.inference_mode():cache.reset()
    cache.layers.clear()
    if cache.get_seq_length()!=0:raise RuntimeError('Completed software cache not empty')

def test():
    import torch
    from transformers.cache_utils import DynamicCache
    retained=[]
    for group in range(3):
        c=DynamicCache();assert c.get_seq_length()==0 and all(c is not old for old in retained)
        with torch.inference_mode():
            for layer in range(2):
                k=torch.full((1,2,5,4),float(group+1));c.update(k,k.clone(),layer)
            assert c.get_seq_length()==5
            for layer in range(2):
                k=torch.full((1,2,1,4),float(group+1));c.update(k,k.clone(),layer)
            assert c.get_seq_length()==6
        discard_completed_cache(torch,c);retained.append(c)
    assert len({id(c) for c in retained})==3 and all(c.get_seq_length()==0 for c in retained)
    print('M454_ACTUAL_INFERENCE_CACHE_LIFECYCLE_PASS_3_INDEPENDENT_INSTANCES')
if __name__=='__main__':test()
