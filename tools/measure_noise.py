import pyaudio
import numpy as np
import time

def measure():
    CHUNK = 2048
    FORMAT = pyaudio.paFloat32
    CHANNELS = 1
    RATE = 44100
    
    p = pyaudio.PyAudio()
    
    # List devices first
    print("\n--- Audio Devices ---")
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            print(f"ID {i}: {name}")

    try:
        device_id_str = input("\nEnter Device ID to test (default 1): ")
        device_id = int(device_id_str) if device_id_str.strip() else 1
    except ValueError:
        device_id = 1
        
    print(f"\nOpening Device ID {device_id}...")
    
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=device_id,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Error opening device: {e}")
        return

    print("\n[MUTE] LISTENING FOR 3 SECONDS... (PLEASE REMAIN SILENT) [MUTE]")
    
    frames = []
    try:
        for _ in range(0, int(RATE / CHUNK * 3)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(np.frombuffer(data, dtype=np.float32))
    except Exception as e:
        print(f"Read error: {e}")
        
    print("Analyzing...")
    
    if not frames:
        print("No data captured.")
        return
        
    all_data = np.concatenate(frames)
    
    raw_min = np.min(all_data)
    raw_max = np.max(all_data)
    raw_mean = np.mean(all_data) # DC Offset
    raw_rms = np.sqrt(np.mean(all_data**2))
    
    # Simulate DC Removal (what the app does now)
    filtered_data = all_data - raw_mean
    filtered_rms = np.sqrt(np.mean(filtered_data**2))
    
    print("\n" + "="*50)
    print("       AUDIO SIGNAL DIAGNOSTICS REPORT       ")
    print("="*50)
    print(f"Total Samples Processed: {len(all_data)}")
    print(f"\n1. RAW SIGNAL (What the computer hears):")
    print(f"   Min Value : {raw_min:.6f}")
    print(f"   Max Value : {raw_max:.6f}")
    print(f"   DC Offset : {raw_mean:.6f} (Static Voltage)")
    print(f"   Raw RMS   : {raw_rms:.6f} (Total Noise Power)")
    
    print(f"\n2. FILTERED SIGNAL (What the app sees after DC Removal):")
    print(f"   Filtered RMS : {filtered_rms:.6f}")
    
    print("-" * 50)
    print("CONCLUSION:")
    if filtered_rms > 0.02:
        print(f"⚠️  CRITICAL NOISE: The loopback has heavy AC noise ({filtered_rms:.4f}).")
        print(f"👉 Recommended Gate Threshold: {filtered_rms * 1.5:.4f}")
    elif filtered_rms > 0.005:
        print(f"⚠️  MODERATE NOISE: There is still some hiss ({filtered_rms:.4f}).")
        print(f"👉 Recommended Gate Threshold: {filtered_rms * 1.5:.4f}")
    else:
        print(f"✅  CLEAN SIGNAL: Noise is negligible ({filtered_rms:.4f}).")
        print(f"👉 Recommended Gate Threshold: 0.005")
    print("="*50)

    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    measure()
