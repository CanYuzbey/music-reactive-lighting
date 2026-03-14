import os
import glob
import csv
import numpy as np

def analyze_logs_and_optimize():
    logs_dir = "c:/Users/xxx/Downloads/music-reactive-lighting/logs/history/"
    files = glob.glob(os.path.join(logs_dir, "*.csv"))
    
    if not files:
        print("No logs found to train on.")
        return

    all_valences = []
    all_arousals = []
    all_dominances = []
    
    for f in files:
        with open(f, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                all_valences.append(float(row['Valence']))
                all_arousals.append(float(row['Arousal']))
                all_dominances.append(float(row['Dominance']))
                
    if not all_valences:
        return
        
    val_arr = np.array(all_valences)
    aro_arr = np.array(all_arousals)
    dom_arr = np.array(all_dominances)
    
    print("=== SYNAPTIC ANALYSIS OF PAST SONGS ===")
    print(f"Total Frames Analyzed: {len(val_arr)}")
    
    # 1. Evaluate Dynamic Range of Valence
    print("\n--- VALENCE (COLOR) DYNAMICS ---")
    val_mean = np.mean(val_arr)
    val_std = np.std(val_arr)
    val_min, val_max = np.min(val_arr), np.max(val_arr)
    print(f"Mean: {val_mean:.3f} | StdDev: {val_std:.3f}")
    print(f"Range: [{val_min:.3f} to {val_max:.3f}]")
    
    if val_std < 0.2:
        print("💡 INSIGHT: Valence is too clumped up. The colors are likely staying in the middle (Purple/Pink/Orange) and rarely hitting deep Blue or bright Yellow/White.")
        print("👉 ACTION: We need to increase the multiplier for absolute and adaptive valence.")
    
    # 2. Evaluate Dynamic Range of Arousal
    print("\n--- AROUSAL (ENERGY/BRIGHTNESS) DYNAMICS ---")
    aro_mean = np.mean(aro_arr)
    aro_std = np.std(aro_arr)
    aro_min, aro_max = np.min(aro_arr), np.max(aro_arr)
    print(f"Mean: {aro_mean:.3f} | StdDev: {aro_std:.3f}")
    print(f"Range: [{aro_min:.3f} to {aro_max:.3f}]")
    
    if aro_std < 0.2:
        print("💡 INSIGHT: Arousal lacks dynamic variance. The lights aren't dimming enough during quiet parts or popping enough during loud parts.")
    
    # 3. Evaluate Dominance Center
    print("\n--- SPECTRAL DOMINANCE CENTER ---")
    dom_mean = np.mean(dom_arr)
    print(f"Observed Mean Dominance (Mid+High vs Total): {dom_mean:.3f} (Theoretical expected was 0.66)")
    if abs(dom_mean - 0.66) > 0.05:
        print(f"👉 ACTION: The absolute valence anchor should be shifted from 0.66 to {dom_mean:.2f} for these tracks.")
        
    # Proposed new parameters:
    suggested_anchor = dom_mean
    suggested_multiplier = 1.5 if val_std > 0.2 else (0.2 / max(0.01, val_std)) * 1.5
    
    print("\n=== SUGGESTED OPTIMIZATIONS ===")
    print(f"New Valence Anchor: {suggested_anchor:.3f}")
    print(f"New Valence Multiplier (Spread): {suggested_multiplier:.3f}")

if __name__ == "__main__":
    analyze_logs_and_optimize()
