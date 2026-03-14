import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.audio.player_backend import TrackAnalyzer

def test_new_math():
    filepath = "C:/Users/xxx/Downloads/music-reactive-lighting/data/The_Sun_(Prod._Gesaffelstein).mp3"
    
    # We need to find the real audio file or we can just run the test from the existing CSVs 
    # WAIT, if I just load the track analyzer on it, it will overwrite the old log or make a new one.
    
    analyzer = TrackAnalyzer()
    print("Running newly compiled engine on The Sun...")
    analyzer.analyze_file("data/Kaycyy - The Sun.mp3") # Wait, what is the actual filename?
    
test_new_math()
