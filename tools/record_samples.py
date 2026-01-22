
import pyaudio
import wave
import sys
import os
import struct
import time

def list_devices(p):
    print("\n--- Available Audio Input Devices ---")
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            print(f"ID {i}: {name}")
    print("-------------------------------------\n")

def record(filename, duration, fs=44100, device_index=None):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    
    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=fs,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Error opening stream: {e}")
        return

    print(f"Recording to {filename} for {duration} seconds...")
    frames = []

    for i in range(0, int(fs / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("Recording finished.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save
    filepath = os.path.join(os.path.dirname(__file__), "..", "user_samples", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    wf = wave.open(filepath, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f"Saved: {filepath}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=int, help="Device ID to record from")
    args = parser.parse_args()
    
    p = pyaudio.PyAudio()

    if args.device is None:
        list_devices(p)
        print("Please run with --device <ID> (Use the ID of your Loopback/Stereo Mix or Mic)")
        p.terminate()
        return
    
    p.terminate()

    # 1. Record Silence
    print(f"\n[1/2] Please STOP all music (make it silent).")
    input("Press Enter to record 5s of 'Silence'...")
    record("user_silence.wav", 5, fs=44100, device_index=args.device)

    # 2. Record Music
    print(f"\n[2/2] Please PLAY a loud/energetic song.")
    input("Press Enter to record 10s of 'Music'...")
    record("user_music.wav", 10, fs=44100, device_index=args.device)
    
    print("\nDONE! Please tell the AI you have recorded the samples.")

if __name__ == "__main__":
    main()
