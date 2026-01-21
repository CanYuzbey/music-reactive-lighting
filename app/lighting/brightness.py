from app.audio.pitch_register import PitchRegister


def apply_pitch_brightness_bias(
    brightness: float,
    register: PitchRegister,
    amount: float = 0.07,
) -> float:
    """
    Applies a small brightness bias based on pitch register.
    """
    if register == PitchRegister.HIGH:
        brightness += amount
    elif register == PitchRegister.LOW:
        brightness -= amount

    return max(0.0, min(1.0, brightness))

