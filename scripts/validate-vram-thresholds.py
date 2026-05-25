#!/usr/bin/env python3
# Copyright (c) 2026 Andrzej Dobosz. All rights reserved.
# Priority Date: 2026-05-18 | Patent Pending: UPRP P.455821
# License: MIT -- see LICENSE file
"""Test VRAM thresholds on current GPU. Run on each machine."""
import subprocess, json, time, statistics

def get_vram_mb():
    r = subprocess.run(['nvidia-smi','--query-gpu=memory.used',
        '--format=csv,noheader,nounits'], capture_output=True, text=True)
    return float(r.stdout.strip())

def get_total_vram():
    r = subprocess.run(['nvidia-smi','--query-gpu=memory.total',
        '--format=csv,noheader,nounits'], capture_output=True, text=True)
    return float(r.stdout.strip())

models = ["phi4-mini","llama3.2:3b","deepseek-r1:7b","qwen2.5:3b"]
results = []
T = get_total_vram() / 1024  # GB
for model in models:
    B = get_vram_mb() / 1024
    lower = B + (T * 0.55)
    upper = B + (T * 0.75)
    measures = []
    for run in range(7):  # 2 warmup + 5 measurement
        subprocess.run(['ollama','run',model,'hello'],
            capture_output=True, timeout=60)
        time.sleep(3)
        vram = get_vram_mb() / 1024
        if run >= 2: measures.append(vram)
    avg = statistics.mean(measures)
    cv = (statistics.stdev(measures)/avg)*100 if len(measures)>1 else 0
    tier = 'GREEN' if avg<=lower else ('YELLOW' if avg<=upper else 'RED')
    results.append({"model":model,"T_GB":T,"B_GB":round(B,2),
        "avg_vram":round(avg,2),"cv_pct":round(cv,1),
        "lower":round(lower,2),"upper":round(upper,2),"tier":tier})
    subprocess.run(['ollama','stop',model], capture_output=True)
    time.sleep(5)

with open(f'VRAM-VALIDATION-{T:.0f}GB.json','w') as f:
    json.dump(results, f, indent=2)
print(json.dumps(results, indent=2))
