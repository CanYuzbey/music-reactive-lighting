# Music Reactive Lighting 🎵💡

A high-performance, intelligent desktop audio player that translates music into real-time, emotionally accurate colors and lighting using a **Psychoacoustic Tri-Band Exertion Algorithm**, **Harmonic-Percussive Source Separation (HPSS)**, and a **Persistent Neural Memory** bank.

![Modern Player UI](docs/ui_preview.png) *(UI Preview)*

## 🌟 The Philosophy: Beyond "Sound Activated"
Most music visualizers simply map volume to brightness or bass to red. This project implements a sophisticated **Music Information Retrieval (MIR)** pipeline designed to understand the *emotion* (Valence), *energy* (Arousal), and *groove* of a track in the exact same way a professional Concert Light Jockey does.

By analyzing historical frequency tracking, musical key extraction, and implementing professional macro-pacing rules (like *Chris Kuroda's* "Color Blocks" and *Tobias Rylander's* "Strobe Blanking"), the system naturally understands how to light a dark, heavy trap track versus a warm, bright acoustic ballad without relying on artificial randomness.

## 🔥 Key Technical Features & Algorithms

### 1. Psychoacoustic Tri-Band Exertion & HPSS
The system uses `librosa.effects.hpss` to split audio into **Harmonic** (Vocals, Synths, Melody) and **Percussive** (Drums, Clicks) signals. 
- **Low/Mid/High Normalization**: Instead of raw decibels, the engine tracks the *rolling average* of each frequency band independently. We calculate an "Exertion" score (`current_energy / average_energy`). 
- **Valence (Mood)**: If Harmonic Mids/Highs are exerting harder than the Bass relative to the track's history, the engine shifts toward Warm/Positive colors. If Bass exerts harder, it shifts toward Cool/Deep colors.

### 2. Continuous 2D Circular Hue Mapping
Russell's Circumplex Model of Emotion maps Arousal and Valence onto a 2D plane. 
- The engine uses a fully continuous mathematical arc to map X/Y emotional coordinates to a 360-degree Hue wheel. 
- **Circular Smoothing**: Transitions utilize a custom `CircularExponentialMovingAverage` algorithm. Going from Orange (0.1) to Magenta (0.9) mathematically crosses Red (0.0) instead of dragging backward through Cyan (0.5), preventing muddy/ugly visual artifacts.
- **Key-Based Hue Shifting**: The system runs the Krumhansl-Schmuckler algorithm to extract the Musical Key (e.g., C Major, F# Minor), subtly shifting the root hue based on the Circle of Fifths. Two songs with identical energy levels will have unique color palettes if they are in different musical keys.

### 3. Professional Macro-Pacing (Hip-Hop / Trap Physics)
To prevent visual fatigue during chaotic genres, the UI render loop (`modern_player.py`) enforces strict concert lighting rules:
- **Color Block Inertia**: During "Hype Drops" (Arousal > 0.70), the palette inertia locks to 95%. This prevents the wash color from violently flickering between Red (808 Bass) and Cyan (Trap Hi-Hats) during dense mixes.
- **Strobe Debouncing (Blanking)**: "Light is nothing without darkness." The UI enforces a strict 120ms cooldown whenever a massive 1/8 or 1/4 note Kick or Snare triggers a blinding white bloom. This crushes rapid 16th-note hi-hat flashes, ensuring strobes map to the *groove* rather than glitching on high-frequencies.

### 4. Neural Memory Bank & RL Feedback UI 🧠
The system doesn't just react; it learns human emotion.
- Every time a song is analyzed, a highly detailed mathematical breakdown (RMS, Exertions, Dominance, Arousal, BPM) is logged to a `logs/history/` CSV.
- The player UI includes a **Human Sentiment Panel** where users submit how the song feels and whether the lights matched. This data is dumped to a corresponding `.json` file, building the required dataset to train a future Deep Learning model.
- The `SongMemoryBank` digests the rolling 20-track history to update an ML `global_model.json`, recalculating the engine's center-of-gravity (Dominance Anchors, Valence Multipliers) based on the user's specific music taste.

### 5. Ahead-of-Time (AOT) Flawless Execution
Built with `customtkinter` and `pygame`:
- Analyzes the entire audio file *before* playback. 
- PyGame's audio mixer is dynamically re-initialized via `mutagen` to match the exact Sample Rate of the playing file (44.1kHz, 48kHz, etc.) with a micro-buffer (512 samples), guaranteeing perfect 60FPS zero-latency visual synchronization.

---

## 🏗 Architecture & Pipeline

```mermaid
graph TD
    AudioFile["Audio File (.mp3/.wav)"] --> AOTAnalyzer["AOT Frame Analyzer"]
    
    subgraph Signal Processing Core (Librosa)
        AOTAnalyzer --> HPSS["Harmonic-Percussive<br/>Source Separation"]
        HPSS --> Harmonic["Harmonic Signal"]
        HPSS --> Percussive["Percussive Signal"]
        
        Harmonic --> Mids["Mid/Vocals"]
        Percussive --> Transients["Onset/Transient Detector"]
        AOTAnalyzer --> Key["K-S Musical Key Detector"]
    end
    
    subgraph Tri-Band Exertion & Mood Engine
        Mids --> Exertion["Historical Exertion Math<br/>(Current / Average)"]
        Percussive --> Exertion
        Exertion --> Valence["Continuous 2D Valence Matrix"]
        Transients --> Arousal["Arousal Metric"]
        
        Valence --> Color["Circular Arc Hue Mapping"]
        Arousal --> Color
        Key --> Color
    end
    
    subgraph Front-End & ML Memory
        Color --> Pacing["Macro-Pacing Engine<br/>(Color Blocks & Strobe Debouncer)"]
        Pacing --> PlayerUI["Modern PyGame UI<br/>(60fps Sync)"]
        
        PlayerUI --> Feedback["User Sentiment Feedback"]
        AOTAnalyzer --> LogDump["CSV Diagnostic Log"]
        
        Feedback --> MemoryBank["Neural Memory Bank<br/>(20-Song Digestion)"]
        LogDump --> MemoryBank
        MemoryBank -.->|"Recalculate Bounds"| Exertion
    end
```

---

## 🤖 AI Developer Handoff
If you are an AI reading this repository to continue development, please note the following critical file structure and design patterns:
1. **`app/mapping/color.py`**: Contains the `map_mood_to_color` function. This is where the Continuous 2D Arc Mapping, Circular Hue Smoothing, and Color Block Inertia live. **Always use Circular Smoothing for Hues.**
2. **`app/ui/modern_player.py`**: Contains the Front-end UI and PyGame rendering loop. Pay close attention to `_update_visual(self, time_sec)`, which contains the Strobe Debouncer physics that crushes 16th-note trap hat flashes to preserve visual darkness. It also contains the ML Feedback Panel.
3. **`app/audio/player_backend.py`**: Executes the AOT Analysis. It runs the HPSS separation, extracts the musical key, calculates the frame-by-frame data, and dumps the `analysis_log.csv`.
4. **`logs/history/`**: Where the CSV physics logs and JSON human feedback files are paired and stored. `app/audio/memory_bank.py` digests these to update `global_model.json`.

---

## 🚀 Installation & Usage

### Prerequisites
- Python 3.10+
- `librosa`, `pygame`, `customtkinter`, `numpy`, `mutagen`, `pandas`

### Setup
1. **Clone the Repository**:
    ```bash
    git clone https://github.com/CanYuzbey/music-reactive-lighting.git
    cd music-reactive-lighting
    ```

2. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Run the Desktop Player**:
    ```bash
    python -m app.ui.modern_player
    ```
