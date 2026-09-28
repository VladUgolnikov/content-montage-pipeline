#!/usr/bin/env python3
"""Проверка и исправление синхрона после Remotion: меряет сдвиг звука финала относительно базы
(взаимная корреляция в 4 точках) и, если он больше 10 мс, сдвигает звук без пережатия видео.
  python3 remotion/sync_fix.py <base.mp4> <final.mp4>
"""
import os, sys, subprocess, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
from montage import ffbin, duration

def pcm(FF, p, ss, d):
    r = subprocess.run([FF, "-v", "error", "-ss", str(ss), "-i", p, "-t", str(d), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(r, np.float32)

def lag_ms(FF, base, fin, dur):
    res = []
    for ss in [dur * x for x in (0.1, 0.35, 0.6, 0.85)]:
        b, f = pcm(FF, base, ss, 3), pcm(FF, fin, ss, 3)
        m = min(len(b), len(f)); b, f = b[:m], f[:m]
        best = max(range(-1600, 1601, 4), key=lambda k: float(np.dot(b[max(0, k):m + min(0, k)], f[max(0, -k):m - max(0, k)])))
        res.append(-best / 16.0)
    return res

def main(base, fin):
    base = os.path.join(HERE, base) if not base.startswith("/") else base
    fin = os.path.join(HERE, fin) if not fin.startswith("/") else fin
    FF = ffbin(); dur = duration(FF, fin)
    lags = lag_ms(FF, base, fin, dur); lag = float(np.median(lags))
    print(f"сдвиг звука (финал позже базы), мс: {lags} -> медиана {lag:.1f}", flush=True)
    if abs(lag) <= 10:
        print("синхрон в норме"); return
    tmp = fin + ".sync.mp4"
    subprocess.run([FF, "-y", "-v", "error", "-i", fin, "-itsoffset", f"{-lag/1000:.4f}", "-i", fin,
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, fin)
    after = lag_ms(FF, base, fin, dur)
    print(f"исправлено: сдвиг после {after} мс", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
