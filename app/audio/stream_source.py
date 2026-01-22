import pyaudio
import numpy as np
import time
from typing import Iterator

def list_devices():
    """Prints all available audio input devices."""
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("\n--- Available Audio Input Devices ---")
    found_any = False
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            print(f"ID {i}: {name}")
            found_any = True
    
    if not found_any:
        print("No input devices found.")
    else:
        print("\nTo use a specific device: python -m app.main --live --device <ID>")
        print("For System Audio: Look for 'Stereo Mix', 'Loopback', or 'What U Hear'.\nIf missing, enable 'Stereo Mix' in Windows Sound Settings.\n")
            
    p.terminate()

def stream_mic(
    fps: float = 20.0,
    sample_rate: int = 44100,
    buffer_seconds: float = 0.5,
    device_index: int | None = None
) -> Iterator[np.ndarray]:
    """
    Yields mono float32 frames from the specified or default input device.
    """
    
    chunk_size = int(sample_rate / fps)
    # PyAudio format
    p = pyaudio.PyAudio()
    
    # WASAPI often fails with 44100 if the system is set to 48000.
    # We try 44100 first, then 48000, then 96000.
    rates_to_try = [sample_rate, 48000, 96000, 44100] 
    rates_to_try = sorted(list(set(rates_to_try)), key=lambda x: rates_to_try.index(x))
    
    stream = None
    final_sr = sample_rate
    
    for sr in rates_to_try:
        try:
            print(f"Attempting playback at {sr}Hz...")
            # Recalculate chunk for this rate to keep approx FPS
            current_chunk = int(sr / fps)
            
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=sr,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=current_chunk
            )
            final_sr = sr
            print(f"Success! Running at {final_sr}Hz")
            chunk_size = current_chunk # Update for the read loop
            break
        except Exception as e:
            print(f"Failed at {sr}Hz: {e}")
            
    if stream is None:
        print("Error: Could not open audio stream with any common sample rate.")
        print("Try running `python -m app.main --list-devices` to find valid IDs.")
        return

    print(f"Stream started: {final_sr}Hz, Device ID: {device_index}")

    print(f"Live Audio Started | SR={sample_rate} | FPS={fps} | CHUNK={chunk_size}")
    
    try:
        while True:
            # Blocking read (keeping it simple for now)
            # In a GUI app, you'd want this in a separate thread.
            raw_data = stream.read(chunk_size, exception_on_overflow=False)
            
            # Convert raw bytes to float32 numpy array
            frame = np.frombuffer(raw_data, dtype=np.float32)
            
            # DC OFFSET REMOVAL (Essential for Loopback devices)
            # Many loopback drivers add a constant bias (e.g. 0.05).
            # Subtracting the mean centers the signal at 0.0, removing "fake" noise.
            # Use subtraction assignment to create new array since frombuffer might be read-only
            frame = frame - np.mean(frame)
            
            yield frame
            
    except KeyboardInterrupt:
        print("\nStopping audio stream...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
