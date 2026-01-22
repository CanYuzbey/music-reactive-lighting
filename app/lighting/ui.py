import tkinter as tk
from dataclasses import dataclass

@dataclass
class UIState:
    loop_index: int
    fps: float
    brightness: float
    onset: float
    pulse: float
    minimal_mode: bool
    drop_frames: int
    arousal: float
    valence: float
    bpm: float = 0.0,
    bpm_stability: float = 0.0
    raw_rms: float = 0.0

class DebugVisualizer:
    def __init__(self, fps: float):
        self.root = tk.Tk()
        self.root.title("Music Reactive Lighting - Debug")
        self.root.geometry("400x550")
        self.root.configure(bg="#202020")
        
        # Color Display (Canvas)
        self.canvas = tk.Canvas(self.root, width=300, height=200, bg="#000000", highlightthickness=0)
        self.canvas.pack(pady=20)
        
        # Info Labels
        self.labels = {}
        self.add_label("status", "Initializing...")
        self.add_label("tempo", "")
        self.add_label("features", "")
        self.add_label("mood", "")
        self.add_label("dynamics", "")
        self.add_label("rgb", "")
        
        self.fps = fps
        self.last_update = 0
        self.is_running = True
        
        # Bring to front
        self.root.attributes("-topmost", True)
        # Disable topmost after 500ms so it doesn't annoy
        self.root.after(500, lambda: self.root.attributes("-topmost", False))
        
        # Handle Close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def on_close(self):
        self.is_running = False
        self.root.destroy()
        
    def add_label(self, key: str, text: str):
        lbl = tk.Label(
            self.root, 
            text=text, 
            fg="#cccccc", 
            bg="#202020", 
            font=("Consolas", 10), 
            justify="left"
        )
        lbl.pack(anchor="w", padx=20, pady=2)
        self.labels[key] = lbl

    def update(self, rgb: tuple[int, int, int], final_brightness: float, state: UIState):
        """
        Updates the UI. Should be called every frame from the main loop.
        """
        r, g, b = rgb
        
        # Simulate brightness on the color patch
        # (We multiply RGB by brightness for display, though LEDs handled differently)
        # However, for pure color monitoring, maybe we keep it full brightness 
        # but change the size or show a brightness bar? 
        # Let's show the TRUE color (Mood Color) in center, and FINAL color (Dimmed) as border?
        # Simpler: Show Final Color.
        
        dr = int(r * final_brightness)
        dg = int(g * final_brightness)
        db = int(b * final_brightness)
        
        hex_color = f"#{dr:02x}{dg:02x}{db:02x}"
        self.canvas.configure(bg=hex_color)
        
        # Update text
        self.labels["status"].config(text=f"Frame: {state.loop_index:05d} | FPS Target: {self.fps}")
        self.labels["tempo"].config(
            text=f"BPM: {state.bpm:.1f} | Stability: {state.bpm_stability:.2f} " + 
            ("✅" if state.bpm_stability > 0.8 else "⚠️" if state.bpm_stability < 0.3 else "🔄")
        )
        self.labels["features"].config(
            text=f"Loudness: {state.brightness:.2f} | Raw RMS: {state.raw_rms:.4f} | Onset: {state.onset:.2f}"
        )
        self.labels["mood"].config(
            text=f"MOOD | Arousal: {state.arousal:.2f} | Valence: {state.valence:.2f}"
            + (" [WARM]" if state.valence > 0.6 else " [COOL]" if state.valence < 0.4 else " [NEUTRAL]")
        )
        
        mode_str = "MINIMAL" if state.minimal_mode else "NORMAL"
        if state.drop_frames > 0:
            mode_str = f"!!! DROP BOOST ({state.drop_frames}) !!!"
            self.labels["dynamics"].config(fg="#ff5555") # Red text for drop
        else:
            self.labels["dynamics"].config(fg="#cccccc")
            
        self.labels["dynamics"].config(text=f"Mode: {mode_str}")
        self.labels["rgb"].config(text=f"RGB: ({r}, {g}, {b}) | Final: {final_brightness:.2f}")

        # Update Tkinter
        self.root.update_idletasks()
        self.root.update()
