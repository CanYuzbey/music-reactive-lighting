
import sys
import os
import glob
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.audio.file_source import frames_from_file
from app.audio.loudness import AdaptiveNormalizer, rms_loudness
from app.audio.onset import onset_strength
from app.audio.pitch_register import spectral_energy_bands, PitchRegister
from app.audio.tempo import ResonatorBPM
from app.mapping.emotion import MoodEngine
from app.mapping.color import ColorEngine

def analyze_file(path):
    print(f"\nAnalyzing: {os.path.basename(path)}")
    try:
        info, frames = frames_from_file(path, fps=20.0, target_sr=None)
    except Exception as e:
        print(f"Skipping {path}: {e}")
        return

    # Initialize Engines
    normalizer = AdaptiveNormalizer()
    tempo_engine = ResonatorBPM(fps=20.0)
    mood_engine = MoodEngine()
    color_engine = ColorEngine(fps=20.0)
    
    # Storage for stats
    stats = {
        "valence": [],
        "arousal": [],
        "hue": [],
        "brightness": [],
        "raw_rms": [],
        "flux": [],
        "density": [],
        "dominance": []
    }
    
    frame_count = 0
    prev_spec_ref = None
    
    for frame in frames:
        frame_count += 1
        
        # 1. Feature Extraction
        # Simulate DC Offset Removal
        frame = frame - np.mean(frame)
        
        rms = rms_loudness(frame)
        onset = onset_strength(frame)
        bands = spectral_energy_bands(frame, info.sample_rate)
        
        # 2. Pipeline Processing
        # Loudness
        b = normalizer.normalize(rms, frame)
        
        # Tempo/Density
        temp_state = tempo_engine.update(onset) # dt is internal or defaults
        
        # Mood
        mood = mood_engine.update(
            loudness=b, 
            onset=onset, 
            pulse=0.0, 
            density=temp_state.density,
            band_energy=bands
        )
        
        # Color
        r, g, b_col = color_engine.map_mood_to_color(mood, temp_state.confidence)
        
        # Extract Hue roughly from RGB
        # (This is a simplified check, color_engine logic is complex)
        
        # Stats
        stats["valence"].append(mood.valence)
        stats["arousal"].append(mood.arousal)
        stats["brightness"].append(b)
        stats["raw_rms"].append(rms) # Store actual RAW RMS
        stats["density"].append(temp_state.density)
        
        # Calculate dominance for debug
        low = bands.get(PitchRegister.LOW, 0.0)
        high = bands.get(PitchRegister.HIGH, 0.0)
        dom = high / (low + high + 0.001)
        stats["dominance"].append(dom)

        if frame_count % 20 == 0:
             print(f"Frame {frame_count}: Onset={onset:.3f}, Pulse={0.0}, Density={temp_state.density:.3f}, Dominance={dom:.3f}")

    # Report
    if frame_count == 0:
        print(" -> No audio data read.")
        return

    avg_v = np.mean(stats["valence"])
    avg_a = np.mean(stats["arousal"])
    avg_b = np.mean(stats["brightness"])
    avg_d = np.mean(stats["density"])
    avg_dom = np.mean(stats["dominance"])
    
    avg_rms = np.mean(stats["raw_rms"])
    avg_flux = np.mean(stats["flux"])
    
    print(f"  -> Avg Brightness (Norm): {avg_b:.2f}")
    print(f"  -> Avg Raw RMS: {avg_rms:.4f}")
    print(f"  -> Avg Flux: {avg_flux:.4f}")
    print(f"  -> Avg Valence: {avg_v:.2f} (0.0=Cold, 1.0=Warm)")
    print(f"  -> Avg Arousal: {avg_a:.2f} (0.0=Calm, 1.0=Excited)")
    print(f"  -> Avg Density: {avg_d:.2f}")
    print(f"  -> Avg Dominance: {avg_dom:.2f} (Engine Target: {mood_engine.avg_dominance:.2f})")
    
    # Interpretation
    if avg_v < 0.4:
        print("  => Conclusion: COLD / SAD")
    elif avg_v > 0.6:
        print("  => Conclusion: WARM / HAPPY")
    else:
        print("  => Conclusion: NEUTRAL")

    if avg_a > 0.5:
        print("  => Energy: HIGH")
    else:
        print("  => Energy: LOW (Arousal < 0.5)")

def main():
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "user_samples")
    files = glob.glob(os.path.join(sample_dir, "*.wav"))
    
    if not files:
        print(f"No .wav files found in {sample_dir}")
        print("Please place 44.1kHz WAV files in the 'samples' folder.")
        return
        
    for f in files:
        analyze_file(f)

if __name__ == "__main__":
    main()
