#!/usr/bin/env python3
"""Оценка рассинхрона звук/губы в исходнике: движение в области рта (кадр к кадру) против огибающей голоса.
  python3 bridge/lipsync.py SRC start dur [start dur ...]
Положительный результат = звук ОТСТАЁТ от губ на N мс."""
import os, sys, subprocess
import numpy as np, cv2
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, PIPE)
from montage import ffbin
FF = ffbin(); src = sys.argv[1]; spans = list(zip(map(float, sys.argv[2::2]), map(float, sys.argv[3::2])))
model = os.path.join(PIPE, "models", "yunet.onnx"); FPS = 30.0; W = 540

def video_motion(ss, d):
    p = subprocess.run([FF, "-v", "error", "-hwaccel", "videotoolbox", "-ss", str(ss), "-i", src, "-t", str(d),
                        "-vf", f"fps={FPS},scale={W}:-2", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    H = int(round(W * 3840 / 2160 / 2) * 2)   # вертикальный кадр после поворота
    n = len(p) // (W * H * 3)
    fr = np.frombuffer(p[:n * W * H * 3], np.uint8).reshape(n, H, W, 3)
    det = cv2.FaceDetectorYN.create(model, "", (W, H), score_threshold=0.6); det.setInputSize((W, H))
    box = None; prev = None; m = []
    for i in range(n):
        if i % 15 == 0:
            _, f = det.detect(fr[i])
            if f is not None and len(f):
                f = max(f, key=lambda z: z[2] * z[3]); nx, ny = f[8], f[9]; rx, ry, lx, ly = f[10], f[11], f[12], f[13]
                mw = lx - rx; my = (ry + ly) / 2
                box = (int(rx - 0.35 * mw), int(ny + 0.3 * (my - ny)), int(lx + 0.35 * mw), int(my + 0.9 * (my - ny)))
        if box is None:
            m.append(0.0); continue
        x0, y0, x1, y1 = [max(0, v) for v in box]
        g = cv2.cvtColor(fr[i][y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype(np.float32)
        m.append(float(np.abs(g - prev).mean()) if prev is not None and prev.shape == g.shape else 0.0); prev = g
    return np.array(m)

def audio_env(ss, d, sr=16000):
    r = subprocess.run([FF, "-v", "error", "-ss", str(ss), "-i", src, "-t", str(d), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(r, np.float32); hop = int(sr / FPS); n = len(x) // hop
    e = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-10)
    return np.abs(np.diff(20 * np.log10(e), prepend=20 * np.log10(e[0])))   # изменение громкости ~ открывание рта

def z(v):
    v = v - np.convolve(v, np.ones(15) / 15, "same"); return (v - v.mean()) / (v.std() + 1e-9)

allc = None
for ss, d in spans:
    mv, au = video_motion(ss, d), audio_env(ss, d); n = min(len(mv), len(au)); mv, au = z(mv[:n]), z(au[:n])
    lags = np.arange(-24, 25)
    def cc(k):
        return float(np.dot(mv[0:n - k], au[k:n])) / n if k >= 0 else float(np.dot(mv[-k:n], au[0:n + k])) / n
    c = np.array([cc(int(k)) for k in lags])
    k = int(lags[c.argmax()])
    if 0 < c.argmax() < len(c) - 1:
        y0, y1, y2 = c[c.argmax() - 1], c[c.argmax()], c[c.argmax() + 1]; k = k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    print(f"участок {ss:.0f}–{ss+d:.0f} с: звук отстаёт на {k*1000/FPS:+.0f} мс (пик корреляции {c.max():.2f})", flush=True)
    allc = c if allc is None else allc + c
k = int(np.arange(-24, 25)[allc.argmax()])
print(f"ИТОГО: звук отстаёт от губ примерно на {k*1000/FPS:+.0f} мс", flush=True)
