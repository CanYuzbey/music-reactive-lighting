import colorsys
from app.mapping.emotion import MoodState
from app.utils.smoothing import ExponentialMovingAverage

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
        
        # We still keep a small smoother for the final output just to remove jagged edges
        self.hue_smoother = ExponentialMovingAverage(alpha=0.1)
        self.sat_smoother = ExponentialMovingAverage(alpha=0.1)

    def map_mood_to_color(self, mood: MoodState, bpm_stability: float = 0.5) -> tuple[int, int, int]:
        """
        Converts MoodState(arousal, valence) into RGB using 2D Circumplex Model.
        """
        
        # 1. Find the "Vibe Center" (Palette)
        palette_valence = self.valence_stab.update(mood.valence)
        palette_arousal = self.arousal_stab.update(mood.arousal)
        
        # 2. Mix Instant Mood with Palette (Analogous Constraint)
        # 2. Mix Instant Mood with Palette (Analogous Constraint)
        # 60% Palette / 40% Instant -> More reactive, allows neighbor colors to breathe.
        v = (palette_valence * 0.60) + (mood.valence * 0.40)
        a = (palette_arousal * 0.60) + (mood.arousal * 0.40)
        
        # 3. 4-Quadrant Hue Map (Rusell's Model)
        # Q1: High Energy + High Valence = Happy (Yellow/Orange)
        # Q2: High Energy + Low Valence  = Tense/Aggressive (Red) -> FIXES "Hype is Blue"
        # Q3: Low Energy  + Low Valence  = Sad/Depressed (Blue/Indigo)
        # Q4: Low Energy  + High Valence = Calm (Cyan/Turquoise/Green)
        
        # Angles (0-1.0 scale): 
        # Red=0.0, Orange=0.08, Yellow=0.16, Green=0.33, Cyan=0.5, Blue=0.66, Purple=0.75, Magenta=0.83
        
        if a > 0.5:
            # HIGH ENERGY (Top Half)
            if v > 0.5:
                # Q1 (Happy): Map 0.5..1.0 -> 0.14 (Yellow) .. 0.08 (Orange)
                # We want it bright and warm.
                rel = (v - 0.5) / 0.5
                target_hue = 0.14 - (rel * 0.06) 
            else:
                # Q2 (Angry): Map 0.5..0.0 -> 0.95 (Crimson) .. 0.0 (Red)
                # Bass Heavy Hype Music goes here!
                rel = (0.5 - v) / 0.5
                # Start at Magenta-Red (0.9) and go to Pure Red (0.0/1.0)
                target_hue = 0.9 + (rel * 0.1)
                if target_hue >= 1.0: target_hue -= 1.0
        else:
            # LOW ENERGY (Bottom Half)
            if v > 0.5:
                # Q4 (Calm): Map 0.5..1.0 -> 0.4 (Greenish) .. 0.5 (Cyan)
                rel = (v - 0.5) / 0.5
                target_hue = 0.35 + (rel * 0.15)
            else:
                # Q3 (Sad): Map 0.5..0.0 -> 0.6 (Blue) .. 0.75 (Purple)
                rel = (0.5 - v) / 0.5
                target_hue = 0.60 + (rel * 0.15)

        
        # 4. Smooth the Hue Transition (remove jagged edges)
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
