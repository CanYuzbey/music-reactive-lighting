# Music-Reactive Lighting System

A music-driven lighting system that translates musical structure and perceived emotion into dynamic color palettes in real time.

---

## Overview

This project explores the relationship between **music, emotion, and color** by designing a lighting system that reacts dynamically to musical input.

The system analyzes a playing song, extracts musically meaningful features such as **key, tempo, harmony, and loudness**, and maps these features to **emotional descriptors** using principles from music theory and common-sense perception.

These emotional descriptors are then translated into **color palettes** based on color theory, which are rendered through dynamic lighting rather than a single static color.

---

## Core Concept

Instead of assigning one fixed color to a song, the lighting evolves continuously as the music unfolds.

The visible lighting behavior is influenced by:
- **Tonal characteristics** (e.g. major vs. minor)
- **Tempo and rhythmic energy**
- **Instantaneous loudness**
- **Harmonic context** (planned extension)

This allows the lighting to reflect both the **emotional character** and the **temporal structure** of the music.

---

## System Architecture

The project follows a modular pipeline:

1. **Audio Analysis**  
   Extraction of musical features from an audio file or audio stream.

2. **Emotion Mapping**  
   Conversion of musical features into emotional representations.

3. **Color Mapping**  
   Translation of emotional states into coherent color palettes.

4. **Lighting Control**  
   Real-time rendering of colors on physical or simulated lighting devices.

The architecture is intentionally hardware-agnostic, allowing the lighting backend to be adapted to different LED systems or smart lighting platforms.

---

## Current Status

This repository is under active development.

The initial focus is on building a **minimum viable prototype (MVP)** based on:
- Tempo detection
- Key estimation
- Loudness-based brightness control

Future stages will include:
- Chord recognition
- Musical section detection (verse, chorus, etc.)
- More expressive emotional models
- Advanced lighting animations

---

## Motivation

Music naturally evokes emotional and visual associations in listeners.

This project aims to externalize that internal experience by turning music into a **visually expressive, emotion-driven lighting environment**, bridging signal processing, music theory, and perceptual design.

---

## License

This project is licensed under the MIT License.
