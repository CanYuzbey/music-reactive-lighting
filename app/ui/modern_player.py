import os
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import pygame

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
        self.dash_frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        self.val_bpm = ctk.CTkLabel(self.dash_frame, text="0.0", font=("Roboto", 24, "bold"))
        self.val_bpm.grid(row=0, column=0, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="BPM", font=("Roboto", 12), text_color="gray").grid(row=1, column=0, pady=(0,10))
        
        self.val_mood = ctk.CTkLabel(self.dash_frame, text="--", font=("Roboto", 24, "bold"))
        self.val_mood.grid(row=0, column=1, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="MOOD (VALENCE)", font=("Roboto", 12), text_color="gray").grid(row=1, column=1, pady=(0,10))
        
        self.val_energy = ctk.CTkLabel(self.dash_frame, text="--", font=("Roboto", 24, "bold"))
        self.val_energy.grid(row=0, column=2, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="ENERGY (AROUSAL)", font=("Roboto", 12), text_color="gray").grid(row=1, column=2, pady=(0,10))
        
        self.val_color = ctk.CTkLabel(self.dash_frame, text="#000000", font=("Roboto", 24, "bold"))
        self.val_color.grid(row=0, column=3, pady=(10,0))
        ctk.CTkLabel(self.dash_frame, text="HEX LUMINANCE", font=("Roboto", 12), text_color="gray").grid(row=1, column=3, pady=(0,10))

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
            self.frames = self.analyzer.analyze_file(filepath, progress_callback=progress)
            self.after(0, lambda: self._on_analysis_complete(filepath))
        except Exception as e:
            self.after(0, lambda: self.lbl_loading.configure(text=f"Error: {e}"))
            
    def _on_analysis_complete(self, filepath: str):
        self.lbl_loading.place_forget()
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
        
        # We increase base brightness for UI representation 
        # because LEDs are inherently brighter than screen pixels.
        ui_brightness = min(1.0, brightness * 1.5) 
        
        dr = int(r * ui_brightness)
        dg = int(g * ui_brightness)
        db = int(b * ui_brightness)
        
        hex_color = f"#{dr:02x}{dg:02x}{db:02x}"
        self.color_canvas.configure(bg=hex_color)
        
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
