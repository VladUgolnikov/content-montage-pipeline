#!/usr/bin/env python3
"""Самопроверка моста MAOS: питон-пакеты, ffmpeg с субтитрами, модели, доступ к T7."""
import os, sys, json, subprocess, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.dirname(HERE)
res = {"time": datetime.datetime.now().isoformat(timespec="seconds"), "python": sys.version.split()[0]}
for m in ["onnx_asr", "onnxruntime", "cv2", "PIL", "numpy", "imageio_ffmpeg"]:
    try:
        __import__(m); res[m] = "ok"
    except Exception as e:
        res[m] = f"ОШИБКА: {e}"
try:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe(); res["ffmpeg"] = ff
    flt = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    res["ffmpeg_ass"] = "ok" if " ass " in flt else "НЕТ libass"
    enc = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    res["libx264"] = "ok" if "libx264" in enc else "нет"
    res["videotoolbox"] = [e for e in ("h264_videotoolbox", "hevc_videotoolbox", "prores_videotoolbox") if e in enc]
except Exception as e:
    res["ffmpeg"] = f"ОШИБКА: {e}"
res["models"] = {p: os.path.exists(os.path.join(PIPE, "models", p)) for p in ["gigaam", "yunet.onnx"]}
t7 = "/Volumes/T7 Shield"
res["t7"] = sorted(f for f in os.listdir(t7) if f.lower().endswith(".mov") and not f.startswith("._")) if os.path.isdir(t7) else "не подключён"
nb = os.path.expanduser("~/Library/Application Support/MAOS-bridge/node/bin/node")
res["node"] = subprocess.run([nb, "-v"], capture_output=True, text=True).stdout.strip() if os.path.exists(nb) else "нет"
rm = os.path.expanduser("~/Library/Application Support/MAOS-bridge/remotion/node_modules/remotion/package.json")
res["remotion"] = json.load(open(rm)).get("version") if os.path.exists(rm) else "нет"
out = os.path.join(HERE, "selftest.json")
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
for k, v in res.items():
    print(f"  {k}: {v}")
