import numpy as np
from enum import Enum


class PitchRegister(Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


def spectral_energy_bands(
    frame: np.ndarray,
    sample_rate: int,
) -> dict:
    """
    Returns normalized energy in low / mid / high frequency bands.
    """
    # mono
    x = frame
    if x.ndim == 2:
        x = x.mean(axis=1)

    # FFT
    spectrum = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), d=1.0 / sample_rate)

    # bands (Hz)
    low_band = (freqs >= 20) & (freqs < 250)
    mid_band = (freqs >= 250) & (freqs < 2000)
    high_band = (freqs >= 2000) & (freqs < 8000)

    low_energy = spectrum[low_band].sum()
    mid_energy = spectrum[mid_band].sum()
    high_energy = spectrum[high_band].sum()

    total = low_energy + mid_energy + high_energy + 1e-12

    return {
        PitchRegister.LOW: low_energy / total,
        PitchRegister.MID: mid_energy / total,
        PitchRegister.HIGH: high_energy / total,
    }


def dominant_pitch_register(band_energy: dict) -> PitchRegister:
    """
    Returns the dominant pitch register.
    """
    return max(band_energy, key=band_energy.get)

