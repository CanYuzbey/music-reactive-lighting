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
    high_freq_content = float(np.mean(np.abs(dx)))
    
    # Simple RMS for low-end energy
    rms = float(np.sqrt(np.mean(x**2)))
    
    # Combine: High Freq transients + significant energy (Bass Kicks)
    # We weight RMS lower as we want "events" not just "loudness", 
    # but for sparse kicks, loudness IS the event.
    return high_freq_content + (rms * 0.6) + 1e-12


def normalize_onset(v: float, floor: float = 0.032, ceiling: float = 0.045) -> float:
    y = (v - floor) / (ceiling - floor)
    return float(max(0.0, min(1.0, y)))

