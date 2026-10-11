import numpy as np

def silu(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, np.float32)
    return (x / (1.0 + np.exp(-x))).astype(np.float32)
