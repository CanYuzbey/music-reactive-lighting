# AI Handoff & Architecture Guide
*Please read this document completely before modifying the codebase.*

## Project State Summary
This project has evolved from a basic "sound-to-light" visualizer into a highly advanced, psychoacoustic emotion-mapping engine. It uses Music Information Retrieval (MIR) techniques to mimic how professional Concert Lighting Designers light shows. 

The engine evaluates songs via **Russell's Circumplex Model of Emotion** (Arousal and Valence) and outputs colors and strobe timings based strictly on structural grooves and historically-normalized metrics.

## Core Architectural Pillars (DO NOT BREAK THESE)

### 1. Psychoacoustic Tri-Band Normalization (`app/mapping/emotion.py` & `app/audio/pitch_register.py`)
- We do not use raw decibel levels to determine mood. We use `librosa.effects.hpss` to separate Harmonic and Percussive signals.
- We track the *rolling average* of Low, Mid, and High frequencies and calculate their **Exertion** (`current / average`). 
- If a song's Mids (Vocals) are exerting harder relative to the track's history than the Lows (Bass), the Valence goes UP (Happy/Warm). 

### 2. Continuous Circular Hue Mapping (`app/mapping/color.py`)
- We map Emotional Coordinates (Arousal + Valence) to a continuous 2D arc. 
- **CRITICAL:** Hues are Angles on a circle. You must *never* use a linear smoother (like standard EMA) to average two hues. Averaging Yellow (0.16) and Crimson (0.95) linearly results in Cyan (0.55), creating hideous muddy colors. 
- You must always use the `CircularExponentialMovingAverage` class when smoothing hues, which finds the shortest path around the color wheel (passing through Red at 0.0).

### 3. Musical Key Hue Shifting (`app/mapping/color.py`)
- The backend runs Krumhansl-Schmuckler to fetch the Musical Key (e.g., C Maj).
- We map the root note against the Chromatic Scale to apply a subtle Hue Tint (±0.05). This ensures two tracks with identical Valence/Arousal but different keys look visually distinct. Minor keys invert the tint to be slightly cooler.

### 4. Macro-Pacing & Trap Physics (`app/ui/modern_player.py` & `color.py`)
- **Color Blocks:** When Trap/Hip-Hop drops hit (Arousal > 0.70), we lock the inertia of the Color Palette to 95%. This prevents the 808 Bass and Trap Hi-Hats from violently oscillating the wash color between Red and Cyan.
- **Strobe Debouncing:** We do *not* flash white on every transient. We enforce a `120ms` cooldown (blanking window) when a massive kick/snare boom fires. This deliberately "crushes" 16th-note trap hi-hats, enforcing "Darkness" and rhythmic orientation so that blooms only map to the structural groove. Minor hits are set explicitly to `flash = 0.0`.

### 5. Neural Memory & ML Feedback (`app/audio/memory_bank.py` & `logs/`)
- During playback analysis, the player dumps a massive CSV of frame-by-frame physics (RMS, Exertion, Valence) to `logs/history/`.
- The user can submit human sentiment reviews via the UI dashboard (e.g. "Felt dark and depressed"). This creates a paired `_feedback.json` file.
- The `SongMemoryBank` reads this 20-track rolling cache and recalculates `global_model.json` to drift the fundamental Dominance/Valence mathematical anchors toward the user's specific music taste. *DO NOT alter the `logs/` output formats without updating the memory bank ingestion parser.*

## Where to go from here
- The ML Feedback loop is currently collecting data. In future sessions, a Deep Learning/NN model could be built to train a scikit-learn or PyTorch model on the CSV+JSON dataset.
- Hardware implementation: The AOT (Ahead of Time) `FrameAnalysis` lists calculated in `player_backend.py` can be streamed linearly over PySerial to a high-speed WLED controller. 
