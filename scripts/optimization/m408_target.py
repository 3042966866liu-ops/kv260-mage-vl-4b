"""Resolve only the exact frozen progress -> precision -> encoder topology."""


def resolve_target(vision, progress_cls, boundary_cls, torch):
    if len(vision.encoder.layers) != 24: raise RuntimeError('Original 24-layer topology differs')
    outer = vision.encoder.layers[12]
    if type(outer) is not progress_cls or outer.index != 12:
        raise RuntimeError('Original progress wrapper identity differs')
    boundary = outer.layer
    if type(boundary) is not boundary_cls or boundary.target_dtype != torch.float32 or boundary.output_dtype != torch.float32:
        raise RuntimeError('Original FP32 precision boundary differs')
    layer = boundary.layer
    if type(layer).__name__ != 'MageVLVisionEncoderLayer' or not hasattr(layer,'mlp') or not hasattr(layer,'layer_norm2'):
        raise RuntimeError('Original encoder layer target differs')
    return layer,dict(progress=type(outer).__name__,precision=type(boundary).__name__,
                      encoder=type(layer).__name__,target_dtype=str(boundary.target_dtype),
                      output_dtype=str(boundary.output_dtype),selected_layer=12)
