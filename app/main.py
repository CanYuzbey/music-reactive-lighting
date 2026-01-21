import numpy as np

from app.utils.time_window import TimeWindow
from app.lighting.dynamics import DynamicsController, DynamicsParams
from app.mapping.color import pick_color
from app.lighting.output import render_console


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def main():
    print("Console render test: palette + final brightness (minimal + drop + onset gating)")

    fps = 10
    instant = TimeWindow(1)
    short = TimeWindow(10)  # ~1s smoothing at fps=10

    params = DynamicsParams(
        enter_hold_frames=3 * fps,
        drop_boost_frames=int(0.5 * fps),
        # these defaults exist in DynamicsParams; set explicitly if you want:
        # low_enter=0.15,
        # low_exit=0.20,
        # peak_th=0.65,
        # surprise_th=0.35,
        # onset_th=0.55,
    )
    dyn = DynamicsController(params)

    # same timeline as before (low -> drop -> settle)
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

        # onset proxy: sudden change in brightness implies a "hit"
        if prev_b is None:
            o = 0.0
        else:
            o = clamp01(abs(b - prev_b) * 8.0)  # scale for visibility in this test
        prev_b = b

        # time windows
        instant.push(b)
        short.push(b)

        ib = instant.latest()
        sb = short.average()

        # dynamics update (requires onset parameter)
        st = dyn.update(instant_brightness=ib, short_brightness=sb, onset=o)

        # compute final brightness
        if st.minimal_mode:
            final = 0.90 * sb + 0.10 * ib
        else:
            final = 0.70 * sb + 0.30 * ib

        # drop boost override
        if st.drop_boost_frames_left > 0:
            final = max(final, ib)

        final = clamp01(final)

        # placeholder hue motion (later: key/chord/emotion)
        phase = (i % 30) / 30.0
        rgb = pick_color(phase)

        # debug + render
        print(
            f"{i:03d} | instant={ib:.2f} short={sb:.2f} onset={o:.2f} "
            f"minimal={st.minimal_mode} drop_boost={st.drop_boost_frames_left:02d} "
            f"final={final:.2f}"
        )
        render_console(rgb, final)


if __name__ == "__main__":
    main()
