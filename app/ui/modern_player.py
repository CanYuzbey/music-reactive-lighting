import os
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import pygame
import mutagen
from app.audio.player_backend import TrackAnalyzer, FrameAnalysis

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ModernPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Neon: Music Reactive Lighting")
        self.geometry("800x600")
        self.minsize(600, 500)
        # Audio Sync State
        # Crucial for low latency: 44.1kHz, 16-bit, stereo, incredibly small buffer (512 frames = ~11ms latency).
        # Default pygame buffer is huge and causes up to 500ms of lag!
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        self.analyzer = TrackAnalyzer(fps=20.0)
        self.frames = []
        self.is_playing = False
        
        # Audio Sync State
        self.seek_offset = 0.0
        self.duration = 0.0
        
        # Physics State
        self.last_strobe_time = 0.0
        
        self.setup_ui()
        self.update_loop() 
        
    def setup_ui(self):
        # 1. Header 
        self.header_frame = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)
        
        self.btn_load = ctk.CTkButton(self.header_frame, text="Load Audio File", command=self.load_file, width=150)
        self.btn_load.pack(side="left", padx=10)
        
        self.lbl_track_name = ctk.CTkLabel(self.header_frame, text="No track loaded", font=("Roboto", 18, "bold"))
        self.lbl_track_name.pack(side="left", padx=20)
        
        # 2. Main Stage 
        self.stage_frame = ctk.CTkFrame(self, corner_radius=20)
        self.stage_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)
        
        self.color_canvas = tk.Canvas(self.stage_frame, bg="#000000", highlightthickness=0)
        self.color_canvas.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.lbl_loading = ctk.CTkLabel(self.color_canvas, text="", font=("Roboto", 24), text_color="white", bg_color="transparent")
        
        # 3. Playback Controls
        self.controls_frame = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.controls_frame.pack(side="top", fill="x", padx=20, pady=5)
        
        self.btn_play = ctk.CTkButton(self.controls_frame, text="▶ Play", command=self.toggle_play, width=100, state="disabled")
        self.btn_play.pack(side="left", padx=10)
        
        self.progress_var = ctk.DoubleVar()
        self.slider_progress = ctk.CTkSlider(self.controls_frame, variable=self.progress_var, from_=0, to=1, state="disabled", command=self.on_slider_change)
        self.slider_progress.pack(side="left", fill="x", expand=True, padx=20)
        
        self.lbl_time = ctk.CTkLabel(self.controls_frame, text="0:00 / 0:00", font=("Roboto", 12))
        self.lbl_time.pack(side="right", padx=10)
        
        # 4. Info Dashboard
        self.dash_frame = ctk.CTkFrame(self, height=80, corner_radius=10)
        self.dash_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        self.dash_frame.grid_columnconfigure((0,1,2,3,4), weight=1)
        
        self.val_key = ctk.CTkLabel(self.dash_frame, text="--", font=("Roboto", 24, "bold"))
        self.val_key.grid(row=0, column=0, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="KEY", font=("Roboto", 12), text_color="gray").grid(row=1, column=0, pady=(0,10))
        
        self.val_bpm = ctk.CTkLabel(self.dash_frame, text="0.0", font=("Roboto", 24, "bold"))
        self.val_bpm.grid(row=0, column=1, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="BPM", font=("Roboto", 12), text_color="gray").grid(row=1, column=1, pady=(0,10))
        
        self.val_mood = ctk.CTkLabel(self.dash_frame, text="--", font=("Roboto", 24, "bold"))
        self.val_mood.grid(row=0, column=2, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="MOOD (VALENCE)", font=("Roboto", 12), text_color="gray").grid(row=1, column=2, pady=(0,10))
        
        self.val_energy = ctk.CTkLabel(self.dash_frame, text="--", font=("Roboto", 24, "bold"))
        self.val_energy.grid(row=0, column=3, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="ENERGY (AROUSAL)", font=("Roboto", 12), text_color="gray").grid(row=1, column=3, pady=(0,10))
        
        self.val_color = ctk.CTkLabel(self.dash_frame, text="#000000", font=("Roboto", 24, "bold"))
        self.val_color.grid(row=0, column=4, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="HEX LUMINANCE", font=("Roboto", 12), text_color="gray").grid(row=1, column=4, pady=(0,10))
        
        # 5. User Feedback Panel
        self.feedback_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.feedback_frame.pack(side="top", fill="x", padx=20, pady=10)
        
        lbl_fb1 = ctk.CTkLabel(self.feedback_frame, text="How do you feel about this song while listening?")
        lbl_fb1.pack(side="top", anchor="w")
        self.entry_feeling = ctk.CTkEntry(self.feedback_frame, width=400)
        self.entry_feeling.pack(side="top", anchor="w", pady=(0, 10))
        
        lbl_fb2 = ctk.CTkLabel(self.feedback_frame, text="Do you think lighting reflects the music good enough?")
        lbl_fb2.pack(side="top", anchor="w")
        
        self.radio_var = tk.StringVar(value="Yes")
        rb_yes = ctk.CTkRadioButton(self.feedback_frame, text="Yes", variable=self.radio_var, value="Yes")
        rb_no = ctk.CTkRadioButton(self.feedback_frame, text="No", variable=self.radio_var, value="No")
        rb_yes.pack(side="left", padx=10)
        rb_no.pack(side="left", padx=10)
        
        self.btn_submit = ctk.CTkButton(self.feedback_frame, text="Submit Memory", command=self.submit_feedback)
        self.btn_submit.pack(side="left", padx=20)
        self.lbl_feedback_status = ctk.CTkLabel(self.feedback_frame, text="")
        self.lbl_feedback_status.pack(side="left", padx=10)
        
    def submit_feedback(self):
        if not hasattr(self, 'current_log_path') or not self.current_log_path:
            self.lbl_feedback_status.configure(text="No track loaded!", text_color="red")
            return
            
        feeling = self.entry_feeling.get()
        reflects = self.radio_var.get()
        
        feedback_data = {
            "feeling": feeling,
            "reflects_music": reflects,
            "log_file": os.path.basename(self.current_log_path)
        }
        
        feedback_path = self.current_log_path.replace(".csv", "_feedback.json")
        try:
            import json
            with open(feedback_path, 'w') as f:
                json.dump(feedback_data, f, indent=4)
            self.lbl_feedback_status.configure(text="Saved to Neural Memory Bank!", text_color="green")
            self.entry_feeling.delete(0, 'end')
        except Exception as e:
            self.lbl_feedback_status.configure(text="Error saving metadata.", text_color="red")

    def load_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac")]
        )
        if not filepath:
            return
            
        filename = os.path.basename(filepath)
        self.lbl_track_name.configure(text=filename)
        
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self.is_playing = False
        self.btn_play.configure(state="disabled", text="▶ Play")
        self.slider_progress.configure(state="disabled")
        
        self.frames = []
        threading.Thread(target=self._analyze_worker, args=(filepath,), daemon=True).start()

    def _analyze_worker(self, filepath: str):
        def progress(perc: float, status: str):
            self.after(0, lambda: self.lbl_loading.configure(text=f"{status} ({int(perc*100)}%)"))
            
        self.after(0, lambda: self.lbl_loading.place(relx=0.5, rely=0.5, anchor="center"))
        
        try:
            self.frames, self.current_log_path = self.analyzer.analyze_file(filepath, progress_callback=progress)
            self.after(0, lambda: self._on_analysis_complete(filepath))
        except Exception as e:
            self.after(0, lambda: self.lbl_loading.configure(text=f"Error: {e}"))
            
    def _on_analysis_complete(self, filepath: str):
        self.lbl_loading.place_forget()
        
        # Extract original sample rate and re-init pygame mixer to prevent latency
        try:
            audio_meta = mutagen.File(filepath)
            if audio_meta is not None and hasattr(audio_meta.info, 'sample_rate'):
                sr = audio_meta.info.sample_rate
                pygame.mixer.quit()
                pygame.mixer.pre_init(frequency=sr, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
                print(f"Dynamically locked PyGame Mixer to {sr}Hz to prevent resampling latency.")
        except Exception as e:
            print(f"Could not read sample rate from mutagen, defaulting to 44100Hz: {e}")
            
        pygame.mixer.music.load(filepath)
        
        self.duration = len(self.frames) / self.analyzer.fps
        self.slider_progress.configure(state="normal", to=self.duration)
        self.progress_var.set(0.0)
        self.seek_offset = 0.0
        
        self.btn_play.configure(state="normal", text="▶ Play")
        self._update_visual(0.0)

    def toggle_play(self):
        if not self.frames: return
        
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.btn_play.configure(text="▶ Play")
        else:
            time_to_play = self.progress_var.get()
            self.seek_offset = time_to_play
            pygame.mixer.music.play(start=time_to_play)
            self.is_playing = True
            self.btn_play.configure(text="|| Pause")

    def on_slider_change(self, value):
        if not self.frames: return
        t = float(value)
        self.seek_offset = t
        if self.is_playing:
            pygame.mixer.music.play(start=t)
        self._update_visual(t)

    def format_time(self, seconds: float) -> str:
        s = int(seconds)
        return f"{s//60}:{s%60:02d}"

    def update_loop(self):
        if self.is_playing and self.frames:
            pos_ms = pygame.mixer.music.get_pos()
            
            # Pygame specific exact timeline logic
            if pos_ms >= 0:
                current_time = (pos_ms / 1000.0) + self.seek_offset
                
                # Enforce bounds
                if current_time > self.duration:
                    self.is_playing = False
                    self.btn_play.configure(text="▶ Play")
                    current_time = self.duration
                    
                self.progress_var.set(current_time)
                self.lbl_time.configure(text=f"{self.format_time(current_time)} / {self.format_time(self.duration)}")
                self._update_visual(current_time)
                
            elif pos_ms == -1: # Music stopped
                 self.is_playing = False
                 self.btn_play.configure(text="▶ Play")

        self.after(16, self.update_loop)

    def _update_visual(self, time_sec: float):
        if not self.frames: return
        
        idx = int(time_sec * self.analyzer.fps)
        if idx >= len(self.frames):
            idx = len(self.frames) - 1
            
        frame = self.frames[idx]
        
        r, g, b = frame.rgb
        brightness = frame.brightness
        
        # UI FIX: We were previously multiplying brightness by 1.5, causing it to
        # clamp to 1.0 constantly. This erased the visual difference between a 
        # normal loud part and a massive drum kick (punch).
        # We will use true brightness, but add a literal "Flash" for high onset.
        
        ui_brightness = brightness
        
        # Adaptive Strobe Gating (Fatigue Reduction) & Debouncing
        # Instead of firing a huge flash mathematically on every drum hit, 
        # we scale the drum flash by the track's global Arousal (Energy).
        energy_gate = max(0.05, frame.arousal)
        raw_flash = frame.onset * 0.5 * energy_gate
        
        # Debounce (Tobias Rylander Rule): Enforce cooldown between massive blooms
        # to ensure they map to Kicks/Snares and ignore fast Trap hats (16th notes are ~70-90ms at 140BPM).
        current_ms = time_sec * 1000.0
        cooldown_ms = 120.0  # 1/8 note at 250BPM. Fast enough for double kicks, slow enough to crush 16th-note trap hats.
        
        if raw_flash > 0.15:
            # This is a major structural hit
            if (current_ms - self.last_strobe_time) > cooldown_ms:
                flash = raw_flash
                self.last_strobe_time = current_ms
            else:
                flash = 0.0 # Crushed by cooldown
        else:
            # Minor hits (hi-hats, shakers)
            # FATAL BUG FIX: Minor hits should NEVER cause a white bloom! 
            # They already pulse gracefully in the base `ui_brightness` channel.
            flash = 0.0 
                
        # Fade out the strobe smoothly if it's very close to recent (optional, but raw pop is better)
        
        dr = int(min(255, (r * ui_brightness) + (255 * flash)))
        dg = int(min(255, (g * ui_brightness) + (255 * flash)))
        db = int(min(255, (b * ui_brightness) + (255 * flash)))
        
        # Minimum idle glow
        dr = max(5, dr)
        dg = max(5, dg)
        db = max(5, db)
        
        hex_color = f"#{dr:02x}{dg:02x}{db:02x}"
        self.color_canvas.configure(bg=hex_color)
        
        self.val_key.configure(text=f"{frame.key}")
        self.val_bpm.configure(text=f"{frame.bpm:.0f}")
        
        mood_str = "NEUTRAL"
        if frame.valence > 0.6: mood_str = "WARM/HAPPY"
        elif frame.valence < 0.4: mood_str = "COOL/DEEP"
        self.val_mood.configure(text=f"{mood_str}\n({frame.valence:.2f})")
        
        energy_str = "LOW"
        if frame.arousal > 0.7: energy_str = "HIGH"
        elif frame.arousal > 0.4: energy_str = "MED"
        self.val_energy.configure(text=f"{energy_str}\n({frame.arousal:.2f})")
        
        self.val_color.configure(text=hex_color.upper())

if __name__ == "__main__":
    app = ModernPlayer()
    app.mainloop()
