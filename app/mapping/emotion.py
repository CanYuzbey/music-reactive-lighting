from dataclasses import dataclass
from app.audio.pitch_register import PitchRegister

@dataclass
class MoodState:
    arousal: float  # 0.0 (calm) -> 1.0 (energetic)
    valence: float  # 0.0 (sad/dark/cool) -> 1.0 (happy/bright/warm)


class MoodEngine:
    def __init__(self):
        self.last_valence = 0.5
        
        # Adaptive Spectral Balancing
        self.avg_dominance = 0.15 # Start with a reasonable low guess
        self.learning_rate = 0.005 # Slow adaptation (Inertia)

    def update(
        self,
        loudness: float,
        onset: float,
        pulse: float,
        density: float,
        band_energy: dict[PitchRegister, float]
    ) -> MoodState:
        """
        Estimates mood based on:
        - Arousal: Driven by Loudness (Power) + Density (Speed/Busy-ness).
        - Valence: Driven by RELATIVE Spectral Balance (Deviations from song average).
        """
        
        # --- Arousal Calculation ---
        # Loudness (0.0-1.0): Raw Volume/Power
        # Density (0.0-1.0): Speed/Busy-ness (0.0=Slow, 1.0=Fast/Trap)
        # Onset (0.0-1.0): Momentary Impact
        
        # High Density + High Loudness = Hype/Aggressive (High Arousal)
        # Low Density + Low Loudness = Calm (Low Arousal)
        # Low Density + High Loudness = Anthem/Epic (Med-High Arousal)
        
        # 50% Loudness, 40% Speed/Density, 10% Impact
        arousal = (loudness * 0.5) + (density * 0.4) + (onset * 0.1)
        
        # --- Valence Calculation (Spectral Balance) ---
        low = band_energy.get(PitchRegister.LOW, 0.0)
        mid = band_energy.get(PitchRegister.MID, 0.0)
        high = band_energy.get(PitchRegister.HIGH, 0.0)
        
        # Dominance: Ratio of Mid+High vs Low
        # We weight Mid by 0.5 because it's "warm" but not "bright/shimmer"
        current_dominance = (mid * 1.0 + high) / (low + mid + high + 0.001)
        
        if loudness > 0.01:
            # 1. Update Long-Term Average (The "Song's Mix")
            self.avg_dominance += (current_dominance - self.avg_dominance) * self.learning_rate
            
            # 2. Calculate Deviation (Relative Warmth)
            deviation = current_dominance - self.avg_dominance
            
            # 3. Hybrid Valence Mixing
            # Absolute Component (Genre Anchor)
            # Center at 0.08 (Deep Bass vs Bass+Mids)
            absolute_valence = 0.5 + (current_dominance - 0.08) * 2.0
            absolute_valence = max(0.0, min(1.0, absolute_valence))
            
            # Adaptive Component (Emotional Phrasing)
            adaptive_valence = 0.5 + (deviation * 4.0)
            
            # Mix: 40% Absolute, 60% Adaptive
            # (We also weight Mid band 1.0 in dominance check now)
            normalized_valence = (absolute_valence * 0.4) + (adaptive_valence * 0.6)
            
            # 4. Bias for Onsets (Kicks are Bass-heavy but energetic)
            if onset > 0.3:
                 normalized_valence += 0.15
                 
            self.last_valence = max(0.0, min(1.0, normalized_valence))
        else:
            # Silence Handling:
            # 1. Decay arousal to 0.0 (Calm)
            arousal = 0.0
            
            # 2. Slowly drift valence to 0.5 (Neutral) to prevent "waking up" with a weird color
            # But do it VERY slowly so short pauses don't reset the vibe.
            self.last_valence += (0.5 - self.last_valence) * 0.01

        return MoodState(
            arousal=max(0.0, min(1.0, arousal)),
            valence=self.last_valence
        )
