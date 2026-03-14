from dataclasses import dataclass
from app.audio.pitch_register import PitchRegister

@dataclass
class MoodState:
    arousal: float  # 0.0 (calm) -> 1.0 (energetic)
    valence: float  # 0.0 (sad/dark/cool) -> 1.0 (happy/bright/warm)
    debug_data: dict = None


class MoodEngine:
    def __init__(self, global_baselines: dict = None):
        self.last_valence = 0.5
        self.last_arousal = 0.0
        
        # Adaptive Tri-Band Exertion (Historical Baselines)
        # If we have neural memory from past 20 songs, use it. Otherwise guess.
        if global_baselines:
            self.avg_low = global_baselines.get("global_avg_bass_exertion", 0.33)
            self.avg_mid = global_baselines.get("global_avg_mid_exertion", 0.33)
            self.avg_high = global_baselines.get("global_avg_high_exertion", 0.33)
            self.last_valence = global_baselines.get("typical_valence", 0.5)
            self.dominance_anchor = global_baselines.get("global_dominance_anchor", 0.66)
            self.valence_spread = global_baselines.get("valence_spread_multiplier", 1.5)
        else:
            self.avg_low = 0.33
            self.avg_mid = 0.33
            self.avg_high = 0.33
            self.dominance_anchor = 0.66
            self.valence_spread = 1.5
            
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
        
        # --- Valence Calculation (Tri-Band Exertion) ---
        low = band_energy.get(PitchRegister.LOW, 0.0)
        mid = band_energy.get(PitchRegister.MID, 0.0)
        high = band_energy.get(PitchRegister.HIGH, 0.0)
        
        if loudness > 0.01:
            # 1. Update Long-Term Averages for each band
            self.avg_low += (low - self.avg_low) * self.learning_rate
            self.avg_mid += (mid - self.avg_mid) * self.learning_rate
            self.avg_high += (high - self.avg_high) * self.learning_rate
            
            # 2. Calculate "Exertion" (Current Energy / Baseline Energy)
            # This normalizes the fact that Bass is always numerically louder
            exert_low = low / (self.avg_low + 1e-4)
            exert_mid = mid / (self.avg_mid + 1e-4)
            exert_high = high / (self.avg_high + 1e-4)
            
            # 3. Assess the dominant exertion
            exertion_sum = exert_low + exert_mid + exert_high + 1e-6
            
            # Dominance of Warm/Bright Exertion (Mid + High vs Total Exertion)
            current_dominance = (exert_mid + exert_high) / exertion_sum
            
            # 4. Hybrid Valence Mixing (Powered by ML Memory Bank)
            # Absolute Component (Dynamic center learned from user history)
            absolute_valence = 0.5 + (current_dominance - self.dominance_anchor) * self.valence_spread
            absolute_valence = max(0.0, min(1.0, absolute_valence))
            
            # Adaptive Component (Deviation from perfect balance)
            deviation = current_dominance - self.dominance_anchor
            # Adaptive is always twice as aggressive to capture small emotional changes
            adaptive_valence = 0.5 + (deviation * (self.valence_spread * 2.0))
            
            # Mix: 30% Absolute, 70% Adaptive (Strongly favor changes in exertion)
            normalized_valence = (absolute_valence * 0.3) + (adaptive_valence * 0.7)
            
            # 5. Energy Update (Optional but requested: arousal peaks when ANY band exerts heavily)
            # A max exertion of > 1.5 means a huge dynamic spike.
            peak_exertion = max(exert_low, exert_mid, exert_high)
            if peak_exertion > 1.5:
                arousal = min(1.0, arousal + (peak_exertion - 1.5) * 0.1)
            
            # 6. Bias for Onsets
            if onset > 0.3:
                 normalized_valence += 0.15
                 
            # 7. DYNAMIC SMOOTHING: 
            # High energy tracks (Pepe Lit, Marshmello) need fast reactive colors.
            # Low energy tracks (Ballerina) need slow, fluid color gliding.
            # We base the transition speed on the current Arousal & Onset (Energy).
            base_glide = 0.05
            energy_boost = (arousal * 0.15) + (onset * 0.2)
            dynamic_glide_speed = base_glide + energy_boost
            # Clamp smoothing speed so it always glides a little, but can snap when needed
            dynamic_glide_speed = max(0.02, min(0.6, dynamic_glide_speed))
                 
            target_valence = max(0.0, min(1.0, normalized_valence))
            self.last_valence += (target_valence - self.last_valence) * dynamic_glide_speed
            
            target_arousal = max(0.0, min(1.0, arousal))
            self.last_arousal += (target_arousal - self.last_arousal) * dynamic_glide_speed
        else:
            # Silence decay
            # Slowly drift valence to 0.5 (Neutral) to prevent "waking up" with a weird color
            # But do it VERY slowly so short pauses don't reset the vibe.
            self.last_valence += (0.5 - self.last_valence) * 0.01
            # Decay arousal to 0.0 (Calm)
            self.last_arousal += (0.0 - self.last_arousal) * 0.05

        debug = {
            "exert_low": exert_low if loudness > 0.01 else 0.0,
            "exert_mid": exert_mid if loudness > 0.01 else 0.0,
            "exert_high": exert_high if loudness > 0.01 else 0.0,
            "dominance": current_dominance if loudness > 0.01 else 0.0,
            "normalized_val": normalized_valence if loudness > 0.01 else 0.5
        }

        return MoodState(
            arousal=self.last_arousal,
            valence=self.last_valence,
            debug_data=debug
        )
