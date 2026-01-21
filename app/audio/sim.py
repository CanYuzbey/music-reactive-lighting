import numpy as np


def sine_with_hits(
    sample_rate: int,
    frame_size: int,
    t0: float,
    base_freq: float = 220.0,
    hit_every_s: float = 0.5,
    hit_strength: float = 0.9,
) -> np.ndarray:
    """
    Generates a mono audio frame:
    - sine wave base
    - periodic transient "hits" (short spikes) to simulate drums
    """
    t = (np.arange(frame_size) / sample_rate) + t0
    x = 0.15 * np.sin(2 * np.pi * base_freq * t)

    # add a short spike at regular intervals
    phase = (t0 % hit_every_s)
    if phase < (frame_size / sample_rate) * 0.25:
        # spike at the beginning of some frames
        x[: max(1, frame_size // 64)] += hit_strength

    # clamp to [-1, 1]
    x = np.clip(x, -1.0, 1.0).astype(np.float32)
    return x

