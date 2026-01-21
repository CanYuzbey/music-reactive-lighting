import sys

from app.utils.time_window import TimeWindow
from app.lighting.dynamics import DynamicsController, DynamicsParams
from app.lighting.pulse import PulseTracker
from app.mapping.color import pick_color
from app.lighting.output import render_console

from app.audio.onset import onset_strength, normalize_onset
from app.audio.loudness import rms_loudness, normalize_loudness
from app.audio.file_source import frames_from_file


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def run_pipeline(frames, fps: float, sample_rate: int):
    instant_b = TimeWindow(1)
    short_b = TimeWindow(10)  # ~0.5s at fps=20 (tune if fps changes)

    params = DynamicsParams(
        enter_hold_frames=int(3 * fps),
        drop_boost_frames=int(0.5 * fps),
    )
    dyn = DynamicsController(params)

    pulse = PulseTracker(
        fps=fps,
        onset_peak_th=0.60,
        refractory_s=0.10,
        decay_s=0.18,
    )

    for i, frame in enumerate(frames):
        # loudness -> brightness
        rms = rms_loudness(frame)
        b = normalize_loudness(rms)

        instant_b.push(b)
        short_b.push(b)

        ib = instant_b.latest()
        sb = short_b.average()

        # onset
        o = normalize_onset(onset_strength(frame))

        # dynamics + pulse
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

        # placeholder hue motion (later: key/chord/emotion)
        phase = (i % 30) / 30.0
        rgb = pick_color(phase)

        print(
            f"{i:05d} | b={b:.2f} onset={o:.2f} pulse={pstate.pulse:.2f} "
            f"minimal={st.minimal_mode} drop={st.drop_boost_frames_left:02d} "
            f"final={final_pulsed:.2f}"
        )
        render_console(rgb, final_pulsed)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.main <path_to_44k1_wav>")
        return

    path = sys.argv[1]
    fps = 20.0

    info, frames = frames_from_file(path, fps=fps, target_sr=44100)
    print(f"Loaded: {path} | sr={info.sample_rate} | ch={info.channels} | fps={fps}")

    run_pipeline(frames, fps=fps, sample_rate=info.sample_rate)


if __name__ == "__main__":
    main()
