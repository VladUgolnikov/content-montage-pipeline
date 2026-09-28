#!/usr/bin/env python3
"""Диагностика звука исходника: параметры потоков, стартовые метки аудио/видео, спектр сырого голоса
и того же места после цепочки шумодава из config.json.
  python3 bridge/diag.py "/Volumes/T7 Shield/X.mov" 250 30
"""
import os, sys, re, json, subprocess
import numpy as np
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, PIPE)
from montage import ffbin
FF = ffbin(); src = sys.argv[1]; ss = float(sys.argv[2]); d = float(sys.argv[3])
info = subprocess.run([FF, "-hide_banner", "-i", src], capture_output=True, text=True).stderr
print("\n".join(l.strip() for l in info.splitlines() if "Stream #" in l or "Duration" in l or "handler_name" in l or "encoder" in l.lower())[:3000])
for sel in ("0:v:0", "0:a:0"):
    r = subprocess.run([FF, "-v", "error", "-i", src, "-map", sel, "-c", "copy", "-frames", "3", "-f", "framecrc", "-"], capture_output=True, text=True).stdout
    print(sel, [l for l in r.splitlines() if not l.startswith("#")][:3])
def spec(extra):
    r = subprocess.run([FF, "-v", "error", "-ss", str(ss), "-i", src, "-t", str(d), "-vn"] + extra + ["-ac", "1", "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(r, np.float32); n = 4096
    fr = x[:len(x) // n * n].reshape(-1, n) * np.hanning(n)
    S = (np.abs(np.fft.rfft(fr, axis=1)) ** 2).mean(0); f = np.fft.rfftfreq(n, 1 / 48000); tot = S[f > 80].sum()
    bands = {f"{lo}-{hi}": round(float(10 * np.log10(S[(f >= lo) & (f < hi)].sum() / tot)), 1) for lo, hi in
             [(80, 300), (300, 1000), (1000, 3000), (3000, 5000), (5000, 8000), (8000, 12000), (12000, 20000)]}
    db = 10 * np.log10(S / S.max() + 1e-20); top = float(f[np.where(db > -60)[0].max()])
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", subprocess.run([FF, "-hide_banner", "-ss", str(ss), "-i", src, "-t", str(d), "-vn"] + extra + ["-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr)
    return bands, top, lufs[-1] if lufs else None
cfg = json.load(open(os.path.join(PIPE, "config.json")))
print("сырой:", spec([]))
print("после шумодава:", spec(["-af", cfg["voice"]["chain"]]))
if len(sys.argv) > 4:   # свои цепочки: имя=цепочка
    for arg in sys.argv[4:]:
        nm, ch = arg.split("=", 1)
        print(f"{nm}:", spec(["-af", ch]))
else:
    print("мягкий вариант:", spec(["-af", "highpass=f=80,afftdn=nr=8:nf=-50,loudnorm=I=-14:TP=-1.5:LRA=11"]))
