# Music Reactive Lighting Engine 🎵💡

> **"Not just a blinker. A Mood Engine."**

This project is a high-fidelity **Audio-Reactive Lighting System** written in Python. Unlike typical "sound-to-light" implementations that simply map volume to brightness, this engine analyzes the **musical emotion** (Valence & Arousal), rhythm, and spectral balance to create a dynamic, living light show.

Designed for **portability**, it is built to run on everything from high-end PCs (via Loopback/WASAPI) to embedded hardware (Raspberry Pi/ESP32) with dedicated audio inputs.

---

## 🔥 Key Features

### 1. The "Mood Engine" (Emotion Analysis)
Lighting should reflect how the music *feels*, not just how loud it is. We use the **Russell's Circumplex Model of Affect**:
-   **Arousal (Energy)**: Driven by Loudness, Onset Density (BPM), and Transient Strength.
-   **Valence (Mood)**: Driven by **Spectral Harmony**.
    -   *Warm/Happy*: High-Mid dominance (Vocals, Guitars, Snares).
    -   *Cool/Deep*: Low-end dominance (Pure Bass, Drones).
    -   **Hybrid Valence**: Combines "Absolute Spectral Anchor" (Genre detection) with "Adaptive Deviation" (Phrasing) to ensure Pop music looks warm and Techno looks intense.

### 2. Auto-Calibration (Smart Noise Gate) 🧠
Hardware audio inputs are noisy. A generic "threshold" fails on 50% of devices.
-   **Startup Calibration**: The system captures the first 2 seconds of "Silence" on boot.
-   **Dynamic Thresholding**: It measures the exact noise floor of your specific hardware (Mic, Line-In, Loopback) and sets the gate *just* above it.
-   **Result**: "True Black" silence, even on noisy inputs.

### 3. Rhythm & Dynamics
-   **RMS-Based Onset Detection**: Captures both "Clicky" transients (High-Freq) and "Thumpy" kicks (Low-Freq).
-   **Cinematic Release**: Brightness decays naturally, preventing a strobe-light effect.
-   **Bass Punch**: Kicks momentarily "overdrive" the brightness for physical impact.

---

## 🛠 Architecture

```mermaid
graph TD
    AudioInput[Audio Input (WASAPI/Mic)] --> |PCM Stream| PreProcess[DC Offset Removal]
    PreProcess --> |Clean Audio| Splitter
    
    subgraph Analysis Core
        Splitter --> |RMS| Loudness[Adaptive Normalizer]
        Splitter --> |FFT| Spectrum[Spectral Flux]
        Splitter --> |Derivative| Onset[Onset Detector]
    end
    
    subgraph Mood Engine
        Spectrum --> ValenceCalc{Valence (Mood)}
        Loudness & Onset --> ArousalCalc{Arousal (Energy)}
        
        ValenceCalc --> |Warmth| ColorMap
        ArousalCalc --> |Intensity| ColorMap
    end
    
    subgraph Output
        Loudness --> |Brightness| Mixer
        ColorMap --> |RGB| Mixer
        Mixer --> |Final Signal| PostProcess[Smoothing & Gamma]
        PostProcess --> LED[LED Controller / UI]
    end
```

## 🧮 Core Logic & Formulas

### Valence (Mood) Calculation
We calculate how "Warm" (Positive) or "Cool" (Negative) the music sounds:

$$ Valence = (0.4 \times V_{absolute}) + (0.6 \times V_{adaptive}) $$

Where:
-   **$V_{absolute}$**: Is the song naturally bright (Pop/Rock) or dark (Techno)? Anchored at ~8% Mid/High dominance.
-   **$V_{adaptive}$**: Is the *current* moment brighter than the song's average?

### Arousal (Energy) Mapping
Maps to the saturation and intensity of the color:

$$ Arousal = \frac{Loudness + (OnsetStrength \times 2.0)}{3.0} $$

---

## 🚀 Installation

1.  **Clone the Repo**:
    ```bash
    git clone https://github.com/your-username/music-reactive-lighting.git
    cd music-reactive-lighting
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Requires `numpy`, `pyaudio`, `scipy`)*

3.  **Run**:
    ```bash
    # Run with GUI Debugger (Best for testing)
    python -m app.main --live --gui
    
    # Run in Headless Mode (For Raspberry Pi)
    python -m app.main --live
    ```

## 🔧 Debugging Tools

We include huge tools for analysis:
-   `tools/measure_noise.py`: Measure your hardware's noise floor.
-   `tools/record_samples.py`: Record audio chunks for testing.
-   `tools/analyze_track.py`: Generate CSV reports of audio files.

---

## 🔮 Future Roadmap

-   [ ] **Hardware Integration**: Serial output for ESP32/Arduino.
-   [ ] **Beat Grid**: Proper Bar/Measure detection (1-2-3-4 counting).
-   [ ] **Genre Presets**: Load "Chill" vs "Party" profiles.

---

*Crafted with ❤️ and Python.*
