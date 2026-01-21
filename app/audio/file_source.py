from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Tuple

import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class AudioStreamInfo:
    sample_rate: int
    channels: int


def frames_from_file(
    path: str,
    fps: float = 20.0,
    target_sr: int = 44100,
) -> Tuple[AudioStreamInfo, Iterator[np.ndarray]]:
    """
    Yields mono float32 frames from an audio file.

    - Minimal v1: expects WAV/FLAC/OGG readable by soundfile.
    - If sample rate differs from target_sr, we do NOT resample yet (we'll enforce later).
    """

    f = sf.SoundFile(path)
    sr = f.samplerate
    ch = f.channels

    if sr != target_sr:
        raise ValueError(
            f"Expected sample_rate={target_sr}, got {sr}. "
            "For v1, please use a 44.1kHz WAV. (We will add resampling later.)"
        )

    frame_size = int(sr / fps)

    def gen() -> Iterator[np.ndarray]:
        while True:
            data = f.read(frame_size, dtype="float32", always_2d=True)
            if len(data) == 0:
                break
            mono = data.mean(axis=1).astype(np.float32)
            yield mono

    return AudioStreamInfo(sample_rate=sr, channels=ch), gen()
