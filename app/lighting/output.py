from dataclasses import dataclass


@dataclass(frozen=True)
class LightFrame:
    r: int
    g: int
    b: int
    brightness: float  # 0..1


def apply_brightness(rgb: tuple[int, int, int], brightness: float) -> tuple[int, int, int]:
    b = max(0.0, min(1.0, brightness))
    r, g, bl = rgb
    return int(r * b), int(g * b), int(bl * b)


def render_console(rgb: tuple[int, int, int], brightness: float) -> None:
    r2, g2, b2 = apply_brightness(rgb, brightness)
    print(f"RGB=({r2:3d},{g2:3d},{b2:3d})  brightness={brightness:.2f}")


