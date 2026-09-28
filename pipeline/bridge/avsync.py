#!/usr/bin/env python3
"""Синхрон звук/губы — подготовка на Маке (анализ делает Claude в облаке по лёгкой копии).
  export SRC OUT.mp4 [ss dur]  — лёгкая копия 360p (таймстемпы кадров сохраняются как в исходнике) + звук 16 кГц моно.
Таймлайн копии = таймлайн ffmpeg для исходника (тот же, по которому режет montage.py), поэтому
измеренный сдвиг напрямую переносится в plan["av_offset"]."""
import os, sys, subprocess, json
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, PIPE)
from montage import ffbin
FF = ffbin()

def export(src, out, ss=None, dur=None):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error", "-hwaccel", "videotoolbox"]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    cmd += ["-i", src]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=360:-2", "-fps_mode", "passthrough",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-g", "60",
            "-ac", "1", "-ar", "16000", "-c:a", "aac", "-b:a", "64k"] + (["-movflags", "+faststart"] if out.endswith(".mp4") else []) + [out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stderr[-2000:] if r.returncode else "ok", flush=True)
    pr = subprocess.run([FF, "-hide_banner", "-i", out], capture_output=True, text=True).stderr
    print("\n".join(l for l in pr.splitlines() if "Duration" in l or "Stream" in l))
    print("размер, МБ:", round(os.path.getsize(out) / 1e6, 1))

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "ls":   # список исходников на диске: имя, размер, дата
        import time
        for root in a[1:]:
            for f in sorted(os.listdir(root)):
                p = os.path.join(root, f)
                if f.startswith(".") or not os.path.isfile(p): continue
                print(f"{f}\t{os.path.getsize(p)/1e9:.2f} ГБ\t{time.strftime('%d.%m %H:%M', time.localtime(os.path.getmtime(p)))}")
    elif a[0] == "export":
        export(a[1], os.path.join(PIPE, a[2]) if not os.path.isabs(a[2]) else a[2],
               float(a[3]) if len(a) > 3 else None, float(a[4]) if len(a) > 4 else None)
