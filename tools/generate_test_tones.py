
import numpy as np
import soundfile as sf
import os

def save_wav(name, data, sr=44100):
    # Ensure data is float32
    data = data.astype(np.float32)
    path = os.path.join(os.path.dirname(__file__), "..", "samples", name)
    sf.write(path, data, sr)
    print(f"Generated: {path}")

def generate_tone(freq, duration, sr=44100):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return 0.5 * np.sin(2 * np.pi * freq * t)

def generate_beat(bpm, duration, freq=100, sr=44100):
    # Simple decay envelope kick
    samples = int(sr * duration)
    audio = np.zeros(samples)
    
    interval = 60.0 / bpm
    interval_samples = int(interval * sr)
    
    # create a single kick
    kick_len = int(0.1 * sr)
    t = np.linspace(0, 0.1, kick_len, endpoint=False)
    kick = 0.8 * np.sin(2 * np.pi * freq * t) * np.exp(-15 * t)
    
    for i in range(0, samples, interval_samples):
        if i + kick_len < samples:
            audio[i:i+kick_len] += kick
            
    return audio

def main():
    sr = 44100
    
    # 1. Pure Bass (Should be Low Valence -> Blue/Indigo)
    # 60Hz Sine, 5 seconds
    bass = generate_tone(60, 5.0, sr)
    save_wav("test_pure_bass.wav", bass, sr)
    
    # 2. Pure High (Should be High Valence -> Cyan/Green if calm, Orange if active)
    # 4000Hz Sine, 5 seconds
    high = generate_tone(4000, 5.0, sr)
    save_wav("test_pure_high.wav", high, sr)
    
    # 3. Fast Techno (High Arousal + Low Valence -> Should represent RED)
    # 150 BPM, Low Freq Kick
    techno = generate_beat(150, 5.0, freq=60, sr=sr)
    save_wav("test_fast_dark.wav", techno, sr)
    
    # 4. Happy Pop (High Arousal + High Valence -> Should represent YELLOW)
    # 120 BPM, High Freq "Ping"
    pop = generate_beat(120, 5.0, freq=1000, sr=sr)
    save_wav("test_fast_bright.wav", pop, sr)

if __name__ == "__main__":
    main()
