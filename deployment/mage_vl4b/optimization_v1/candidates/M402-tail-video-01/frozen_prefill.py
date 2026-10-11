def prefill(self, hidden: np.ndarray) -> tuple[int, np.ndarray, KVCache]:
    hidden = np.asarray(hidden, dtype=np.float32)
    if hidden.ndim != 2 or hidden.shape[1] != HIDDEN or not 1 <= hidden.shape[0] <= MAX_CONTEXT:
        raise ValueError("prefill hidden state is outside the M120 video contract")
    tokens = hidden.shape[0]
    positions = np.arange(tokens, dtype=np.int64)
    keys: list[np.ndarray] = []
    values: list[np.ndarray] = []
    for layer in range(LAYERS):
        prefix = f"model.language_model.layers.{layer}"
        residual = hidden
        normed = rms_norm(hidden, self.weight(f"{prefix}.input_layernorm.weight"))
        q_raw, k_raw, v_raw = self._attention_inputs(layer, normed)
        q = q_raw.reshape(tokens, HEADS, HEAD_DIM)
        k = k_raw.reshape(tokens, KV_HEADS, HEAD_DIM)
        v = v_raw.reshape(tokens, KV_HEADS, HEAD_DIM)
        q = rms_norm(q, self.weight(f"{prefix}.self_attn.q_norm.weight"))
        k = rms_norm(k, self.weight(f"{prefix}.self_attn.k_norm.weight"))
        # Keep the accepted per-layer RoPE path; M240 rejected table caching.
        q, k = apply_rope(q, k, positions)
        keys.append(k.copy())
        values.append(v.copy())
        attention_started = time.monotonic()
        attended = causal_attention_grouped(q, k, v)
        self.grouped_attention_wall_ms += (time.monotonic() - attention_started) * 1000.0
        self.grouped_attention_calls += 1
        if layer == LAYERS - 1:
            attended, residual = _m397_select(self, layer, attended, residual)
        projected = self._family(layer, "attention_out", attended)
        hidden = residual + projected[f"{prefix}.self_attn.o_proj"]
        residual = hidden
        normed = rms_norm(hidden, self.weight(f"{prefix}.post_attention_layernorm.weight"))
        gate_up = self._family(layer, "gate_up", normed)
        down_input = silu(gate_up[f"{prefix}.mlp.gate_proj"]) * gate_up[f"{prefix}.mlp.up_proj"]
        down = self._family(layer, "mlp_down", down_input)
        hidden = residual + down[f"{prefix}.mlp.down_proj"]
        if not np.isfinite(hidden).all():
            raise FloatingPointError(f"non-finite M241 hidden state at layer {layer}")
    final = rms_norm(hidden[-1:], self.weight("model.language_model.norm.weight"))
    logits = self.runtime.lm_head(final)[0]
    return int(np.argmax(logits)), logits, KVCache(keys, values)
