import os
import csv
import json
import numpy as np

class SongMemoryBank:
    """
    Acts as a persistent 'Neural Memory' for the lighting system.
    Before a song log is deleted due to storage limits, this bank reads it,
    extracts key mathematical distributions, and updates a global 'model'.
    This allows the engine to adapt to the user's specific music taste over time.
    """
    def __init__(self, memory_dir: str):
        self.memory_dir = memory_dir
        self.model_path = os.path.join(memory_dir, "global_model.json")
        self.model = self._load_model()
        
    def _load_model(self) -> dict:
        default_model = {
            "total_songs_digested": 0,
            "global_avg_bass_exertion": 1.0,
            "global_avg_mid_exertion": 1.0,
            "global_avg_high_exertion": 1.0,
            "typical_arousal": 0.5,
            "typical_valence": 0.5,
            "learning_rate": 0.05 # How much each deleted song shifts the global model
        }
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'r') as f:
                    return json.load(f)
            except:
                return default_model
        return default_model
        
    def _save_model(self):
        try:
            with open(self.model_path, 'w') as f:
                json.dump(self.model, f, indent=4)
        except Exception as e:
            print(f"MemoryBank error saving model: {e}")

    def digest_log(self, csv_filepath: str):
        """
        Extracts insights from a song's log before it is deleted.
        """
        print(f"🧠 Memory Bank: Digesting {os.path.basename(csv_filepath)} before deletion...")
        
        try:
            bass_exertions = []
            mid_exertions = []
            high_exertions = []
            arousals = []
            valences = []
            
            with open(csv_filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bass_exertions.append(float(row.get('Exert_L', 1.0)))
                    mid_exertions.append(float(row.get('Exert_M', 1.0)))
                    high_exertions.append(float(row.get('Exert_H', 1.0)))
                    arousals.append(float(row.get('Arousal', 0.5)))
                    valences.append(float(row.get('Valence', 0.5)))
                    
            if not bass_exertions: return
            
            # Compute song averages
            # We ignore silent frames where exertion is 0.0 to find true song energy
            song_avg_bass = np.mean([x for x in bass_exertions if x > 0.01]) if max(bass_exertions) > 0.01 else 1.0
            song_avg_mid = np.mean([x for x in mid_exertions if x > 0.01]) if max(mid_exertions) > 0.01 else 1.0
            song_avg_high = np.mean([x for x in high_exertions if x > 0.01]) if max(high_exertions) > 0.01 else 1.0
            song_avg_arousal = np.mean(arousals)
            song_avg_valence = np.mean(valences)
            
            # Update global model using momentum
            lr = self.model["learning_rate"]
            
            # Smoothly transition the global expectations
            self.model["global_avg_bass_exertion"] += (song_avg_bass - self.model["global_avg_bass_exertion"]) * lr
            self.model["global_avg_mid_exertion"] += (song_avg_mid - self.model["global_avg_mid_exertion"]) * lr
            self.model["global_avg_high_exertion"] += (song_avg_high - self.model["global_avg_high_exertion"]) * lr
            
            self.model["typical_arousal"] += (song_avg_arousal - self.model["typical_arousal"]) * lr
            self.model["typical_valence"] += (song_avg_valence - self.model["typical_valence"]) * lr
            
            self.model["total_songs_digested"] += 1
            
            self._save_model()
            print(f"🧠 Memory Bank: Digestion complete. Updating global baseline expectations.")
            
        except Exception as e:
            print(f"MemoryBank failed to digest log: {e}")
