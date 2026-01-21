from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DynamicsState:
    minimal_mode: bool = False
    drop_boost_frames_left: int = 0


@dataclass(frozen=True)
class DynamicsParams:
    # Minimal mode thresholds (hysteresis)
    low_enter: float = 0.15   # short_avg below this -> start counting
    low_exit: float = 0.20    # short_avg above this -> exit minimal mode

    # How long short_avg must stay low to enter minimal mode
    enter_hold_frames: int = 20  # ~ (enter_hold_frames / fps) seconds

    # Drop detection
    peak_th: float = 0.65
    surprise_th: float = 0.35

    # Drop boost duration
    drop_boost_frames: int = 10  # ~ (drop_boost_frames / fps) seconds


class DynamicsController:
    """
    Manages:
    - Minimal Mode (trend-based)
    - Drop Boost (event-based override)
    Using two signals:
    - instant_brightness (fast)
    - short_brightness (smoothed)
    """

    def __init__(self, params: DynamicsParams):
        self.p = params
        self.state = DynamicsState()
        self._low_counter = 0

    def update(self, instant_brightness: float, short_brightness: float) -> DynamicsState:
        # --- Drop detection (event) ---
        surprise = instant_brightness - short_brightness
        is_drop = (instant_brightness >= self.p.peak_th) and (surprise >= self.p.surprise_th)

        if is_drop:
            self.state.drop_boost_frames_left = self.p.drop_boost_frames

        # --- Minimal mode (state) ---
        if short_brightness < self.p.low_enter:
            self._low_counter += 1
        else:
            self._low_counter = 0

        if not self.state.minimal_mode and self._low_counter >= self.p.enter_hold_frames:
            self.state.minimal_mode = True

        if self.state.minimal_mode and short_brightness > self.p.low_exit:
            self.state.minimal_mode = False
            self._low_counter = 0

        # --- Decay drop boost timer ---
        if self.state.drop_boost_frames_left > 0:
            self.state.drop_boost_frames_left -= 1

        return self.state

