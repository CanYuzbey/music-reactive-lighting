import csv
import glob
import os

logs_dir = "c:/Users/xxx/Downloads/music-reactive-lighting/logs/history/"
files = glob.glob(os.path.join(logs_dir, "*.csv"))

report = "Diagnostic Analysis of User's Tri-Band Logs\n"
report += "="*60 + "\n"

if not files:
    report += "No logs found.\n"
else:
    for f in files[-3:]: # Get the 3 most recent logs
        song_name = os.path.basename(f).replace(".csv", "").replace("log_", "")
        
        exert_l_list = []
        exert_m_list = []
        exert_h_list = []
        valence_list = []
        last_time = "0.0"
        
        with open(f, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                last_time = row['Time_sec']
                exert_l_list.append(float(row['Exert_L']))
                exert_m_list.append(float(row['Exert_M']))
def analyze_logs():
    logs_dir = "c:/Users/xxx/Downloads/music-reactive-lighting/logs/history/"
    files = glob.glob(os.path.join(logs_dir, "*.csv"))

    report = "Diagnostic Analysis of User's Tri-Band Logs\n"
    report += "="*60 + "\n"

    if not files:
        report += "No logs found.\n"
    else:
        for f in files[-3:]: # Get the 3 most recent logs
            song_name = os.path.basename(f).replace(".csv", "").replace("log_", "")
            
            exert_l_list, exert_m_list, exert_h_list, valence_list = [], [], [], []
            last_time = "0.0"
            
            with open(f, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    last_time = row['Time_sec']
                    exert_l_list.append(float(row['Exert_L']))
                    exert_m_list.append(float(row['Exert_M']))
                    exert_h_list.append(float(row['Exert_H']))
                    valence_list.append(float(row['Valence']))
                    
            if not exert_l_list: continue
            
            report += f"Song: {song_name}\n"
            report += f"Total length: {last_time} seconds\n"
            
            avg_l, avg_m, avg_h = sum(exert_l_list)/len(exert_l_list), sum(exert_m_list)/len(exert_m_list), sum(exert_h_list)/len(exert_h_list)
            spike_l = sum(1 for x in exert_l_list if x > 1.5)
            spike_m = sum(1 for x in exert_m_list if x > 1.5)
            spike_h = sum(1 for x in exert_h_list if x > 1.5)
            avg_v = sum(valence_list)/len(valence_list)
            
            report += f"Average Exertion -> Bass: {avg_l:.2f} | Mid: {avg_m:.2f} | High: {avg_h:.2f}\n"
            report += f"Spike Frames (>1.5) -> Bass: {spike_l} | Mid: {spike_m} | High: {spike_h} (Total Frames: {len(exert_l_list)})\n"
            report += f"Average Valence (Mood): {avg_v:.2f}\n"
            report += "-" * 60 + "\n"
            
    # Safe print for Windows console characters
    print(report.encode('cp1254', errors='replace').decode('cp1254'))
