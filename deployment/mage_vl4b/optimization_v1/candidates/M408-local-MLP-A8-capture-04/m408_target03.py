"""Exact original FP32 inner encoder with BF16 outer precision boundary."""
def resolve_target(vision,progress_cls,boundary_cls,torch):
    if len(vision.encoder.layers)!=24:raise RuntimeError('Original 24-layer topology differs')
    outer=vision.encoder.layers[12]
    if type(outer) is not progress_cls or outer.index!=12:raise RuntimeError('Original progress wrapper identity differs')
    boundary=outer.layer
    if type(boundary) is not boundary_cls or boundary.target_dtype!=torch.float32 or boundary.output_dtype!=torch.bfloat16:
        raise RuntimeError('Original FP32-to-BF16 precision boundary differs')
    layer=boundary.layer
    if type(layer).__name__!='MageVLVisionEncoderLayer' or not hasattr(layer,'mlp') or not hasattr(layer,'layer_norm2'):
        raise RuntimeError('Original encoder layer target differs')
    return layer,dict(progress=type(outer).__name__,precision=type(boundary).__name__,encoder=type(layer).__name__,
                      target_dtype=str(boundary.target_dtype),output_dtype=str(boundary.output_dtype),selected_layer=12)

def verify_matrices(layer,linear_cls,torch):
    import hashlib
    result={}
    for part,shape in (('fc1',(1024,4096)),('fc2',(4096,1024))):
        mod=getattr(layer.mlp,part)
        if type(mod) is not linear_cls or mod.name!=f'encoder.layers.12.mlp.{part}' or (mod.in_features,mod.out_features)!=shape:
            raise RuntimeError('Original matrix implementation/name/geometry differs')
        if mod.output_dtype!=torch.float32 or mod.bias is None or mod.bias.dtype!=torch.float32 or tuple(mod.bias.shape)!=(shape[1],):
            raise RuntimeError('Original matrix precision/bias differs')
        if mod.store.entries[mod.name]['module']!=f'model.visual.{mod.name}':raise RuntimeError('Original CPU-store/PL-layout name binding differs')
        result[part]=dict(name=mod.name,in_features=mod.in_features,out_features=mod.out_features,
            output_dtype=str(mod.output_dtype),bias_dtype=str(mod.bias.dtype),bias_shape=list(mod.bias.shape),
            bias_sha256=hashlib.sha256(mod.bias.detach().numpy().tobytes()).hexdigest())
    return result
