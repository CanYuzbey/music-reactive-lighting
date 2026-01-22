
import pyaudio

def main():
    p = pyaudio.PyAudio()
    
    print("\n--- Audio Host APIs ---")
    for i in range(p.get_host_api_count()):
        api_info = p.get_host_api_info_by_index(i)
        print(f"API {i}: {api_info['name']} (Devices: {api_info['deviceCount']})")
        
        # List devices for this API
        for j in range(api_info['deviceCount']):
            dev_info = p.get_device_info_by_host_api_device_index(i, j)
            # Only inputs
            if dev_info['maxInputChannels'] > 0:
                print(f"    Dev {j} (Global ID {dev_info['index']}): {dev_info['name']}")
                
    p.terminate()

if __name__ == "__main__":
    main()
