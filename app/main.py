import numpy as np
from collections import Counter, deque

from app.audio.loudness import rms_loudness, normalize_loudness
from app.audio.pitch_register import (
    spectral_energy_bands,
    dominant_pitch_register,
)
from app.lighting.brightness import apply_pitch_brightness_bias


def majority_vote(window):
    return Counter(window).most_common(1)[0][0]


def main():
    print("Brightness + Pitch Register Bias Test")

    sample_rate = 44100
    pitch_window = deque(maxlen=5)

    for i in range(30):
        # fake audio frame
        t = np.linspace(0, 0.05, int(sample_rate * 0.05), endpoint=False)
        freq = 100 + (i / 29.0) * 4000
        amp = 0.02 + 0.18 * (i / 29.0)

        frame = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)

        # loudness → brightness
        rms = rms_loudness(frame)
        brightness = normalize_loudness(rms)

        # pitch register
        bands = spectral_energy_bands(frame, sample_rate)
        dominant = dominant_pitch_register(bands)
        pitch_window.append(dominant)

        smoothed_register = (
            majority_vote(pitch_window)
            if len(pitch_window) == pitch_window.maxlen
            else dominant
        )

        # apply micro bias
        final_brightness = apply_pitch_brightness_bias(
            brightness,
            smoothed_register,
        )

        print(
            f"frame {i:02d} | "
            f"base_brightness={brightness:.2f} | "
            f"register={smoothed_register.value} | "
            f"final_brightness={final_brightness:.2f}"
        )


if __name__ == "__main__":
    main()
