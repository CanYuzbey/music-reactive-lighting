from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PulseState:
    pulse: float = 0.0          # 0..1 current pulse value
    beat_interval: float = 0.0  # seconds (smoothed), optional info


class PulseTracker:
    """
    Real-time beat/pulse tracker from an onset signal (0..1).

    - Detects "beats" as onset peaks above a threshold.
    - Uses a refractory period to avoid double-triggers.
    - Estimates beat interval via EMA of inter-beat time.
    - Generates a short pulse that decays smoothly each frame.
    """

    def __init__(
        self,
        fps: float,
        onset_peak_th: float = 0.60,
        refractory_s: float = 0.12,
        decay_s: float = 0.18,
        interval_ema_alpha: float = 0.25,
    ):
        self.fps = fps
        self.onset_peak_th = onset_peak_th
        self.refractory_frames = max(1, int(refractory_s * fps))
        self.decay_frames = max(1, int(decay_s * fps))
        self.interval_ema_alpha = interval_ema_alpha

        self.state = PulseState()
        self._refractory_left = 0
        self._frames_since_last_beat = 10**9  # large initial
        self._last_onset = 0.0

    def update(self, onset: float) -> PulseState:
        onset = max(0.0, min(1.0, onset))

        # decay pulse every frame
        if self.state.pulse > 0.0:
            self.state.pulse *= (1.0 - 1.0 / self.decay_frames)
            if self.state.pulse < 0.001:
                self.state.pulse = 0.0

        # refractory countdown
        if self._refractory_left > 0:
            self._refractory_left -= 1

        # simple peak detection: rising edge + threshold
        is_peak = (
            (self._refractory_left == 0)
            and (onset >= self.onset_peak_th)
            and (onset > self._last_onset)
        )

        if is_peak:
            # beat detected
            interval_s = self._frames_since_last_beat / self.fps
            if interval_s > 0.0 and interval_s < 2.0:  # ignore weird long gaps
                if self.state.beat_interval == 0.0:
                    self.state.beat_interval = interval_s
                else:
                    a = self.interval_ema_alpha
                    self.state.beat_interval = (1 - a) * self.state.beat_interval + a * interval_s

            self._frames_since_last_beat = 0
            self._refractory_left = self.refractory_frames

            # inject pulse (cap to 1.0)
            self.state.pulse = min(1.0, self.state.pulse + 1.0)

        else:
            self._frames_since_last_beat += 1

        self._last_onset = onset
        return self.state

