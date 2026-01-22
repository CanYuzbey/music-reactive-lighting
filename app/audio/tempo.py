import numpy as np
from dataclasses import dataclass
from collections import deque

@dataclass
class TempoState:
    bpm: float
    confidence: float
    is_stable: bool
    density: float # 0.0 (Sparse) -> 1.0 (Dense/Busy)

class ResonatorBPM:
    """
    BPM Detection using a bank of Phase Resonators (Comb Filter) combined with IOI Density Check.
    """
    def __init__(self, fps: float, min_bpm=60, max_bpm=180):
        self.fps = fps
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        
        # Create bank of BPMs
        self.bpms = np.arange(min_bpm, max_bpm + 1, 1.0)
        self.n_bins = len(self.bpms)
        
        # Phase Resonators
        self.phases = np.random.rand(self.n_bins)
        self.energies = np.zeros(self.n_bins)
        
        # IOI Tracking for Octave Disambiguation
        self.last_onset_time = 0.0
        self.current_time = 0.0
        self.ioi_buffer = deque(maxlen=20) # Track last 20 intervals
        self.min_ioi = 0.2 # Ignore super fast trills (< 200ms)

        # Parameters
        self.energy_decay = 0.97   
        self.pulse_coupling = 0.4 
        
        # Smoothing
        self.best_bpm = 120.0
        self.confidence = 0.0

    def check_density(self, target_bpm: float) -> float:
        """
        Returns a score (0.0 to 1.0) indicating how many recent IOIs match this BPM's period.
        """
        if len(self.ioi_buffer) < 4:
            return 0.5
            
        period_s = 60.0 / target_bpm
        
        # We check for multiples too! 140 BPM might have IOIs of 0.428s (1 beat) or 0.856s (2 beats)
        # But mainly we want to see if the *fundamental* period exists.
        
        matches = 0
        total_weight = 0.0
        
        # Simple histogram-like check
        tolerance = 0.10 # 10% tolerance
        
        for ioi in self.ioi_buffer:
            # Check 1x
            err = abs(ioi - period_s) / period_s
            weight = 1.0
            
            # Check 2x (missing beat)
            err2 = abs(ioi - period_s * 2) / (period_s * 2)
            
            if err < tolerance:
                matches += 1.0
            elif err2 < tolerance:
                matches += 0.5 # Weak match
                
            total_weight += 1.0
            
        return matches / (total_weight + 0.0001)

    def update(self, onset: float) -> TempoState:
        # Time keeping
        dt = 1.0 / self.fps
        self.current_time += dt
        
        # 1. Update phases
        freqs = self.bpms / 60.0
        self.phases += freqs / self.fps
        self.phases %= 1.0 
        
        # 2. Add Energy from Onset
        is_beat = False
        if onset > 0.01:
            dist = np.abs(self.phases - np.round(self.phases))
            activation = np.exp(- (dist * dist) / 0.05) 
            self.energies += onset * self.pulse_coupling * activation
            
            # Record IOI if onset is significant (Peak-like behavior handled vaguely here, 
            # ideally we'd use a peak detector, but let's assume raw onset works for coarse IOI if sparse)
            # Actually, using raw onset for IOI is noisy.
            # Let's simple check if onset > 0.5 and it's been a while?
            if onset > 0.5 and (self.current_time - self.last_onset_time) > self.min_ioi:
                ioi = self.current_time - self.last_onset_time
                self.ioi_buffer.append(ioi)
                self.last_onset_time = self.current_time
                is_beat = True
            
        # 3. Decay Energy
        self.energies *= self.energy_decay
        
        # 4. Find Best Candidate (Raw Resonance)
        peak_idx = np.argmax(self.energies)
        max_energy = self.energies[peak_idx]
        raw_bpm = self.bpms[peak_idx]
        
        # --- Advanced Octave Correction (Density Check) ---
        
        candidates = [raw_bpm]
        
        # Propose Half
        half_bpm = raw_bpm / 2.0
        if half_bpm >= self.min_bpm: 
            candidates.append(half_bpm)
            
        # Propose Double
        double_bpm = raw_bpm * 2.0
        if double_bpm <= self.max_bpm:
            candidates.append(double_bpm)
            
        # Score candidates by Density
        best_candidate = raw_bpm
        best_score = -1.0
        
        # Tune scores: we prefer the one with highest density match
        # But we also respect the resonance energy.
        # Let's just break ties for Double/Half using Density.
        
        start_density = self.check_density(raw_bpm)
        
        # Check Half?
        if half_bpm >= self.min_bpm:
             half_idx = int(half_bpm - self.min_bpm)
             half_energy = self.energies[half_idx]
             half_density = self.check_density(half_bpm)
             
             # If Half has decent energy (>50%) AND significantly better density (>1.2x)
             if (half_energy > max_energy * 0.5) and (half_density > start_density + 0.15):
                 # Switch to Half
                 raw_bpm = half_bpm
                 max_energy = half_energy
                 start_density = half_density

        # Check Double?
        if double_bpm <= self.max_bpm:
             double_idx = int(double_bpm - self.min_bpm)
             double_energy = self.energies[double_idx]
             double_density = self.check_density(double_bpm)
             
             # If Double has decent energy (>60%) AND better density
             if (double_energy > max_energy * 0.6) and (double_density > start_density + 0.15):
                 raw_bpm = double_bpm
                 max_energy = double_energy

        # 5. Smoothing
        alpha = 0.05 # Slower smoothing
        self.best_bpm = (1-alpha) * self.best_bpm + alpha * raw_bpm
        
        # 6. Confidence
        avg_energy = np.mean(self.energies) + 0.001
        conf_measure = (max_energy - avg_energy) / (max_energy + avg_energy)
        self.confidence = max(0.0, min(1.0, conf_measure * 3.0))

        # 7. Density Calculation (Proxy for Energy/Arousal)
        # 1.0 = Very Busy (16th notes @ 140bpm -> ~100ms)
        # 0.0 = Very Sparse (>1000ms)
        density = 0.0
        if self.ioi_buffer:
            avg_ioi = sum(self.ioi_buffer) / len(self.ioi_buffer)
            # Clip between 1.0s and 0.1s
            # 1.0s -> 0.0 density | 0.1s -> 1.0 density
            density = 1.0 - (avg_ioi - 0.1) / 0.9
            density = max(0.0, min(1.0, density))

        return TempoState(
            bpm=self.best_bpm,
            confidence=self.confidence,
            is_stable=(self.confidence > 0.5),
            density=density
        )
