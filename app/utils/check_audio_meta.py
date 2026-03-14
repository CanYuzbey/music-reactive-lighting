import os
import glob
from mutagen.mp3 import MP3

def check_samplerates():
    sample_dir = "c:/Users/xxx/Downloads/music-reactive-lighting/samples/"
    files = glob.glob(os.path.join(sample_dir, "*.mp3"))
    
    print("Checking Audio Metadata for Latency Origins:")
    print("-" * 50)
    for f in files:
        audio = MP3(f)
        sr = audio.info.sample_rate
        br = audio.info.bitrate
        length = audio.info.length
        name = os.path.basename(f)
        print(f"File: {name}")
        print(f"   Sample Rate: {sr} Hz | Bitrate: {br//1000} kbps | Length: {length:.1f}s")
        if sr != 44100:
            print(f"   ⚠️ WARNING: Sample rate mismatch! Pygame is locked to 44100Hz. This WILL cause real-time resampling latency.")

if __name__ == "__main__":
    check_samplerates()
