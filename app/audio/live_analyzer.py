import os
import time
import threading
import numpy as np
import pyaudiowpatch as pyaudio
import librosa
from collections import deque
from app.audio.player_backend import FrameAnalysis
from app.audio.onset import onset_strength, normalize_onset
from app.audio.pitch_register import spectral_energy_bands
from app.audio.loudness import rms_loudness, AdaptiveNormalizer
from app.lighting.dynamics import DynamicsController, DynamicsParams
from app.lighting.pulse import PulseTracker
from app.mapping.emotion import MoodEngine
from app.mapping.color import ColorEngine
from app.audio.tempo import ResonatorBPM
from app.utils.time_window import TimeWindow

class LiveAnalyzer:
    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self.p_audio = pyaudio.PyAudio()
        self.is_running = False
        
        # We need a large buffer for MIR algorithms to see 'history' (at least 2 seconds)
        # But we only feed 'new' chunks in periodically to maintain low latency.
        self.sample_rate = 44100
        self.chunk_size = 2048 # ~46ms at 44.1kHz
        self.audio_buffer = np.zeros(self.sample_rate * 3) # 3 seconds of rolling audio
        
        self.latest_analysis = None
        self.process_thread = None
        
        # Setup Engines (like in player_backend)
        params = DynamicsParams(enter_hold_frames=int(3 * self.fps), drop_boost_frames=int(0.5 * self.fps))
        
        # Load Memory for ML Baselines
        from app.audio.memory_bank import SongMemoryBank
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "logs", "history")
        memory = SongMemoryBank(log_dir)
        global_baselines = memory.model
        
        self.dyn = DynamicsController(params)
        self.pulse = PulseTracker(fps=self.fps, onset_peak_th=0.60, refractory_s=0.10, decay_s=0.18)
        self.mood_engine = MoodEngine(global_baselines=global_baselines)
        self.color_engine = ColorEngine(fps=self.fps)
        self.normalizer = AdaptiveNormalizer()
        self.tempo_est = ResonatorBPM(fps=self.fps)
        
        self.instant_b = TimeWindow(1)
        self.short_b = TimeWindow(10)
        
        self.frame_count = 0
        self.song_key = "C Maj" # Default

    def get_default_wasapi_device(self):
        """Finds the default WASAPI loopback device for capturing 'What U Hear'."""
        try:
            wasapi_info = self.p_audio.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("Looks like WASAPI is not available on the system. Exiting...")
            return None
            
        default_speakers = self.p_audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        if not default_speakers["isLoopbackDevice"]:
            for loopback in self.p_audio.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    print(f"Found loopback device: {loopback['name']}")
                    return loopback
        
        print(f"Default loopback found: {default_speakers['name']}")
        return default_speakers

    def start(self):
        if self.is_running: return
        
        self.device = self.get_default_wasapi_device()
        if not self.device:
            raise Exception("No WASAPI Loopback device found. Ensure audio is playing through speakers.")
            
        self.sample_rate = int(self.device["defaultSampleRate"])
        self.chunk_size = int(self.sample_rate / self.fps) # Match chunk size perfectly to desired FPS

        try:
            self.stream = self.p_audio.open(
                format=pyaudio.paFloat32,
                channels=self.device["maxInputChannels"],
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.device["index"],
                stream_callback=self._audio_callback
            )
            self.is_running = True
            print("Live Audio Tracking Started...")
        except Exception as e:
            print(f"Failed to open audio stream: {e}")

    def stop(self):
        self.is_running = False
        if hasattr(self, 'stream') and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Called by PyAudioWPatch when a new chunk is ready."""
        # Convert bytes to numpy float array
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        
        # If stereo, average out to mono for Librosa analysis speed
        if self.device["maxInputChannels"] > 1:
            audio_data = np.mean(audio_data.reshape(-1, self.device["maxInputChannels"]), axis=1)
            
        # Shift old data out, put new data in
        self.audio_buffer = np.roll(self.audio_buffer, -len(audio_data))
        self.audio_buffer[-len(audio_data):] = audio_data
        
        # Analyze the latest frame chunk!
        self._analyze_chunk(audio_data)
        
        return (in_data, pyaudio.paContinue)
        
    def _analyze_chunk(self, frame: np.ndarray):
        """Runs the MIR math on a single frame chunk."""
        self.frame_count += 1
        
        frame = frame - np.mean(frame) # Remove DC offset
        
        # FIX: Librosa HPSS requires > 2048 samples. We process a slightly 
        # larger window from the buffer and take the latest frame length
        analysis_window = 4096
        window = self.audio_buffer[-analysis_window:]
        window = window - np.mean(window)
        window_h, window_p = librosa.effects.hpss(window)
        
        # Extract just the current frame's portion of the separated audio
        frame_h = window_h[-len(frame):]
        frame_p = window_p[-len(frame):]
        
        # Loudness
        rms = rms_loudness(frame)
        b = self.normalizer.normalize(rms, frame=frame)
        self.instant_b.push(b)
        self.short_b.push(b)
        ib = self.instant_b.latest()
        sb = self.short_b.average()
        
        # Onset
        o = normalize_onset(onset_strength(frame_p))
        
        # Bands
        bands = spectral_energy_bands(frame, self.sample_rate, frame_h, frame_p)
        
        # Dynamics Engine
        st = self.dyn.update(instant_brightness=ib, short_brightness=sb, onset=o)
        if st.minimal_mode:
            final = 0.90 * sb + 0.10 * ib
        else:
            final = 0.70 * sb + 0.30 * ib
        if st.drop_boost_frames_left > 0:
            final = max(final, ib)
        final = max(0.0, min(1.0, final))
        
        # Pulse & Tempo
        pstate = self.pulse.update(o)
        tempo_state = self.tempo_est.update(o)
        
        base_level = final * 0.80
        punch = o * 0.50
        rhythm = pstate.pulse * 0.15
        final_pulsed = max(0.0, min(1.0, base_level + punch + rhythm))
        
        # Mood & Color
        mood = self.mood_engine.update(
            loudness=b,
            onset=o,
            pulse=pstate.pulse,
            density=tempo_state.density,
            band_energy=bands
        )
        rgb = self.color_engine.map_mood_to_color(mood, song_key=self.song_key, bpm_stability=tempo_state.confidence)
        
        self.latest_analysis = FrameAnalysis(
            time_sec=self.frame_count / self.fps,
            rgb=rgb,
            brightness=final_pulsed,
            bpm=tempo_state.bpm,
            bpm_confidence=tempo_state.confidence,
            arousal=mood.arousal,
            valence=mood.valence,
            raw_rms=rms,
            onset=o,
            key=self.song_key,
            debug_data=mood.debug_data
        )

    def get_latest_frame(self) -> FrameAnalysis:
        return self.latest_analysis
