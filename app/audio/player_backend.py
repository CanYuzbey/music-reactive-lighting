import os
import time
import numpy as np
import librosa
from typing import List, Tuple
from dataclasses import dataclass

from app.audio.onset import onset_strength, normalize_onset
from app.audio.pitch_register import spectral_energy_bands
from app.audio.loudness import rms_loudness, AdaptiveNormalizer
from app.lighting.dynamics import DynamicsController, DynamicsParams
from app.lighting.pulse import PulseTracker
from app.mapping.emotion import MoodEngine
from app.mapping.color import ColorEngine
from app.audio.tempo import ResonatorBPM

@dataclass
class FrameAnalysis:
    time_sec: float
    rgb: Tuple[int, int, int]
    brightness: float
    bpm: float
    bpm_confidence: float
    arousal: float
    valence: float
    raw_rms: float
    onset: float
    key: str
    debug_data: dict

class TrackAnalyzer:
    def __init__(self, fps: float = 20.0, target_sr: int = 44100):
        self.fps = fps
        self.target_sr = target_sr
        
    def analyze_file(self, filepath: str, progress_callback=None) -> Tuple[List[FrameAnalysis], str]:
        """
        Loads the entire audio file, runs the MoodEngine over it,
        and returns a pre-computed list of FrameAnalysis for flawless playback,
        along with the path to the diagnostic log file.
        """
        # 1. Load Audio
        if progress_callback: progress_callback(0.0, "Loading audio file...")
        y, sr = librosa.load(filepath, sr=self.target_sr, mono=True)
        
        # 1a. HPSS (Harmonic-Percussive Source Separation) for Advanced Separation
        if progress_callback: progress_callback(0.04, "Isolating Instruments (HPSS)...")
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        
        # 1b. Global Key Detection (Krumhansl-Schmuckler)
        if progress_callback: progress_callback(0.05, "Extracting Musical Key...")
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_sum = np.sum(chroma, axis=1)
        
        major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
        pitch_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        best_corr = -1
        song_key = "Unknown"
        for i in range(12):
            maj_p = np.roll(major_profile, i)
            min_p = np.roll(minor_profile, i)
            maj_corr = np.corrcoef(chroma_sum, maj_p)[0, 1]
            if maj_corr > best_corr:
                best_corr = maj_corr
                song_key = f"{pitch_names[i]} Maj"
            min_corr = np.corrcoef(chroma_sum, min_p)[0, 1]
            if min_corr > best_corr:
                best_corr = min_corr
                song_key = f"{pitch_names[i]} Min"
                
        # 2. Setup Engines
        if progress_callback: progress_callback(0.1, "Initializing engines...")
        params = DynamicsParams(enter_hold_frames=int(3 * self.fps), drop_boost_frames=int(0.5 * self.fps))
        # 2b. Load Neural Memory 
        from app.audio.memory_bank import SongMemoryBank
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "logs", "history")
        memory = SongMemoryBank(log_dir)
        global_baselines = memory.model
        
        dyn = DynamicsController(params)
        pulse = PulseTracker(fps=self.fps, onset_peak_th=0.60, refractory_s=0.10, decay_s=0.18)
        mood_engine = MoodEngine(global_baselines=global_baselines)
        color_engine = ColorEngine(fps=self.fps)
        normalizer = AdaptiveNormalizer()
        tempo_est = ResonatorBPM(fps=self.fps)
        
        # 3. Chunking
        frame_size = int(sr / self.fps)
        total_frames = len(y) // frame_size
        
        results = []
        
        # Pre-allocate for DC offset tracking
        from app.utils.time_window import TimeWindow
        instant_b = TimeWindow(1)
        short_b = TimeWindow(10)
        
        # 4. Process Loop
        for i in range(total_frames):
            if progress_callback and i % 50 == 0:
                progress_callback(0.1 + 0.9 * (i / total_frames), f"Analyzing frame {i}/{total_frames}...")
                
            start = i * frame_size
            end = start + frame_size
            frame = y[start:end]
            frame_h = y_harmonic[start:end]
            frame_p = y_percussive[start:end]
            
            # Match live pipeline logic exactly
            frame = frame - np.mean(frame) # DC offset
            
            # Loudness
            rms = rms_loudness(frame)
            b = normalizer.normalize(rms, frame=frame)
            instant_b.push(b)
            short_b.push(b)
            ib = instant_b.latest()
            sb = short_b.average()
            
            # Onset (Uses percussive component for strict drum tracking)
            o = normalize_onset(onset_strength(frame_p))
            
            # Bands (Uses harmonic/percussive split for instrument isolation)
            bands = spectral_energy_bands(frame, sr, frame_h, frame_p)
            
            # Dynamics
            st = dyn.update(instant_brightness=ib, short_brightness=sb, onset=o)
            if st.minimal_mode:
                final = 0.90 * sb + 0.10 * ib
            else:
                final = 0.70 * sb + 0.30 * ib
            if st.drop_boost_frames_left > 0:
                final = max(final, ib)
            final = max(0.0, min(1.0, final))
            
            # Pulse & Tempo
            pstate = pulse.update(o)
            tempo_state = tempo_est.update(o)
            
            # Punch Mix (Like live)
            base_level = final * 0.80 
            punch = o * 0.50
            rhythm = pstate.pulse * 0.15
            final_pulsed = max(0.0, min(1.0, base_level + punch + rhythm))
            
            # Mood & Color
            mood = mood_engine.update(
                loudness=b,
                onset=o,
                pulse=pstate.pulse,
                density=tempo_state.density,
                band_energy=bands
            )
            rgb = color_engine.map_mood_to_color(mood, song_key=song_key, bpm_stability=tempo_state.confidence)
            
            results.append(FrameAnalysis(
                time_sec=i / self.fps,
                rgb=rgb,
                brightness=final_pulsed,
                bpm=tempo_state.bpm,
                bpm_confidence=tempo_state.confidence,
                arousal=mood.arousal,
                valence=mood.valence,
                raw_rms=rms,
                onset=o,
                key=song_key,
                debug_data=mood.debug_data
            ))
            
        if progress_callback: progress_callback(0.95, "Writing diagnostic log to memory...")
        
        # 5. Diagnostic Log Dump (20-song rolling memory)
        try:
            import csv
            import glob
            
            # Create logs directory
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "logs", "history")
            os.makedirs(log_dir, exist_ok=True)
            
            # Clean filename
            safe_name = os.path.basename(filepath).replace(" ", "_")
            timestamp = int(time.time())
            log_filename = f"log_{timestamp}_{safe_name}.csv"
            log_path = os.path.join(log_dir, log_filename)
            
            with open(log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Time_sec', 'Hue_Hex', 'Arousal', 'Valence', 'RMS', 'Exert_L', 'Exert_M', 'Exert_H', 'Dominance', 'BPM'])
                for r in results:
                    hex_color = f"#{r.rgb[0]:02x}{r.rgb[1]:02x}{r.rgb[2]:02x}"
                    db = r.debug_data if r.debug_data else {}
                    writer.writerow([
                        f"{r.time_sec:.2f}", 
                        hex_color,
                        f"{r.arousal:.3f}", 
                        f"{r.valence:.3f}", 
                        f"{r.raw_rms:.4f}",
                        f"{db.get('exert_low', 0):.3f}",
                        f"{db.get('exert_mid', 0):.3f}",
                        f"{db.get('exert_high', 0):.3f}",
                        f"{db.get('dominance', 0):.3f}",
                        f"{r.bpm:.0f}"
                    ])
                    
            # Auto-Delete oldest logs if over 20
            existing_logs = glob.glob(os.path.join(log_dir, "*.csv"))
            if len(existing_logs) > 20:
                from app.audio.memory_bank import SongMemoryBank
                memory = SongMemoryBank(log_dir)
                
                # Sort by modification time (oldest first)
                existing_logs.sort(key=os.path.getmtime)
                # Delete until we have 20 log files left
                for old_log in existing_logs[:-20]:
                    # Digest the song before deleting
                    memory.digest_log(old_log)
                    os.remove(old_log)
                    
            print(f"Saved diagnostic log to {log_path} (Memory: {min(len(existing_logs), 20)}/20)")
        except Exception as e:
            print(f"Failed to write log: {e}")
            log_path = ""
            
        if progress_callback: progress_callback(1.0, "Analysis complete!")
        return results, log_path
