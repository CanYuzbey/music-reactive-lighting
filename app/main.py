import numpy as np

from app.utils.time_window import TimeWindow
from app.lighting.dynamics import DynamicsController, DynamicsParams
from app.mapping.color import pick_color
from app.lighting.output import render_console
from app.lighting.pulse import PulseTracker


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def main():
    print("Console render test: final brightness + onset gating + rhythmic pulse")

    fps = 10
    instant = TimeWindow(1)
    short = TimeWindow(10)  # ~1s smoothing at fps=10

    params = DynamicsParams(
        enter_hold_frames=3 * fps,
        drop_boost_frames=int(0.5 * fps),
    )
    dyn = DynamicsController(params)

    # Pulse tracker uses the same onset signal (0..1)
    pulse = PulseTracker(
        fps=fps,
        onset_peak_th=0.60,   # you can tune this
        refractory_s=0.12,
        decay_s=0.18,
    )

    # timeline (low -> spike -> settle)
    timeline = []
    timeline += [0.08] * 35
    timeline += [0.06] * 10
    timeline += [0.95, 0.90, 0.85]  # spike region
    timeline += [0.40] * 10
    timeline += [0.10] * 20

    prev_b = None

    for i, base in enumerate(timeline):
        # base brightness with small noise
        b = clamp01(base + np.random.uniform(-0.02, 0.02))

        # onset proxy (for this test): sudden brightness change = "hit"
        if prev_b is None:
            o = 0.0
        else:
            o = clamp01(abs(b - prev_b) * 8.0)  # scale for visibility
        prev_b = b

        # time windows
        instant.push(b)
        short.push(b)

        ib = instant.latest()
        sb = short.average()

        # dynamics (minimal + drop gating)
        st = dyn.update(instant_brightness=ib, short_brightness=sb, onset=o)

        # base final brightness from dynamics
        if st.minimal_mode:
            final = 0.90 * sb + 0.10 * ib
        else:
            final = 0.70 * sb + 0.30 * ib

        if st.drop_boost_frames_left > 0:
            final = max(final, ib)

        final = clamp01(final)

        # rhythmic pulse (small additive punch)
        pstate = pulse.update(o)
        pulse_boost = 0.12 * pstate.pulse  # small, safe amount
        final_pulsed = clamp01(final + pulse_boost)

        # placeholder hue motion (later: key/chord/emotion)
        phase = (i % 30) / 30.0
        rgb = pick_color(phase)

        # debug + render
        print(
            f"{i:03d} | inst={ib:.2f} short={sb:.2f} onset={o:.2f} "
            f"pulse={pstate.pulse:.2f} minimal={st.minimal_mode} "
            f"drop_boost={st.drop_boost_frames_left:02d} "
            f"final={final:.2f} final_pulsed={final_pulsed:.2f}"
        )
        render_console(rgb, final_pulsed)


if __name__ == "__main__":
    main()
