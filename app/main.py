import numpy as np

from app.utils.time_window import TimeWindow
from app.lighting.dynamics import DynamicsController, DynamicsParams
from app.mapping.color import pick_color
from app.lighting.output import render_console
from app.audio.onset import onset_strength, normalize_onset



def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def main():
    print("Console render test: palette + final brightness (minimal + drop)")

    fps = 10
    instant = TimeWindow(1)
    short = TimeWindow(10)

    params = DynamicsParams(enter_hold_frames=3 * fps, drop_boost_frames=int(0.5 * fps))
    dyn = DynamicsController(params)

    # same timeline as before (low -> drop -> settle)
    timeline = []
    timeline += [0.08] * 35
    timeline += [0.06] * 10
    timeline += [0.95, 0.90, 0.85]
    timeline += [0.40] * 10
    timeline += [0.10] * 20

    for i, base in enumerate(timeline):
        b = clamp01(base + np.random.uniform(-0.02, 0.02))

        instant.push(b)
        short.push(b)

        ib = instant.latest()
        sb = short.average()

        st = dyn.update(instant_brightness=ib, short_brightness=sb)

        # compute final brightness
        if st.minimal_mode:
            final = 0.90 * sb + 0.10 * ib
        else:
            final = 0.70 * sb + 0.30 * ib

        if st.drop_boost_frames_left > 0:
            final = max(final, ib)

        final = clamp01(final)

        # placeholder hue motion (later: key/chord/emotion)
        phase = (i % 30) / 30.0
        rgb = pick_color(phase)

        render_console(rgb, final)


if __name__ == "__main__":
    main()
