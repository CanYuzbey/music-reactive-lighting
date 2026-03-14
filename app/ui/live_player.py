import tkinter as tk
import customtkinter as ctk
import time
from app.audio.live_analyzer import LiveAnalyzer

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class LivePlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Neon: Live Hardware Audio Sync")
        self.geometry("800x600")
        self.minsize(600, 500)
        
        # Max out FPS for real-time smoothness
        self.fps = 40.0 
        self.analyzer_engine = LiveAnalyzer(fps=self.fps)
        self.is_tracking = False
        
        self.last_strobe_time = 0.0
        
        self.setup_ui()
        self.ui_tick()
        
    def setup_ui(self):
        # 1. Header 
        self.header_frame = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)
        
        self.lbl_title = ctk.CTkLabel(self.header_frame, text="Real-Time System Audio Loopback", font=("Roboto", 18, "bold"))
        self.lbl_title.pack(side="left", padx=20)
        
        # 2. Main Stage 
        self.stage_frame = ctk.CTkFrame(self, corner_radius=20)
        self.stage_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)
        
        self.color_canvas = tk.Canvas(self.stage_frame, bg="#000000", highlightthickness=0)
        self.color_canvas.pack(fill="both", expand=True, padx=2, pady=2)
        
        # 3. Playback Controls (Replaced with Live Connect Controls)
        self.controls_frame = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.controls_frame.pack(side="top", fill="x", padx=20, pady=5)
        
        self.btn_toggle = ctk.CTkButton(self.controls_frame, text="🟢 Start Live Sync", command=self.toggle_sync, width=150)
        self.btn_toggle.pack(side="left", padx=10)
        
        self.lbl_status = ctk.CTkLabel(self.controls_frame, text="Idle", font=("Roboto", 14), text_color="gray")
        self.lbl_status.pack(side="left", padx=10)
        
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

    def toggle_sync(self):
        if self.is_tracking:
            self.analyzer_engine.stop()
            self.is_tracking = False
            self.btn_toggle.configure(text="🟢 Start Live Sync",fg_color=["#3a7ebf", "#1f538d"])
            self.lbl_status.configure(text="Idle", text_color="gray")
        else:
            try:
                self.analyzer_engine.start()
                self.is_tracking = True
                self.btn_toggle.configure(text="🔴 Stop Live Sync", fg_color="darkred", hover_color="red")
                self.lbl_status.configure(text="Listening to System Output...", text_color="green")
            except Exception as e:
                self.lbl_status.configure(text=str(e), text_color="red")

    def ui_tick(self):
        if self.is_tracking:
            frame = self.analyzer_engine.get_latest_frame()
            if frame:
                self._update_visual(frame)
                
        # 60fps UI paint loop (~16ms)
        self.after(16, self.ui_tick)

    def _update_visual(self, frame):
        r, g, b = frame.rgb
        ui_brightness = frame.brightness
        
        # Adaptive Strobe Gating
        energy_gate = max(0.05, frame.arousal)
        raw_flash = frame.onset * 0.5 * energy_gate
        current_ms = time.time() * 1000.0
        cooldown_ms = 120.0  
        
        if raw_flash > 0.15: # Major transient
            if (current_ms - self.last_strobe_time) > cooldown_ms:
                flash = raw_flash
                self.last_strobe_time = current_ms
            else:
                flash = 0.0 
        else: # Minor hit (hi-hat)
            flash = 0.0 
                
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
    app = LivePlayer()
    app.mainloop()
