#!/usr/bin/env python3
"""Проверка синхрона в исходниках: для каждого .mov/.mp4 в папке — fps, старт видео/звука, точная длина
видео (кадры) и звука (сэмплы), дрейф. python3 bridge/avcheck.py "/Volumes/T7 Shield" """
import os, sys, re, subprocess
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, PIPE)
from montage import ffbin
FF = ffbin(); root = sys.argv[1]
files = sorted(f for f in os.listdir(root) if f.lower().endswith((".mov", ".mp4")) and not f.startswith("."))
for f in files:
    p = os.path.join(root, f)
    info = subprocess.run([FF, "-hide_banner", "-i", p], capture_output=True, text=True).stderr
    fps = re.search(r"([\d.]+) fps", info); ar = re.search(r"Audio: (\w+).*?(\d+) Hz", info)
    def first_pts(sel):
        r = subprocess.run([FF, "-v", "error", "-i", p, "-map", sel, "-c", "copy", "-frames", "1", "-f", "framecrc", "-"], capture_output=True, text=True).stdout
        tb = re.search(r"#tb \d+: (\d+)/(\d+)", r); l = [x for x in r.splitlines() if not x.startswith("#")]
        return int(l[0].split(",")[1]) * int(tb.group(1)) / int(tb.group(2)) if l and tb else None
    v0, a0 = first_pts("0:v:0"), first_pts("0:a:0")
    r = subprocess.run([FF, "-hide_banner", "-i", p, "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-af", "astats=metadata=0:reset=0",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    fr = re.findall(r"frame=\s*(\d+)", r); ns = re.search(r"Number of samples: (\d+)", r)
    f_ = float(fps.group(1)) if fps else 30.0; sr = int(ar.group(2)) if ar else 48000
    vd = int(fr[-1]) / f_ if fr else None; ad = int(ns.group(1)) / sr if ns else None
    print(f"{f}: fps {fps.group(1) if fps else '?'}, звук {ar.group(1) if ar else '?'} {sr} Гц | старт видео {v0}, звук {a0} с | "
          f"длина видео {vd} с, звук {ad} с, разница {((ad or 0)-(vd or 0))*1000:+.0f} мс", flush=True)
