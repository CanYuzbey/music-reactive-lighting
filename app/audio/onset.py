import numpy as np


def onset_strength(frame: np.ndarray) -> float:
    """
    Very simple transient/onset strength proxy:
    mean absolute derivative (works without preload).
    """
    x = frame
    if x.ndim == 2:
        x = x.mean(axis=1)

    dx = np.diff(x)
    return float(np.mean(np.abs(dx)) + 1e-12)


def normalize_onset(v: float, floor: float = 0.001, ceiling: float = 0.02) -> float:
    y = (v - floor) / (ceiling - floor)
    return float(max(0.0, min(1.0, y)))

