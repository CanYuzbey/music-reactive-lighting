import numpy as np


def rms_loudness(frame: np.ndarray) -> float:
    """
    Computes RMS loudness from a mono or multi-channel audio frame.
    """
    x = frame
    if x.ndim == 2:
        x = x.mean(axis=1)
    return float(np.sqrt(np.mean(x * x) + 1e-12))

class NoiseFilter:
    """
    Robust Noise Gate with Spectral Flux Analysis.
    Uses FFT to distinguish 'Quiet Music' (Dynamic) from 'Loud Noise' (Static).
    """
    def __init__(self, threshold_on: float = 0.005, threshold_off: float = 0.003, hold_frames: int = 5):
        self.threshold_on = threshold_on   # High RMS Threshold (Loud Music)
        self.threshold_off = threshold_off # RMS Threshold for closing
        self.hold_frames = hold_frames     
        
        # Spectral Settings
        # Hysteresis Thresholds (Linear 0.0-1.0)
        # User Data: Silence=0.055, Music=0.058. SNR is tiny!
        # We must set threshold JUST above silence.
        self.threshold_on = 0.0565
        self.threshold_off = 0.0555
        self.flux_threshold = 2.0  # Increased sensitivity to spectral change
        self.prev_spectrum = None
        self.min_music_rms = 0.056 # Absolute minimum floor to consider signal
        
        self.is_active = False
        self._hold_counter = 0

    def calibrate_from_frames(self, frames: list[np.ndarray]):
        """
        Analyzes a buffer of 'Silence' frames to set the noise threshold automatically.
        """
        if not frames:
            return
            
        print("Calibrating Noise Floor...")
        rms_values = []
        for f in frames:
            # We must apply the same pre-processing? 
            # Ideally main loop uses raw frames, but loudness.py handles the rest.
            # Just compute raw RMS
            r = np.sqrt(np.mean(f * f) + 1e-12)
            rms_values.append(r)
            
        max_noise = max(rms_values)
        avg_noise = np.mean(rms_values)
        
        print(f"  -> Measured Noise Floor: Max={max_noise:.4f}, Avg={avg_noise:.4f}")
        
        # Set threshold JUST above the max noise encountered
        # +10% safety margin or at least +0.002
        margin = max(max_noise * 0.10, 0.002)
        
        self.threshold_on = max_noise + margin
        self.threshold_off = max_noise + (margin * 0.5)
        
        self.min_music_rms = self.threshold_off # Adjust min music floor too
        
        print(f"  -> New Thresholds: ON={self.threshold_on:.4f}, OFF={self.threshold_off:.4f}")

    def update(self, rms: float, frame: np.ndarray = None) -> float:
        """
        Returns filtered RMS. 
        Requires 'frame' for Spectral Analysis!
        """
        
        # 1. Spectral Flux Calculation (Detect Dynamic Change)
        current_flux = 0.0
        if frame is not None and frame.size > 0:
            # Normalize frame for FFT
            # Hanning window to reduce leakage
            windowed = frame * np.hanning(len(frame))
            # Real FFT
            spectrum = np.abs(np.fft.rfft(windowed))
            
            if self.prev_spectrum is not None:
                # Euclidean distance between spectra (Spectral Flux)
                # We focus on lower frequencies (bass/mids) where music energy lives
                n_bins = len(spectrum) // 2 
                diff = spectrum[:n_bins] - self.prev_spectrum[:n_bins]
                # Half-wave rectification (only positive increasing energy counts more?) 
                # actually L2 norm or L1 norm of difference is standard flux
                current_flux = np.sum(np.abs(diff))
                
                # Normalize flux by frame size roughly to keep it consistent
                current_flux /= (len(frame) / 512.0)
                
            self.prev_spectrum = spectrum

        # 2. Hybrid Gate Logic
        gate_should_open = False
        
        # Condition A: Signal is LOUD (Undeniably music)
        if rms > self.threshold_on:
            gate_should_open = True
            
        # Condition B: Signal is QUIET but DYNAMIC (Intro/Outro)
        # RMS must be > min_music_rms (0.057) to ensure we don't flux-analyze pure static
        elif rms > self.min_music_rms:
            # If flux is high, it means the Spectrum is changing (Music), not static (Hum)
            if current_flux > self.flux_threshold:
                 gate_should_open = True

        # 3. State Machine
        if self.is_active:
            # We are currently OPEN.
            # We close only if RMS drops REAL LOW
            if rms < self.threshold_off:
                self._hold_counter += 1
                if self._hold_counter > self.hold_frames:
                    self.is_active = False
                    return 0.0
            else:
                self._hold_counter = 0 
                # If we are in the "Quiet Music" zone (0.057 - 0.065), we KEEP it open
                # as long as rms > threshold_off
        else:
            # We are currently CLOSED.
            if gate_should_open:
                self.is_active = True
                self._hold_counter = 0
                
        return rms if self.is_active else 0.0



class AdaptiveNormalizer:
    def __init__(self, decay_rate: float = 0.01):
        # We now use the NoiseFilter for gating.
        # DYNAMIC CONTRAST TUNING:
        # 1. Intro Sensitivity: Lowered Gate ON to 0.060 to catch soft piano.
        #    Lowered Flux Floor to 0.056 to trust Spectrum Analysis more.
        # 2. Drop Headroom: Removed static boost to prevent "flooding".
        self.filter = NoiseFilter(threshold_on=0.060, threshold_off=0.058, hold_frames=40)
        # Update quiet music detection inside filter manually if needed, 
        # but better to instantiate it correctly.
        self.filter.min_music_rms = 0.056
        
        # Normalization floor
        self.min_rms = 0.058
        self.max_rms = 0.15  
        self.decay_rate = decay_rate
        
        # Output Smoothing State
        self.current_value = 0.0
        
        # Safety limits - Allow deep zoom for intro
        # User has very low dynamic range (0.003 difference). We need to zoom HARD.
        self.min_max_rms = 0.005

    def calibrate(self, frames: list[np.ndarray]):
        self.filter.calibrate_from_frames(frames)

    def normalize(self, rms: float, frame: np.ndarray = None) -> float:
        # 1. Apply Noise Filter (Hysteresis Gate)
        # Now filtering requires the FRAME to check for Spectral Flux (Music) vs Static (Noise)
        filtered_rms = self.filter.update(rms, frame)
        
        target_val = 0.0
        
        # If gate is OPEN (or held open), we compute desired brightness
        if filtered_rms > 0.0:
            # 2. Adaptive Normalization (on the active signal)
            if filtered_rms > self.max_rms:
                self.max_rms = filtered_rms
            else:
                self.max_rms -= self.max_rms * self.decay_rate * 0.1
                
            self.max_rms = max(self.max_rms, self.min_max_rms)
            
            # 3. Scale 0..1
            denom = max(self.max_rms - self.filter.threshold_off, 0.001)
            normalized = (filtered_rms - self.filter.threshold_off) / denom
            normalized = max(0.0, min(1.0, normalized))
            
            # Gamma 0.45 
            target_val = pow(normalized, 0.45)
            
            # REMOVED Static Boost (1.25x).
            # Punch is handled by main.py transients now.
            # target_val = target_val * 1.25
        
        # 4. Output Smoothing (Release Envelope)
        
        if target_val > self.current_value:
             # Fast Attack
            self.current_value = target_val
        else:
            # Slow Release (Decay) for smooth fade out
            # User requested 15-20% faster fade.
            # 0.01 -> 0.012
            self.current_value -= 0.012
            
        self.current_value = max(0.0, min(1.0, self.current_value))
        
        return float(self.current_value)

# Backwards compatibility wrapper (optional, but we will update main.py)
def normalize_loudness(rms: float, floor=0.01, ceiling=0.20) -> float:
    return (rms - floor) / (ceiling - floor)
