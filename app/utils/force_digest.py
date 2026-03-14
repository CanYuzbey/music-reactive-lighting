import os
import glob
from app.audio.memory_bank import SongMemoryBank

def train_on_existing():
    logs_dir = "c:/Users/xxx/Downloads/music-reactive-lighting/logs/history/"
    files = glob.glob(os.path.join(logs_dir, "*.csv"))
    
    if not files:
        print("No logs found to train on.")
        return
        
    memory = SongMemoryBank(logs_dir)
    print("Forcing Neural Memory Bank to digest existing logs...")
    for f in files:
        memory.digest_log(f)
        
    print("\nTraining Complete. Final Global Model:")
    import json
    print(json.dumps(memory.model, indent=4))

if __name__ == "__main__":
    train_on_existing()
