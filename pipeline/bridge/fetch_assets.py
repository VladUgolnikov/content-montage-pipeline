#!/usr/bin/env python3
"""Скачивание открытых ассетов в pipeline/assets: звуки Kenney (CC0) и шрифты Google Fonts (OFL)."""
import os, re, io, json, zipfile, urllib.request
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) MAOS-assets"}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
# --- Kenney ---
sfx = os.path.join(PIPE, "assets", "sfx", "kenney"); os.makedirs(sfx, exist_ok=True)
for slug in ["interface-sounds", "ui-audio", "impact-sounds", "digital-audio", "casino-audio"]:
    try:
        html = get(f"https://kenney.nl/assets/{slug}").decode("utf8", "ignore")
        m = re.search(r'https://kenney\.nl/media/pages/assets/[^"\']+?\.zip', html)
        if not m:
            print(f"kenney {slug}: ссылка на zip не найдена"); continue
        z = zipfile.ZipFile(io.BytesIO(get(m.group(0))))
        out = os.path.join(sfx, slug); os.makedirs(out, exist_ok=True)
        n = 0
        for nm in z.namelist():
            if nm.lower().endswith((".ogg", ".wav", ".mp3")) or nm.lower().endswith(("license.txt",)):
                with open(os.path.join(out, os.path.basename(nm)), "wb") as f:
                    f.write(z.read(nm)); n += 1
        print(f"kenney {slug}: {n} файлов")
    except Exception as e:
        print(f"kenney {slug}: ошибка {e}")
# --- Google Fonts ---
fdir = os.path.join(PIPE, "assets", "fonts", "google"); os.makedirs(fdir, exist_ok=True)
for fam in ["montserrat", "unbounded", "onest", "rubik", "manrope", "alumnisans", "sofiasansextracondensed",
            "delagothicone", "tektur", "badscript", "neucha", "pangolin"]:
    try:
        items = json.loads(get(f"https://api.github.com/repos/google/fonts/contents/ofl/{fam}"))
        out = os.path.join(fdir, fam); os.makedirs(out, exist_ok=True); n = 0; cyr = False
        for it in items:
            if it["name"].endswith(".ttf") or it["name"] in ("OFL.txt", "METADATA.pb"):
                data = get(it["download_url"])
                open(os.path.join(out, it["name"]), "wb").write(data); n += 1
                if it["name"] == "METADATA.pb": cyr = b'"cyrillic"' in data
        print(f"font {fam}: {n} файлов, кириллица: {'да' if cyr else 'НЕТ'}")
    except Exception as e:
        print(f"font {fam}: ошибка {e}")
