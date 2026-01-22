import sys

from app.utils.time_window import TimeWindow
from app.lighting.dynamics import DynamicsController, DynamicsParams
from app.lighting.pulse import PulseTracker
from app.lighting.output import render_console

from app.audio.onset import onset_strength, normalize_onset
from app.audio.loudness import rms_loudness, AdaptiveNormalizer
from app.audio.pitch_register import spectral_energy_bands
from app.audio.file_source import frames_from_file

from app.mapping.emotion import MoodEngine
from app.mapping.color import ColorEngine

from app.audio.tempo import ResonatorBPM

# UI Imports
from app.lighting.ui import DebugVisualizer, UIState


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def run_pipeline(frames, fps: float, sample_rate: int, enable_gui: bool = False):
    instant_b = TimeWindow(1)
    short_b = TimeWindow(10)  # ~0.5s at fps=20 (tune if fps changes)

    params = DynamicsParams(
        enter_hold_frames=int(3 * fps),
        drop_boost_frames=int(0.5 * fps),
    )
    dyn = DynamicsController(params)

    pulse = PulseTracker(
        fps=fps,
        onset_peak_th=0.60,
        refractory_s=0.10,
        decay_s=0.18,
    )
    
    # Initialize Engines
    mood_engine = MoodEngine()
    color_engine = ColorEngine(fps=fps)
    normalizer = AdaptiveNormalizer()
    tempo_est = ResonatorBPM(fps=fps)
    
    # UI
    ui = None
    if enable_gui:
        print("Starting GUI...")
        ui = DebugVisualizer(fps=fps)

    # Calibration Buffer
    calibration_frames = []
    is_calibrating = True
    calibration_duration = 40 # 2 seconds @ 20fps

    for i, frame in enumerate(frames):
        # --- DC OFFSET REMOVAL ---
        # User has massive 0.055 DC offset/Noise Floor.
        # We try to center the signal.
        frame = frame - np.mean(frame)
        
        if is_calibrating:
            calibration_frames.append(frame)
            if len(calibration_frames) >= calibration_duration:
                print("Running Calibration...")
                normalizer.calibrate(calibration_frames)
                is_calibrating = False
                print("Calibration Complete. Starting reaction.")
            else:
                # During calibration, output black
                if ui: ui.update((0,0,0), 0.0, UIState(i, fps, 0,0,0,False,0,0,0))
                if (i % 10) == 0: print(f"Calibrating... {i}/{calibration_duration}")
                continue

        # loudness -> brightness
        rms = rms_loudness(frame)
        b = normalizer.normalize(rms, frame=frame)

        instant_b.push(b)
        short_b.push(b)

        ib = instant_b.latest()
        sb = short_b.average()

        # onset
        o = normalize_onset(onset_strength(frame))
        
        # spectral bands for valence
        bands = spectral_energy_bands(frame, sample_rate)

        # dynamics + pulse
        st = dyn.update(instant_brightness=ib, short_brightness=sb, onset=o)

        if st.minimal_mode:
            final = 0.90 * sb + 0.10 * ib
        else:
            final = 0.70 * sb + 0.30 * ib

        if st.drop_boost_frames_left > 0:
            final = max(final, ib)
            
        final = clamp01(final)

        # Update Pulse and Tempo
        pstate = pulse.update(o)
        
        # ResonatorBPM takes raw onset, doesn't need interval
        tempo_state = tempo_est.update(o)
        
        # --- TRANSIENT CONTRAST & PUNCH ---
        # User wants "extra brightness on kicks" but "less brightness" elsewhere.
        # Logic: 
        # Base brightness is reduced to 80% to create headroom.
        # Onset Strength (Transient) adds +50% punch.
        # Pulse State adds +15% rhythmic sway.
        
        base_level = final * 0.80 
        punch = o * 0.50             # Kicks add up to 0.5
        rhythm = pstate.pulse * 0.15 # Pulse adds swaying
        
        final_pulsed = clamp01(base_level + punch + rhythm)
        
        # Startup Mute: Kill lights for first 50 frames (~2.5s) to let filters settle
        if i < 50:
            final_pulsed = 0.0
        

        # --- Mood & Color Update ---
        mood = mood_engine.update(
            loudness=b,
            onset=o,
            pulse=pstate.pulse,
            density=tempo_state.density,
            band_energy=bands
        )
        
        # Pass tempo confidence to Color Engine
        rgb = color_engine.map_mood_to_color(mood, bpm_stability=tempo_state.confidence)

        print(
            f"{i:05d} | b={b:.2f} | BPM={tempo_state.bpm:.1f} (Conf={tempo_state.confidence:.2f}) | "
            f"V={mood.valence:.2f} | RGB={rgb}"
        )
        render_console(rgb, final_pulsed)
        
        if ui:
            if not ui.is_running:
                print("UI Closed. Stopping.")
                break
            
            state = UIState(
                loop_index=i,
                fps=fps,
                brightness=b,
                onset=o,
                pulse=pstate.pulse,
                minimal_mode=st.minimal_mode,
                drop_frames=st.drop_boost_frames_left,
                arousal=mood.arousal,
                valence=mood.valence,
                bpm=tempo_state.bpm,
                bpm_stability=tempo_state.confidence,
                raw_rms=rms
            )
            try:
                ui.update(rgb, final_pulsed, state)
            except Exception:
                break


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Music Reactive Lighting")
    parser.add_argument("file", nargs="?", help="Path to WAV file")
    parser.add_argument("--live", action="store_true", help="Use live microphone input")
    parser.add_argument("--gui", action="store_true", help="Show debug visualization window")
    parser.add_argument("--list-devices", action="store_true", help="List audio input devices")
    parser.add_argument("--device", type=int, help="Input device ID for live mode (e.g. Stereo Mix)")
    
    args = parser.parse_args()

    # Special command: list devices
    if args.list_devices:
        from app.audio.stream_source import list_devices
        list_devices()
        return

    fps = 20.0
    target_sr = 44100
    
    if args.live:
        from app.audio.stream_source import stream_mic
        print("Starting Live Mode...")
        # Live stream iterator with optional device index
        frames = stream_mic(
            fps=fps, 
            sample_rate=target_sr,
            device_index=args.device
        )
        run_pipeline(frames, fps=fps, sample_rate=target_sr, enable_gui=args.gui)
        
    elif args.file:
        print(f"Loading File: {args.file}")
        info, frames = frames_from_file(args.file, fps=fps, target_sr=target_sr)
        print(f"File Info: sr={info.sample_rate} | ch={info.channels}")
        run_pipeline(frames, fps=fps, sample_rate=info.sample_rate, enable_gui=args.gui)
        
    else:
        parser.print_help()



if __name__ == "__main__":
    main()
