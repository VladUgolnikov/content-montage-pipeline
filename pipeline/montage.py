#!/usr/bin/env python3
"""MAOS montage v3: сырой talking-head (оригинал на T7 + прокси камеры) -> готовый Reels 1080x1920.

Графика и субтитры рисуются в Remotion (дизайн-код «Визуальный язык MAOS»), здесь — рез, кадр, звук, сборка.

Запуск (через мост или руками):
  python3 montage.py --src SRC --name NAME --transcribe-only            -> NAME_words.json + NAME_transcript.txt
  python3 montage.py --src SRC --name NAME --plan plans/X.json [--words W] — режим берётся из plan["mode"]:
    "probe"     — параметры исходника и доступные аппаратные кодеки
    "review"    — plan["takes"]=[{"id","lo","hi"}]: листы лиц по каждому дублю (взгляд) + флаги звука
    "base"      — plan["edl"]: точный по кадрам рез, кадр, B-roll, цвет, звук, ускорение -> NAME_base.mp4
                  + NAME_timeline.json (слова и события графики в финальном времени) + QA синхрона и склеек
    "composite" — NAME_base.mp4 + NAME_overlay.webm (Remotion, прозрачный) + звуки -> NAME_final.mp4

План (base): edl [[lo,hi],...] — куски исходника в нужном порядке (границы уточняются по звуку),
  replace {слово: замена}, accents [префиксы слов для красного бокса], broll [{at_word, until_word, file, start}],
  graphics [{type, at_word, until_word, ...}] — события для Remotion (якорь: "префикс", "=точно", "слово#2").
"""
import os, sys, json, re, subprocess, unicodedata, argparse, shutil, time, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LOG = []

def log(msg):
    print(msg, flush=True); LOG.append(msg)

def nfc(s):
    return unicodedata.normalize("NFC", s)

def resolve(base, rel):
    p = base
    for part in rel.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            p = os.path.dirname(p); continue
        cand = os.path.join(p, part)
        if os.path.exists(cand):
            p = cand; continue
        hit = [e for e in os.listdir(p) if nfc(e) == nfc(part)]
        if not hit:
            raise FileNotFoundError(os.path.join(p, part))
        p = os.path.join(p, hit[0])
    return p

def ffbin():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-4000:])
        hint = " (процесс убит — скорее всего не хватило памяти)" if r.returncode < 0 else ""
        raise SystemExit(f"ffmpeg failed, код {r.returncode}{hint}")
    return r

def duration(FF, path):
    r = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

def grab(FF, src, t, out):
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", out])

# ---------- распознавание (кусками по паузам — длинные записи) ----------
def asr_long(FF, proxy, work, cfg, max_chunk=24.0):
    wav = os.path.join(work, "asr.wav")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", proxy, "-vn", "-ac", "1", "-ar", "16000", wav])
    total = duration(FF, wav)
    r = subprocess.run([FF, "-hide_banner", "-i", wav, "-af", "silencedetect=n=-35dB:d=0.3", "-f", "null", "-"],
                       capture_output=True, text=True)
    ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    mids = [(a + b) / 2 for a, b in zip(ss, se)]
    # режем по серединам пауз, куски 8–24 с
    cuts = [0.0]
    while total - cuts[-1] > max_chunk:
        cand = [m for m in mids if cuts[-1] + 8.0 <= m <= cuts[-1] + max_chunk]
        cuts.append(cand[-1] if cand else cuts[-1] + max_chunk)
    cuts.append(total)
    import onnx_asr
    from transcribe import words_from
    a = cfg["asr"]
    model = onnx_asr.load_model(a["model"], os.path.join(HERE, a["path"]), quantization=a.get("quantization"))
    words = []
    for i in range(len(cuts) - 1):
        s0, s1 = cuts[i], cuts[i + 1]
        if s1 - s0 < 0.3:
            continue
        cw = os.path.join(work, f"chunk_{i:03d}.wav")
        run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{s0:.3f}", "-t", f"{s1-s0:.3f}", "-i", wav, cw])
        res = model.with_timestamps().recognize(cw)
        for w in words_from(res.tokens, res.timestamps):
            w["start"] = round(w["start"] + s0, 3); w["end"] = round(w["end"] + s0, 3)
            words.append(w)
    log(f"распознано кусками: {len(cuts)-1} кусков, {len(words)} слов, {total:.0f} с аудио")
    return words

def write_transcript(words, path, gap=0.8):
    lines = []; buf = []; t0 = None
    for i, w in enumerate(words):
        if t0 is None:
            t0 = w["start"]
        buf.append(w["word"])
        g = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 99
        if g > gap:
            m, s = divmod(t0, 60)
            lines.append(f"[{int(m):02d}:{s:05.2f} – {w['end']:.2f}] " + " ".join(buf))
            buf = []; t0 = None
    open(path, "w").write("\n".join(lines) + "\n")

# ---------- цифры и замены в субтитрах ----------
UNITS = {"ноль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6,
         "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
         "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19}
TENS = {"двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
        "восемьдесят": 80, "девяносто": 90}
HUND = {"сто": 100, "двести": 200, "триста": 300, "четыреста": 400, "пятьсот": 500, "шестьсот": 600,
        "семьсот": 700, "восемьсот": 800, "девятьсот": 900}

def normalize(words, replace):
    rep = {k.lower(): v for k, v in (replace or {}).items()}
    out = []; i = 0
    while i < len(words):
        lw = words[i]["word"].lower()
        if lw in HUND or lw in TENS or lw in UNITS:
            j = i; val = 0; used = []
            if j < len(words) and words[j]["word"].lower() in HUND:
                val += HUND[words[j]["word"].lower()]; used.append(j); j += 1
            if j < len(words) and words[j]["word"].lower() in TENS:
                val += TENS[words[j]["word"].lower()]; used.append(j); j += 1
            if j < len(words) and words[j]["word"].lower() in UNITS and (not used or UNITS[words[j]["word"].lower()] < 10):
                val += UNITS[words[j]["word"].lower()]; used.append(j); j += 1
            single_one = len(used) == 1 and val == 1
            if used and not single_one:
                txt = str(val)
                if j < len(words) and words[j]["word"].lower().startswith("процент"):
                    txt += "%"; used.append(j); j += 1
                m = {"word": txt, "orig": " ".join(words[k]["word"].lower() for k in used),
                     "start": words[used[0]]["start"], "end": words[used[-1]]["end"]}
                if "ns" in words[used[0]]:
                    m["ns"] = words[used[0]]["ns"]; m["ne"] = words[used[-1]]["ne"]
                out.append(m)
                i = j; continue
        w = dict(words[i]); w["orig"] = lw
        if lw in rep:
            w["word"] = rep[lw]
        out.append(w); i += 1
    return out

# ---------- служебные фразы ----------
NUMW = set(UNITS) | {"первый", "второй", "третий"}

def drop_service(words, phrases):
    low = [w["word"].lower() for w in words]
    keep = [True] * len(words); removed = []; i = 0
    while i < len(words):
        hit = False
        for ph in sorted(phrases, key=len, reverse=True):
            n = len(ph)
            if i + n <= len(words) and all(
                (p == "#" and (low[i + k] in NUMW or low[i + k].isdigit())) or low[i + k] == p
                for k, p in enumerate(ph)):
                for k in range(n):
                    keep[i + k] = False
                removed.append(" ".join(low[i:i + n])); i += n; hit = True; break
        if not hit:
            i += 1
    return [w for w, k in zip(words, keep) if k], removed

# ---------- рез ----------
def cut_range(words, lo, hi, pb, pa, gap):
    seg = []
    for w in words:
        a, b = max(lo, w["start"] - pb), min(hi, w["end"] + pa)
        if seg and a - seg[-1][1] < gap:
            seg[-1][1] = max(seg[-1][1], b)
        else:
            seg.append([a, b])
    return seg

# ---------- лицо и кадр ----------
def face_at(FF, proxy, t, work, W0, H0, model):
    import cv2
    fp = os.path.join(work, f"face_{t:.2f}.png")
    grab(FF, proxy, t, fp)
    img = cv2.imread(fp); h, w = img.shape[:2]
    sw, sh = 540, int(540 * h / w)
    small = cv2.resize(img, (sw, sh))
    d = cv2.FaceDetectorYN.create(model, "", (sw, sh), score_threshold=0.6)
    d.setInputSize((sw, sh))
    _, faces = d.detect(small)
    if faces is None or len(faces) == 0:
        return None
    f = max(faces, key=lambda f: f[2] * f[3])
    k = W0 / sw
    return ((f[0] + f[2] / 2) * k, (f[1] + f[3] / 2) * k, f[2] * k)

def crop_box(face, W0, H0, fr, zoom):
    target = fr.get("face_frac", 0.30)
    if face:
        fx, fy, fw = face
        ch = fw / target * 16 / 9
    else:
        fx, fy, ch = W0 / 2, H0 * 0.45, H0
    ch = max(min(ch, H0), fr.get("min_crop_h", 1400))
    ch = int(round(ch / zoom / 2) * 2); cw = int(round(ch * 9 / 16 / 2) * 2)
    if cw > W0:
        cw = W0 - W0 % 2; ch = int(round(cw * 16 / 9 / 2) * 2)
    cx = int(min(max(fx - cw / 2, 0), W0 - cw)); cy = int(min(max(fy - fr["face_y_frac"] * ch, 0), H0 - ch))
    return cw, ch, cx, cy

# ---------- B-roll ----------
def pick_broll(broll_root, tags, prefer, used):
    best = None
    for shoot in sorted(os.listdir(broll_root)):
        cp = os.path.join(broll_root, shoot, "_footage_catalog.json")
        if not os.path.exists(cp):
            continue
        for fname, info in json.load(open(cp)).items():
            if f"{nfc(shoot)}/{fname}" in used:
                continue
            for sg in info.get("segments", []):
                score = sum(1 for t in tags if t in sg.get("tags", []) or t in sg.get("scene", "").lower())
                if score and (best is None or score > best[0]):
                    best = (score, shoot, fname, sg)
    if not best:
        return None
    _, shoot, fname, sg = best
    return {"file": f"{nfc(shoot)}/{fname}", "path": resolve(os.path.join(broll_root, shoot), fname),
            "start": sg["start"] + min(3.0, (sg["end"] - sg["start"]) / 3), "scene": sg.get("scene", "")}

# ---------- звуки (заглушки, пока банк пуст) ----------
def sfx_files(FF, work):
    bank = os.path.join(HERE, "assets", "sfx")
    have = sorted(f for f in os.listdir(bank) if f.lower().endswith((".wav", ".mp3"))) if os.path.isdir(bank) else []
    pop = os.path.join(work, "pop.wav"); whoosh = os.path.join(work, "whoosh.wav")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         "aevalsrc='0.8*sin(2*PI*(1700-7000*t)*t)*exp(-38*t)':s=48000:d=0.14", "-ac", "2", pop])
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         "anoisesrc=d=0.42:c=pink:r=48000:a=0.7", "-af",
         "bandpass=f=1400:width_type=h:w=1800,afade=t=in:d=0.2,afade=t=out:st=0.2:d=0.22", "-ac", "2", whoosh])
    return pop, whoosh, bool(have)


# ================= v3: проба, звук, точный рез =================
FPS_MAP = {"29.97": 30000 / 1001, "59.94": 60000 / 1001, "23.98": 24000 / 1001, "23.976": 24000 / 1001}

def probe(FF, src):
    r = subprocess.run([FF, "-hide_banner", "-i", src], capture_output=True, text=True).stderr
    m = re.search(r"Video: ([\w]+)[^\n]*?, (\d{3,5})x(\d{3,5})[^\n]*?([\d.]+) fps", r)
    fps_s = m.group(4) if m else "30"
    fps = FPS_MAP.get(fps_s, float(fps_s))
    enc = subprocess.run([FF, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    dec = subprocess.run([FF, "-hide_banner", "-decoders"], capture_output=True, text=True).stdout
    hwa = subprocess.run([FF, "-hide_banner", "-hwaccels"], capture_output=True, text=True).stdout
    hw = {"h264_vt": "h264_videotoolbox" in enc, "hevc_vt": "hevc_videotoolbox" in enc,
          "vt_decode": "videotoolbox" in hwa, "vp9_alpha_dec": "libvpx-vp9" in dec, "vp9_enc": "libvpx-vp9" in enc}
    info = {"codec": m.group(1) if m else "?", "size": f"{m.group(2)}x{m.group(3)}" if m else "?", "fps_str": fps_s, "fps": fps}
    return info, hw

def venc(hw, rate, crf):
    if hw.get("h264_vt"):
        return ["-c:v", "h264_videotoolbox", "-b:v", rate, "-maxrate", rate, "-profile:v", "high", "-allow_sw", "1"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf)]

def hwdec(hw):
    return ["-hwaccel", "videotoolbox"] if hw.get("vt_decode") else []

def stream_dur(FF, path, sel):
    """Точная длина потока: число декодированных кадров / сэмплов (а не время последнего пакета)."""
    if sel == "v":
        r = subprocess.run([FF, "-hide_banner", "-i", path, "-map", "0:v:0", "-fps_mode", "passthrough", "-f", "null", "-"], capture_output=True, text=True).stderr
        fr = re.findall(r"frame=\s*(\d+)", r); fps = re.search(r"(\d+(?:\.\d+)?) fps", r)
        f = FPS_MAP.get(fps.group(1), float(fps.group(1))) if fps else 30.0
        return int(fr[-1]) / f if fr else None
    r = subprocess.run([FF, "-hide_banner", "-i", path, "-map", "0:a:0", "-af", "astats=metadata=0:reset=0", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    n = re.search(r"Number of samples: (\d+)", r); sr = re.search(r"(\d+) Hz", r)
    return int(n.group(1)) / int(sr.group(1)) if n and sr else None

def load_env(FF, proxy, work):
    import numpy as np
    npy = os.path.join(work, "env_" + re.sub(r"\W", "_", os.path.basename(proxy)) + ".npy")
    if os.path.exists(npy):
        return np.load(npy)
    p = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", proxy, "-vn", "-ac", "1", "-ar", "16000",
                        "-f", "f32le", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, np.float32)
    n = len(a) // 160
    rms = np.sqrt((a[:n * 160].astype(np.float64).reshape(n, 160) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    np.save(npy, db)
    return db

class Voice:
    """Огибающая громкости 10 мс: где реально звучит голос (а не где ASR поставил метку)."""
    def __init__(self, db, cfg):
        import numpy as np
        self.db = db
        floor, p95 = float(np.percentile(db, 10)), float(np.percentile(db, 95))
        self.thr = max(floor + cfg.get("thr_over_floor_db", 10), p95 - cfg.get("thr_below_peak_db", 32))
        log(f"звук: фон {floor:.1f} dB, пики {p95:.1f} dB, порог голоса {self.thr:.1f} dB")

    def loud(self, t):
        i = int(round(t * 100))
        return 0 <= i < len(self.db) and self.db[i] >= self.thr

    def silent_runs(self, a, b, min_len):
        runs = []; t = a; start = None
        while t < b:
            if not self.loud(t):
                if start is None:
                    start = t
            else:
                if start is not None and t - start >= min_len:
                    runs.append((start, t))
                start = None
            t += 0.01
        if start is not None and b - start >= min_len:
            runs.append((start, b))
        return runs

def refine_range(ws, allw, V, c):
    """Границы куска по звуку: начало — где голос реально начался, конец — где затих (окончания не режем).
    Внутри режем только настоящую тишину длиннее min_pause, оставляя воздух по краям."""
    first, last = ws[0], ws[-1]
    i0 = allw.index(first); i1 = allw.index(last)
    prev_end = allw[i0 - 1]["end"] if i0 > 0 else 0.0
    next_start = allw[i1 + 1]["start"] if i1 + 1 < len(allw) else 1e9
    t = first["start"]; lim = max(first["start"] - c["lead_max"], prev_end + 0.05)
    while t - 0.01 > lim and V.loud(t - 0.01):
        t -= 0.01
    a = max(t - c["lead_pad"], prev_end + 0.03, 0.0)
    t = last["end"]; lim = min(last["end"] + c["tail_max"], next_start - 0.05); quiet = 0
    while t < lim:
        quiet = quiet + 1 if not V.loud(t) else 0
        if quiet >= 8:
            t -= 0.07; break
        t += 0.01
    b = min(t + c["tail_pad"], next_start - 0.03)
    # внутренние паузы
    parts = [[a, b]]
    for rs, re_ in V.silent_runs(a + 0.05, b - 0.05, c["min_pause"]):
        ca, cb = rs + c["keep_before"], re_ - c["keep_after"]
        if cb - ca < 0.1:
            continue
        if any(w["start"] < cb and w["end"] > ca + 0.04 for w in ws):   # тихое слово — не режем
            continue
        cur = parts[-1]
        if cur[0] < ca < cur[1]:
            parts[-1] = [cur[0], ca]; parts.append([cb, cur[1]])
    # звук без слов (эканье, вдох, чмок) — в отчёт
    flags = []
    for s0, s1 in parts:
        t = s0; run = None
        while t < s1:
            covered = any(w["start"] - 0.1 <= t <= w["end"] + 0.12 for w in ws)
            if V.loud(t) and not covered:
                run = run or t
            else:
                if run and t - run >= 0.22:
                    flags.append([round(run, 2), round(t, 2)])
                run = None
            t += 0.01
    return parts, flags

# ================= лица / взгляд =================
def face_full(img, model):
    import cv2
    h, w = img.shape[:2]
    sw, sh = 540, int(540 * h / w)
    small = cv2.resize(img, (sw, sh))
    d = cv2.FaceDetectorYN.create(model, "", (sw, sh), score_threshold=0.6)
    d.setInputSize((sw, sh))
    _, faces = d.detect(small)
    if faces is None or len(faces) == 0:
        return None
    f = max(faces, key=lambda f: f[2] * f[3]); k = w / sw
    L = [(f[4 + 2 * i] * k, f[5 + 2 * i] * k) for i in range(5)]   # глаз П, глаз Л, нос, рот П, рот Л
    ex, ey = (L[0][0] + L[1][0]) / 2, (L[0][1] + L[1][1]) / 2
    ed = max(1.0, math.dist(L[0], L[1]))
    my = (L[3][1] + L[4][1]) / 2
    return {"box": [f[0] * k, f[1] * k, f[2] * k, f[3] * k], "yaw": (L[2][0] - ex) / ed, "pitch": (my - ey) / ed}

def frame_at(FF, path, t, out, hw=None):
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{max(0, t):.3f}", "-i", path, "-frames:v", "1", out])
    import cv2
    return cv2.imread(out)

def face_thumb(img, fc, size=150):
    import cv2
    h, w = img.shape[:2]
    if fc:
        x, y, bw, bh = fc["box"]; cx, cy = x + bw / 2, y + bh / 2; s = bw * 1.7
    else:
        cx, cy, s = w / 2, h * 0.4, w * 0.6
    x0, y0 = int(max(0, cx - s / 2)), int(max(0, cy - s / 2))
    x1, y1 = int(min(w, cx + s / 2)), int(min(h, cy + s / 2))
    return cv2.resize(img[y0:y1, x0:x1], (size, size))

def sheet(rows, path, size=150):
    """rows: [(label, [img,...])] -> один jpg с подписями."""
    from PIL import Image, ImageDraw, ImageFont
    import cv2
    ncol = max(len(r[1]) for r in rows)
    W, H = 220 + ncol * (size + 4), len(rows) * (size + 6) + 6
    im = Image.new("RGB", (W, H), (20, 20, 22)); dr = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype(os.path.join(HERE, "assets", "fonts", "GolosText.ttf"), 17)
    except Exception:
        font = ImageFont.load_default()
    for r, (label, imgs) in enumerate(rows):
        y = 6 + r * (size + 6)
        for i, line in enumerate(label.split("\n")[:6]):
            dr.text((6, y + i * 22), line[:24], fill=(235, 235, 235), font=font)
        for c, img in enumerate(imgs):
            if img is None:
                continue
            im.paste(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), (220 + c * (size + 4), y))
    im.save(path, quality=86)

# ================= якоря =================
def find_anchor(key, content):
    """'слово' — префикс, '=слово' — точное совпадение, 'слово#2' — второе вхождение. -> (ns, ne) до ускорения."""
    k = key.lower(); nth = 1
    if "#" in k:
        k, n = k.rsplit("#", 1); nth = int(n)
    exact = k.startswith("=")
    k = k.lstrip("=")
    hit = 0
    for w in content:
        toks = w.get("orig", w["word"].lower()).split()
        if any((t == k) if exact else t.startswith(k) for t in toks):
            hit += 1
            if hit == nth:
                return w["ns"], w["ne"]
    return None

def resolve_times(obj, content, sp, missing):
    if isinstance(obj, list):
        return [resolve_times(x, content, sp, missing) for x in obj]
    if not isinstance(obj, dict):
        return obj
    out = {}
    for k, v in obj.items():
        if k.endswith("word") and isinstance(v, str):
            a = find_anchor(v, content)
            tk = {"at_word": "t", "until_word": "t_end", "word": "t"}.get(k, k[:-4] + "t")
            if a is None:
                missing.append(v); continue
            out[tk] = round((a[1] if k.startswith("until") or k.endswith("end_word") else a[0]) / sp, 3)
        else:
            out[k] = resolve_times(v, content, sp, missing)
    return out

# ================= режимы =================
def mode_review(FF, src, proxy, words, plan, cfg, work, outdir, name, hw):
    import cv2
    V = Voice(load_env(FF, proxy, work), cfg["cut"])
    model = os.path.join(HERE, "models", "yunet.onnx")
    res = []; rows = []; n = plan.get("frames", 8)
    # время слов — от первого сэмпла звука; a_start — где звук стоит в таймлайне файла (пустая правка elst),
    # av_offset — на сколько звук отстаёт от губ (мерили по губам). Кадр к слову в t — это t + a_start - av_offset.
    off = float(plan.get("av_offset", 0.0)) - float(plan.get("a_start", 0.0))
    for tk in plan["takes"]:
        ws = [w for w in words if tk["lo"] <= w["start"] < tk["hi"]]
        ws, _ = drop_service(ws, cfg["service_phrases"])
        if not ws:
            continue
        parts, flags = refine_range(ws, words, V, cfg["cut"])
        a, b = parts[0][0], parts[-1][1]
        thumbs = []; yaw = []; pitch = []
        for i in range(n):
            t = a + (b - a) * (i + 0.5) / n
            img = frame_at(FF, proxy, t - off, os.path.join(work, "rv.png"))
            fc = face_full(img, model) if img is not None else None
            thumbs.append(face_thumb(img, fc) if img is not None else None)
            yaw.append(round(fc["yaw"], 3) if fc else None); pitch.append(round(fc["pitch"], 3) if fc else None)
        low = [x["word"].lower() for x in ws]
        rep = [low[i] for i in range(1, len(low)) if low[i] == low[i - 1] and len(low[i]) > 1]
        txt = " ".join(low)
        res.append({"id": tk["id"], "a": round(a, 2), "b": round(b, 2), "dur": round(b - a, 2), "text": txt,
                    "parts": len(parts), "no_word_sound": flags, "repeats": rep, "yaw": yaw, "pitch": pitch})
        rows.append((f"{tk['id']}  {a:.1f}с\n{b-a:.1f}с\n" + "\n".join(re.findall(r".{1,24}(?:\s|$)", txt)[:4]), thumbs))
    per = plan.get("rows_per_sheet", 11)
    for i in range(0, len(rows), per):
        sheet(rows[i:i + per], os.path.join(outdir, f"{name}_review_{i // per + 1}.jpg"))
    json.dump(res, open(os.path.join(outdir, f"{name}_review.json"), "w"), ensure_ascii=False, indent=1, default=float)
    log(f"ревью: {len(res)} дублей, листов {math.ceil(len(rows) / per)}")

def mode_base(FF, src, proxy, words, plan, cfg, work, outdir, name, hw, info):
    import cv2
    fps = info["fps"]; sp = plan.get("speed", cfg["pacing"]["global_speed"]); c = cfg["cut"]
    vfr = bool(plan.get("cfr30", abs(fps - 30) > 0.1))   # камера писала с плавающей частотой: приводим к 30 по таймстемпам
    if vfr:
        log(f"частота источника {fps:.2f} fps (плавающая) -> фрагменты приводятся к 30 fps по таймстемпам"); fps = 30.0
    # время слов — от первого сэмпла звука (так их даёт ASR); a_start — где этот сэмпл стоит в таймлайне файла
    # (пустая правка elst в индексе MOV), av_offset — на сколько звук отстаёт от губ (мерили по губам).
    a0 = float(plan.get("a_start", 0.0)); off = float(plan.get("av_offset", 0.0)) - a0
    draft = bool(plan.get("draft", False))    # черновик: 720x1280
    if a0 or off:
        log(f"синхрон: звук режется с {a0:+.3f} с к времени слов, картинка — с {-off:+.3f} с")
    dur = duration(FF, src)
    V = Voice(load_env(FF, proxy, work), c)
    segs = []; seg_words = []; seg_take = []; flags_all = []; seg_opt = []
    for k, item in enumerate(plan["edl"]):
        lo, hi = item[0], item[1]; opt = item[2] if len(item) > 2 else {}   # opt: {"mute_from": t} — звук глушится с t (слово обрывается)
        ws = [w for w in words if lo <= w["start"] < hi]
        ws, rm = drop_service(ws, cfg["service_phrases"])
        if rm:
            log(f"  кусок {lo:.1f}–{hi:.1f}: вырезано служебное {rm}")
        if opt.get("raw"):   # opt raw: кусок без слов (молчаливый взгляд) — берётся ровно [lo, hi]
            ws = []; parts, flags = [[lo, hi]], []
        elif not ws:
            log(f"  ⚠ кусок {lo:.1f}–{hi:.1f} пустой"); continue
        else:
            parts, flags = refine_range(ws, words, V, dict(c, min_pause=opt.get("min_pause", c["min_pause"])))   # opt min_pause: не резать паузы внутри куска
        flags_all += flags
        for s0, s1 in parts:
            f0 = math.floor(s0 * fps); f1 = math.ceil(s1 * fps)
            s0q, s1q = f0 / fps, f1 / fps
            segs.append((s0q, s1q, f1 - f0)); seg_take.append(k); seg_opt.append(opt)
            seg_words.append([w for w in ws if s0q - 0.02 <= w["start"] < s1q])
    offs = []; acc = 0.0
    for s0, s1, nfr in segs:
        offs.append(acc); acc += nfr / fps
    total = acc
    content = []
    for (s0, s1, nfr), o, ws in zip(segs, offs, seg_words):
        for w in ws:
            w2 = dict(w); w2["ns"] = o + max(0.0, w["start"] - s0); w2["ne"] = o + (min(w["end"], s1) - s0)
            content.append(w2)
    content = normalize(content, plan.get("replace"))
    log(f"монтаж: {len(plan['edl'])} кусков -> {len(segs)} фрагментов, {total:.1f} с до ускорения ({total/sp:.1f} с после)")
    log(f"текст: «{' '.join(w['word'] for w in content)}»")
    if flags_all:
        log(f"звук без слов (проверить): {flags_all}")

    # кадр
    ref = os.path.join(work, "ref.png"); grab(FF, src, max(0.0, min(segs[0][0] - off + 0.5, dur - 0.1)), ref)
    H0, W0 = cv2.imread(ref).shape[:2]
    fr = cfg["framing"]; model = os.path.join(HERE, "models", "yunet.onnx")
    boxes = []; last = None; zi = 0
    for k, (s0, s1, nfr) in enumerate(segs):
        f = face_at(FF, proxy, max(0.0, (s0 + s1) / 2 - off), work, W0, H0, model) or last
        last = f
        zi = zi + 1 if (k > 0 and seg_take[k] == seg_take[k - 1]) else zi   # зум меняем только на джамп-кате
        z = 1.0 if zi % 2 == 0 else fr["zoom_alt"]
        boxes.append(crop_box(f, W0, H0, fr, z))

    # якоря и B-roll (время до ускорения)
    brolls = []
    broot = resolve(HERE, cfg["paths"]["broll_root"])
    for br in plan.get("broll", []):
        a = find_anchor(br["at_word"], content)
        if not a:
            log(f"  ⚠ B-roll: якорь не найден {br['at_word']}"); continue
        u = find_anchor(br.get("until_word", ""), content) if br.get("until_word") else None
        bs = a[0] - 0.05; be = (u[1] + 0.12) if u else bs + br.get("dur", 2.5)
        be = min(max(be, bs + cfg["broll"]["min_s"]), total - 0.05)
        shoot, fname = br["file"].split("/", 1)
        brolls.append({"file": br["file"], "path": resolve(os.path.join(broot, shoot), fname),
                       "start": br.get("start", 2.0), "win": (bs, be)})
        log(f"B-roll: {br['file']} {bs/sp:.2f}–{be/sp:.2f} с (финал)")

    # проход 1: фрагменты точно по кадрам, звук ровно той же длины
    sr = 48000; parts_f = []
    for k, ((s0, s1, nfr), (cw, ch, cx, cy)) in enumerate(zip(segs, boxes)):
        pth = os.path.join(work, f"seg_{k:02d}.mov"); ns = round(nfr / fps * sr)
        mf = seg_opt[k].get("mute_from")
        mute = f",afade=t=out:st={mf - s0 - 0.025:.3f}:d=0.025" if mf and s0 < mf < s1 else ""
        run([FF, "-y", "-hide_banner", "-loglevel", "error"] + hwdec(hw) + ["-ss", f"{max(0.0, s0 - off):.4f}", "-i", src,
             "-ss", f"{s0 + a0:.4f}", "-i", src, "-map", "0:v:0", "-map", "1:a:0",
             "-vf", ("fps=30," if vfr else "") + f"crop={cw}:{ch}:{cx}:{cy},scale=1080:1920:flags=lanczos,setsar=1,format=yuv420p",
             "-frames:v", str(nfr), "-af", f"aresample={sr},apad,atrim=end_sample={ns}{mute}"]
            + venc(hw, "45M", 12) + ["-bf", "0", "-c:a", "pcm_s16le", "-ac", "2", pth])
        parts_f.append(pth)
    bad = []
    for k, pth in enumerate(parts_f):
        v_, a_ = stream_dur(FF, pth, "v"), stream_dur(FF, pth, "a")
        if v_ is None or a_ is None or abs(v_ - a_) > 0.02:
            bad.append((k, v_, a_))
    log(f"фрагменты: {len(parts_f)}, с расхождением видео/звук >20 мс: {bad if bad else 'нет'}")
    bparts = []
    for i, br in enumerate(brolls):
        bs, be = br["win"]; bp = os.path.join(work, f"broll_{i}.mov"); nfr = math.ceil((be - bs) * fps) + 1
        run([FF, "-y", "-hide_banner", "-loglevel", "error"] + hwdec(hw) + ["-ss", f"{br['start']:.3f}", "-i", br["path"],
             "-vf", f"fps={fps:.5f},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p",
             "-frames:v", str(nfr), "-an"] + venc(hw, "30M", 12) + [bp])
        bparts.append(bp)
    # склейка фильтром concat: каждый фрагмент выравнивается сам (видео/звук), ошибка не копится
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error"]
    for pth in parts_f:
        cmd += ["-i", pth]
    n = len(parts_f)
    fc = [f"[{i}:v]setpts=PTS-STARTPTS[v{i}];[{i}:a]asetpts=PTS-STARTPTS[a{i}]" for i in range(n)]
    fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[cv][ca]")
    vlast = "cv"
    for i, (bp, br) in enumerate(zip(bparts, brolls)):
        bs, be = br["win"]; cmd += ["-i", bp]
        fc.append(f"[{n+i}:v]setpts=PTS-STARTPTS+{bs:.3f}/TB[bv{i}]")
        fc.append(f"[{vlast}][bv{i}]overlay=0:0:enable='between(t,{bs:.3f},{be:.3f})':eof_action=pass[ob{i}]")
        vlast = f"ob{i}"
    grade = plan.get("colorgrade", cfg["colorgrade"]["ffmpeg"])
    if cfg["colorgrade"].get("lut") and not plan.get("no_lut"):
        grade += f",lut3d=file='{resolve(HERE, cfg['colorgrade']['lut'])}'"
    scale = ",scale=720:1280:flags=lanczos" if draft else ""
    fc.append(f"[{vlast}]{grade},setpts=PTS/{sp},fps=30{scale},format=yuv420p[vout]")
    fc.append(f"[ca]{plan.get('voice_chain', cfg['voice']['chain'])},aresample=48000,atempo={sp}[aout]")
    base = os.path.join(outdir, f"{name}_base.mp4")
    run(cmd + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]"] + venc(hw, "24M", 14)
        + ["-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", base])
    bv, ba = stream_dur(FF, base, "v"), stream_dur(FF, base, "a")
    log(f"база: {base} — видео {bv:.3f} с, звук {ba:.3f} с, расхождение {abs(bv-ba)*1000:.0f} мс")

    # таймлайн для Remotion (всё в финальном времени)
    acc_pref = [p.lower() for p in plan.get("accents", [])]
    subs = [{"w": w["word"], "t0": round(w["ns"] / sp, 3), "t1": round(w["ne"] / sp, 3),
             "acc": bool(re.search(r"\d", w["word"])) or any(w.get("orig", "").startswith(p) for p in acc_pref)}
            for w in content]
    missing = []
    graphics = resolve_times(plan.get("graphics", []), content, sp, missing)
    if missing:
        log(f"⚠ якоря графики не найдены: {missing}")
    cuts = [round(o / sp, 3) for o in offs]
    tl = {"fps": 30, "duration": round(total / sp, 3), "words": subs, "graphics": graphics, "cuts": cuts,
          "broll": [{"file": b["file"], "t0": round(b["win"][0] / sp, 3), "t1": round(b["win"][1] / sp, 3)} for b in brolls],
          "subtitles": plan.get("subtitles", {})}
    json.dump(tl, open(os.path.join(outdir, f"{name}_timeline.json"), "w"), ensure_ascii=False, indent=1, default=float)

    # QA склеек: лицо в начале/середине/конце каждого фрагмента (взгляд, джамп-каты)
    rows = []
    for k, ((s0, s1, nfr), o) in enumerate(zip(segs, offs)):
        ts = [o + 0.08, o + nfr / fps / 2, o + nfr / fps - 0.08]
        th = []
        for t in ts:
            img = frame_at(FF, base, t / sp, os.path.join(work, "qa.png"))
            th.append(face_thumb(img, face_full(img, model)) if img is not None else None)
        txt = " ".join(w["word"] for w in seg_words[k])
        rows.append((f"#{k+1} {o/sp:.1f}с\n" + "\n".join(re.findall(r".{1,24}(?:\s|$)", txt)[:4]), th))
    for i in range(0, len(rows), 12):
        sheet(rows[i:i + 12], os.path.join(outdir, f"{name}_cuts_{i // 12 + 1}.jpg"))
    json.dump({"log": LOG, "edl": plan["edl"], "segments": [[round(a, 3), round(b, 3), n] for a, b, n in segs],
               "fps": fps, "flags": flags_all}, open(os.path.join(outdir, f"{name}_report.json"), "w"), ensure_ascii=False, indent=1, default=float)

def mode_composite(FF, plan, cfg, work, outdir, name, hw):
    base = os.path.join(outdir, f"{name}_base.mp4")
    ov = next((os.path.join(outdir, f"{name}_overlay{e}") for e in (".webm", ".mov") if os.path.exists(os.path.join(outdir, f"{name}_overlay{e}"))), None)
    tl = json.load(open(os.path.join(outdir, f"{name}_timeline.json")))
    pop, whoosh, _ = sfx_files(FF, work)
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", base]
    fc = []; vin = "0:v"; idx = 1
    if ov:
        cmd += (["-c:v", "libvpx-vp9"] if ov.endswith(".webm") and hw.get("vp9_alpha_dec") else []) + ["-i", ov]
        fc.append(f"[0:v][1:v]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[vout]"); idx = 2
    else:
        log("⚠ оверлея нет — собираю без графики"); fc.append("[0:v]null[vout]")
    events = [("whoosh", max(0.0, b["t0"] - 0.14)) for b in tl.get("broll", [])]
    events += [("pop", g["t"]) for g in tl.get("graphics", []) if g.get("sfx", "pop") == "pop" and "t" in g]
    mix = ["[0:a]"]
    for j, (kind, t) in enumerate(events):
        cmd += ["-i", pop if kind == "pop" else whoosh]; ms = int(t * 1000)
        vol = cfg["inserts"]["sfx_db"] - 6 if kind == "pop" else -20
        fc.append(f"[{idx}:a]adelay={ms}|{ms},volume={vol}dB[sx{j}]"); mix.append(f"[sx{j}]"); idx += 1
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0,alimiter=limit=0.95[aout]")
    out = os.path.join(outdir, f"{name}_final.mp4")
    run(cmd + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]"] + venc(hw, "16M", 17)
        + ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    fv, fa = stream_dur(FF, out, "v"), stream_dur(FF, out, "a")
    r = subprocess.run([FF, "-hide_banner", "-i", out, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    li = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    log(f"готово: {out} ({fv:.1f} с, {os.path.getsize(out)/1e6:.1f} МБ), звук {fa:.2f} с, громкость {li[-1] if li else '?'} LUFS")
    qa = os.path.join(outdir, f"{name}_qa.jpg"); n = 21
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", out, "-vf",
         f"fps={n/fv:.4f},scale=240:427,tile=7x3", "-frames:v", "1", qa])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True); ap.add_argument("--proxy"); ap.add_argument("--name", required=True)
    ap.add_argument("--plan"); ap.add_argument("--words"); ap.add_argument("--transcribe-only", action="store_true")
    a = ap.parse_args(); t0 = time.time()
    cfg = json.load(open(os.path.join(HERE, "config.json")))
    FF = ffbin()
    src = os.path.expanduser(a.src)
    proxy = os.path.expanduser(a.proxy) if a.proxy else os.path.join(os.path.dirname(src), "Proxy", os.path.basename(src))
    if not os.path.exists(proxy):
        proxy = src
    work = os.path.join(cfg["paths"]["work"], a.name); os.makedirs(work, exist_ok=True)
    for f in os.listdir(work):
        if f.startswith(("seg_", "broll_", "joined", "chunk_", "face_")):
            os.remove(os.path.join(work, f))
    outdir = os.path.join(HERE, cfg["paths"]["output"]); os.makedirs(outdir, exist_ok=True)
    plan = json.load(open(os.path.expanduser(a.plan))) if a.plan else {}
    mode = plan.get("mode", "base")
    info, hw = probe(FF, src)
    log(f"источник: {os.path.basename(src)} {info['codec']} {info['size']} {info['fps_str']} fps; прокси: {'да' if proxy != src else 'нет'}; аппаратно: {hw}")
    if mode == "probe":
        return
    if mode == "composite":
        mode_composite(FF, plan, cfg, work, outdir, a.name, hw)
        log(f"время: {time.time()-t0:.0f} с"); return
    wpath = os.path.join(outdir, f"{a.name}_words.json")
    if a.words and os.path.exists(os.path.expanduser(a.words)):
        words = json.load(open(os.path.expanduser(a.words)))
    else:
        words = asr_long(FF, proxy, work, cfg)
        json.dump(words, open(wpath, "w"), ensure_ascii=False, indent=0)
    if a.transcribe_only:
        write_transcript(words, os.path.join(outdir, f"{a.name}_transcript.txt")); return
    if mode == "review":
        mode_review(FF, src, proxy, words, plan, cfg, work, outdir, a.name, hw)
    else:
        mode_base(FF, src, proxy, words, plan, cfg, work, outdir, a.name, hw, info)
    log(f"время: {time.time()-t0:.0f} с")

if __name__ == "__main__":
    main()
