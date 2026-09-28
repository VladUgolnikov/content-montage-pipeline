#!/usr/bin/env python3
"""Мелкие медиа-задачи для Claude через мост.
  sheet OUT.jpg "FILE|t1,t2,t3" ["FILE|t..."]   — лист кадров (строка на файл, 360 px по ширине кадра)
  find URL REGEX                                — найти в HTML страницы строки по регулярке (для ссылок на сток)
  fetch URL OUT                                 — скачать файл (сток после «да» Влада; ссылку записать в _licenses.md)
  clip SRC OUT ss dur [vf]                      — вырезать кусок в h264 (для превью/подготовки вставок)
Пути OUT/SRC — абсолютные или от pipeline/."""
import os, sys, re, subprocess, urllib.request
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, PIPE)
from montage import ffbin
FF = ffbin()
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
P = lambda p: p if os.path.isabs(p) else os.path.join(PIPE, p)

def sheet(out, specs):
    import numpy as np, cv2
    rows = []
    for sp in specs:
        f, ts = sp.split("|"); row = []
        for t in ts.split(","):
            r = subprocess.run([FF, "-v", "error", "-ss", t, "-i", P(f), "-frames:v", "1", "-vf", "scale=360:-2",
                                "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
            img = cv2.imdecode(np.frombuffer(r, np.uint8), 1) if r else None
            if img is None: img = np.zeros((202, 360, 3), np.uint8)
            cv2.putText(img, f"{os.path.basename(f)[:14]} {t}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            row.append(img)
        h = max(i.shape[0] for i in row)
        row = [cv2.copyMakeBorder(i, 0, h - i.shape[0], 0, 4, cv2.BORDER_CONSTANT) for i in row]
        rows.append(cv2.hconcat(row))
    w = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 4, 0, w - r.shape[1], cv2.BORDER_CONSTANT) for r in rows]
    cv2.imwrite(P(out), cv2.vconcat(rows), [cv2.IMWRITE_JPEG_QUALITY, 85]); print("ok", P(out))

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "sheet":
        sheet(a[1], a[2:])
    elif a[0] == "find":
        html = get(a[1]).decode("utf8", "ignore")
        for m in sorted(set(re.findall(a[2], html)))[:200]:
            print(m)
    elif a[0] == "fetch":
        data = get(a[1]); os.makedirs(os.path.dirname(P(a[2])), exist_ok=True)
        open(P(a[2]), "wb").write(data); print("ok", len(data), "байт ->", P(a[2]))
    elif a[0] == "clip":
        vf = ["-vf", a[5]] if len(a) > 5 else []
        r = subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", a[3], "-i", P(a[1]), "-t", a[4]] + vf +
                           ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", P(a[2])],
                           capture_output=True, text=True)
        print(r.stderr[-1500:] or "ok")
