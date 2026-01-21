import numpy as np

from app.utils.time_window import TimeWindow
from app.lighting.dynamics import DynamicsController, DynamicsParams
from app.lighting.pulse import PulseTracker
from app.mapping.color import pick_color
from app.lighting.output import render_console

from app.audio.onset import onset_strength, normalize_onset
from app.audio.loudness import rms_loudness, normalize_loudness
from app.audio.sim import sine_with_hits


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def main():
    print("Real onset test: audio frame -> loudness/brightness + onset -> dynamics + pulse")

    fps = 20
    sample_rate = 44100
    frame_size = int(sample_rate / fps)  # ~1 frame per tick

    instant_b = TimeWindow(1)
    short_b = TimeWindow(10)  # ~0.5s at fps=20

    params = DynamicsParams(
        enter_hold_frames=3 * fps,
        drop_boost_frames=int(0.5 * fps),
    )
    dyn = DynamicsController(params)

    pulse = PulseTracker(
        fps=fps,
        onset_peak_th=0.60,
        refractory_s=0.10,
        decay_s=0.18,
    )

    t0 = 0.0
    for i in range(200):
        # --- fake audio frame (will be replaced by real input later) ---
        frame = sine_with_hits(
            sample_rate=sample_rate,
            frame_size=frame_size,
            t0=t0,
            base_freq=220.0 + 40.0 * np.sin(i / 50.0),
            hit_every_s=0.5,
            hit_strength=0.9,
        )
        t0 += frame_size / sample_rate

        # --- loudness -> brightness ---
        rms = rms_loudness(frame)
        b = normalize_loudness(rms)

        instant_b.push(b)
        short_b.push(b)

        ib = instant_b.latest()
        sb = short_b.average()

        # --- real onset (transient strength) ---
        o = normalize_onset(onset_strength(frame))

        # --- dynamics + pulse ---
        st = dyn.update(instant_brightness=ib, short_brightness=sb, onset=o)

        if st.minimal_mode:
            final = 0.90 * sb + 0.10 * ib
        else:
            final = 0.70 * sb + 0.30 * ib

        if st.drop_boost_frames_left > 0:
            final = max(final, ib)

        final = clamp01(final)

        pstate = pulse.update(o)
        final_pulsed = clamp01(final + 0.12 * pstate.pulse)

        # placeholder hue motion
        phase = (i % 30) / 30.0
        rgb = pick_color(phase)

        print(
            f"{i:03d} | b={b:.2f} ib={ib:.2f} sb={sb:.2f} "
            f"onset={o:.2f} pulse={pstate.pulse:.2f} "
            f"minimal={st.minimal_mode} drop={st.drop_boost_frames_left:02d} "
            f"final={final_pulsed:.2f}"
        )
        render_console(rgb, final_pulsed)


if __name__ == "__main__":
    main()
