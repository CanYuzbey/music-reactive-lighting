import numpy as np
from collections import Counter, deque

from app.audio.pitch_register import (
    spectral_energy_bands,
    dominant_pitch_register,
)


def majority_vote(window):
    return Counter(window).most_common(1)[0][0]


def main():
    print("Pitch register test with short-term window")

    sample_rate = 44100

    # Short-term window for pitch register (categorical)
    short_window = deque(maxlen=5)

    for i in range(30):
        t = np.linspace(0, 0.05, int(sample_rate * 0.05), endpoint=False)

        # sweep from low to high
        freq = 100 + (i / 29.0) * 4000
        frame = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)

        bands = spectral_energy_bands(frame, sample_rate)
        dominant = dominant_pitch_register(bands)

        short_window.append(dominant)

        if len(short_window) < short_window.maxlen:
            smoothed = dominant
        else:
            smoothed = majority_vote(short_window)

        print(
            f"frame {i:02d} | "
            f"dominant={dominant.value} | "
            f"short_term={smoothed.value}"
        )


if __name__ == "__main__":
    main()


