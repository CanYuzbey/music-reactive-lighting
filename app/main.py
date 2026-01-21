import numpy as np

from app.utils.time_window import TimeWindow
from app.lighting.dynamics import DynamicsController, DynamicsParams


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def main():
    print("Minimal Mode + Drop Boost test")

    fps = 10  # test rate
    instant = TimeWindow(1)
    short = TimeWindow(10)  # ~1s smoothing at fps=10

    # Tune hold time to this fps (enter after ~3s of low energy)
    params = DynamicsParams(enter_hold_frames=3 * fps, drop_boost_frames=int(0.5 * fps))
    dyn = DynamicsController(params)

    # Fake brightness timeline:
    # - calm (low) for a while -> should enter minimal
    # - sudden drop spike -> should override minimal instantly
    timeline = []
    timeline += [0.08] * 35          # low for 3.5s (enter minimal)
    timeline += [0.06] * 10          # still low
    timeline += [0.95, 0.90, 0.85]   # drop spike (should boost)
    timeline += [0.40] * 10          # settles
    timeline += [0.10] * 20          # calm again

    for i, base in enumerate(timeline):
        # add tiny noise so it looks more real
        b = clamp01(base + np.random.uniform(-0.02, 0.02))

        instant.push(b)
        short.push(b)

        ib = instant.latest()
        sb = short.average()

        st = dyn.update(instant_brightness=ib, short_brightness=sb)

        # Example "final brightness" composition:
        # - normal: mix short + instant
        # - minimal: dampen instant contribution
        # - drop boost: force punch
        if st.minimal_mode:
            final = 0.90 * sb + 0.10 * ib
        else:
            final = 0.70 * sb + 0.30 * ib

        if st.drop_boost_frames_left > 0:
            final = max(final, ib)  # instant punch override

        final = clamp01(final)

        print(
            f"{i:03d} | "
            f"instant={ib:.2f} short={sb:.2f} "
            f"minimal={st.minimal_mode} "
            f"drop_boost={st.drop_boost_frames_left:02d} "
            f"final={final:.2f}"
        )


if __name__ == "__main__":
    main()
