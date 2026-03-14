import colorsys
from app.mapping.emotion import MoodState
from app.utils.smoothing import ExponentialMovingAverage

class CircularExponentialMovingAverage:
    """
    Smoothing for Hues (Angles 0.0-1.0) so it doesn't drag across the color wheel.
    E.g. Averaging 0.9 (Magenta) and 0.1 (Orange) should yield 0.0 (Red), not 0.5 (Cyan).
    """
    def __init__(self, alpha=0.1, initial_val=0.0):
        self.alpha = alpha
        self.current = initial_val
        
    def update(self, target: float) -> float:
        # Wrap target just in case
        while target >= 1.0: target -= 1.0
        while target < 0.0: target += 1.0
            
        diff = target - self.current
        # Find shortest path around the circle [-0.5, 0.5]
        if diff > 0.5:
            diff -= 1.0
        elif diff < -0.5:
            diff += 1.0
            
        self.current += diff * self.alpha
        
        if self.current >= 1.0: self.current -= 1.0
        if self.current < 0.0: self.current += 1.0
            
        return self.current


class MoodStabilizer:
    """
    Simulates 'Vibe Inertia'.
    Latches onto a 'Palette Center' (Long-term average).
    Detects 'Song Change' (Drift) to fast-track adaptation.
    """
    def __init__(self, initial_val=0.5):
        self.center = initial_val  # The "Key/Vibe" of the song
        self.drift_counter = 0
        self.is_adapting = True    # Start in adapting mode to find first song fast
        
    def update(self, current_val: float) -> float:
        # Distance from current "Center"
        dist = abs(current_val - self.center)
        
        # 1. Drift Detection (Song Change?)
        # If the input stays different from our center for ~2 seconds, we assume song changed.
        if dist > 0.20: 
            self.drift_counter += 1
        else:
            self.drift_counter = max(0, self.drift_counter - 1)
            
        # Threshold: 2.0s @ 20fps = 40 frames
        if self.drift_counter > 40:
            self.is_adapting = True
            
        # 2. Alpha Selection (Inertia vs Adaptation)
        if self.is_adapting:
            # FAST ADAPTATION (Finding the new vibe)
            alpha = 0.05 
            # If we get close enough, lock it in
            if dist < 0.05 and self.drift_counter == 0:
                self.is_adapting = False
        else:
            # STABLE PALETTE (Inertia)
            # Very slow tracking to ignore random snare hits/drum fills
            alpha = 0.005 
            
        # 3. Update Center
        self.center += (current_val - self.center) * alpha
        
        return self.center

class ColorEngine:
    def __init__(self, fps: float):
        # We replace simple EMA with MoodStabilizer for Palette Logic
        # Valence (Hue) needs strong stabilization for palette consistency
        self.valence_stab = MoodStabilizer(initial_val=0.5)
        self.arousal_stab = MoodStabilizer(initial_val=0.5)
        
        # We MUST use Circular Smoothing for Hue, otherwise it drags straight across the wheel
        # generating hideous muddy Gray/Cyan logic when bouncing from Yellow to Red.
        self.hue_smoother = CircularExponentialMovingAverage(alpha=0.1)
        self.sat_smoother = ExponentialMovingAverage(alpha=0.1)

    def map_mood_to_color(self, mood: MoodState, song_key: str = "C Maj", bpm_stability: float = 0.5) -> tuple[int, int, int]:
        """
        Converts MoodState(arousal, valence) into RGB.
        Applies a subtle Hue Tint based on the Musical Key so every song feels unique.
        """
        
        # 1. Find the "Vibe Center" (Palette)
        palette_valence = self.valence_stab.update(mood.valence)
        palette_arousal = self.arousal_stab.update(mood.arousal)
        
        # 2. Mix Instant Mood with Palette (Analogous Constraint)
        # If Arousal is high (Hype Drop), enforce a "Color Block" (Chris Kuroda Rule).
        # We lock the inertia to 96% Palette / 4% Instant to prevent Trap 808/Hat flickering.
        # Dropped threshold to 0.70 because trap songs oscillate a lot and we do NOT want it 
        # breaking in and out of the "block" constantly during a chorus.
        if palette_arousal > 0.70:
            mix_weight_palette = 0.95
            mix_weight_instant = 0.05
        else:
            mix_weight_palette = 0.70
            mix_weight_instant = 0.30  # Slower than before so standard listening is less chaotic
            
        v = (palette_valence * mix_weight_palette) + (mood.valence * mix_weight_instant)
        a = (palette_arousal * mix_weight_palette) + (mood.arousal * mix_weight_instant)
        
        # 3. Continuous 2D Hue Mapping (Russell's Circumplex Model)
        # Instead of 4-Quadrants with hard boundaries that cause the color to jump,
        # we use a continuous Arc-Blend mapping so every emotional coordinate has a distinct, continuous color.
        
        # HIGH AROUSAL ARC (Top Half):
        # Happy (v=1.0) -> Yellow (0.16)
        # Neutral (v=0.5) -> Red-Orange (0.055)
        # Angry (v=0.0) -> Crimson/Red (0.95)
        high_hue = 0.95 + (v * 0.21)
        
        # LOW AROUSAL ARC (Bottom Half):
        # Calm (v=1.0) -> Green/Turquoise (0.40)
        # Neutral (v=0.5) -> Cyan/Blue (0.55)
        # Sad (v=0.0) -> Deep Blue/Indigo (0.70)
        low_hue = 0.70 - (v * 0.30)
        
        # We circularly blend the High and Low Arcs using the Arousal axis
        def circular_blend(h1, h2, weight):
            while h1 >= 1.0: h1 -= 1.0
            while h2 >= 1.0: h2 -= 1.0
            diff = h1 - h2
            if diff > 0.5: diff -= 1.0
            elif diff < -0.5: diff += 1.0
            res = h2 + (diff * weight)
            if res < 0.0: res += 1.0
            if res >= 1.0: res -= 1.0
            return res
            
        target_hue = circular_blend(high_hue, low_hue, a)

        # 4. Apply Key-Based Musical Tint
        # Extract the root note from "C Maj", "F# Min" etc.
        root_note = song_key.split()[0] if " " in song_key else "C"
        
        # We assign a unique subtle offset to each note based on the chromatic scale
        # Max offset is ±0.05 (18 degrees on hue wheel) so we don't destroy the emotional color mapping
        key_offsets = {
            'C': 0.0, 'C#': +0.02, 'D': -0.02, 'D#': +0.04, 
            'E': -0.04, 'F': +0.06, 'F#': -0.06, 'G': +0.01, 
            'G#': -0.01, 'A': +0.03, 'A#': -0.03, 'B': +0.05
        }
        
        tint = key_offsets.get(root_note, 0.0)
        
        # Invert tint for Minor keys to make them slightly cooler/deeper than their Major counterparts
        if "Min" in song_key: 
            tint = -tint
            
        target_hue += tint
        if target_hue < 0.0: target_hue += 1.0
        if target_hue >= 1.0: target_hue -= 1.0
        
        # 5. Smooth the Hue Transition (remove jagged edges)
        current_hue = self.hue_smoother.update(target_hue)

        # 5. Arousal -> Saturation Mapping
        # Use stabilized arousal for palette consistency.
        # Low Energy -> Pastel/Desaturated (0.4)
        # High Energy -> Vivid (1.0)
        target_sat = 0.4 + (palette_arousal * 0.6)
        current_sat = self.sat_smoother.update(target_sat)

        # Value is driven by Loudness/Transients in main.py, so we default to 1.0 here
        val = 1.0

        r, g, b = colorsys.hsv_to_rgb(current_hue, current_sat, val)
        return int(r * 255), int(g * 255), int(b * 255)
