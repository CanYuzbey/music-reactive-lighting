import colorsys


def pick_color(phase: float) -> tuple[int, int, int]:
    """
    Simple placeholder palette (will be replaced by key/chord/emotion later).
    phase: 0..1
    """
    palette_hsv = [
        (0.60, 0.80, 1.00),  # blue
        (0.52, 0.80, 1.00),  # cyan
        (0.10, 0.85, 1.00),  # amber
    ]
    idx = int(phase * len(palette_hsv)) % len(palette_hsv)
    h, s, v = palette_hsv[idx]
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)
# color mapping will be implemented here

