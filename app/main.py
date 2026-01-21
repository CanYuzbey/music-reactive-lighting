from app.utils.time_window import TimeWindow


def main():
    print("Music-Reactive Lighting: project initialized ✅")


def test_time_windows():
    # Time windows
    instant = TimeWindow(1)    # anlık
    short = TimeWindow(5)      # kısa dönem
    mid = TimeWindow(20)       # orta dönem

    # Test values (fake loudness / feature values)
    test_values = [0.1, 0.2, 0.4, 0.3, 0.15, 0.1, 0.05]

    for v in test_values:
        instant.push(v)
        short.push(v)
        mid.push(v)

        print(
            f"instant={instant.latest():.2f} | "
            f"short_avg={short.average():.2f} | "
            f"mid_avg={mid.average():.2f}"
        )


if __name__ == "__main__":
    main()
    test_time_windows()


