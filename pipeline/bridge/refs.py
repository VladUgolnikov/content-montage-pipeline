#!/usr/bin/env python3
"""Сбор референсов через Apify. Режим {"mode":"raw","out":...,"calls":[...]} — сырые выдачи акторов.
 (ключ читается из bridge/_archive/*Apify*.json, в лог не выводится).
  python3 bridge/refs.py refs.json   ; refs.json = {"out": "...", "urls": [...]}
Для каждого ролика: подпись, метаданные, видео (если отдано), звук, расшифровка (GigaAM для русского),
лист кадров (1 кадр/с), число склеек и средняя длина плана. Итог — <out>/refs_summary.json
"""
import os, sys, json, re, glob, time, urllib.request, subprocess, unicodedata
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, PIPE)
from montage import ffbin, asr_long, duration

def token():
    for f in glob.glob(os.path.join(PIPE, "bridge", "*.json")) + glob.glob(os.path.join(PIPE, "bridge", "_archive", "*.json")):
        if "apify" not in unicodedata.normalize("NFC", os.path.basename(f)).lower():
            continue
        def walk(o):
            if isinstance(o, str) and o.strip().startswith("apify_api_"): return o.strip()
            if isinstance(o, dict): o = list(o.values())
            if isinstance(o, list):
                for v in o:
                    r = walk(v)
                    if r: return r
        try:
            t = walk(json.load(open(f)))
        except Exception:
            t = (re.search(r"apify_api_\w+", open(f).read()) or [None])[0]
        if t: return t
    raise SystemExit("ключ Apify не найден")

def apify(actor, inp, tok, timeout=300):
    url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items?timeout={timeout}"
    req = urllib.request.Request(url, data=json.dumps(inp).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout + 30))
    except urllib.error.HTTPError as e:
        print(f"  Apify {actor}: HTTP {e.code} {e.read()[:300]!r}", flush=True); return []

def get(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def analyze(FF, cfg, vid, base, cyr):
    d = duration(FF, vid); res = {"dur": round(d, 1)}
    # склейки
    r = run([FF, "-hide_banner", "-i", vid, "-vf", "select='gt(scene,0.3)',showinfo", "-an", "-f", "null", "-"])
    cuts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    res["cuts"] = len(cuts); res["avg_shot_s"] = round(d / (len(cuts) + 1), 2); res["cut_times"] = [round(c, 1) for c in cuts]
    # лист кадров 1/с, до 60 кадров, 6 в ряд
    n = min(60, max(6, int(d)))
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", vid, "-vf",
         f"fps={n/d:.4f},scale=180:-2,tile=6x{(n+5)//6}", "-frames:v", "1", "-q:v", "4", base + "_sheet.jpg"])
    # громкость
    r = run([FF, "-hide_banner", "-i", vid, "-af", "ebur128", "-f", "null", "-"])
    li = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr); res["lufs"] = li[-1] if li else None
    # расшифровка (русский — GigaAM)
    if cyr:
        work = os.path.join(os.path.dirname(base), "_work"); os.makedirs(work, exist_ok=True)
        try:
            ws = asr_long(FF, vid, work, cfg)
            res["transcript"] = " ".join(w["word"] for w in ws)
        except Exception as e:
            res["transcript_err"] = str(e)[:200]
    return res

def api(path, tok, data=None, method=None, timeout=60):
    req = urllib.request.Request("https://api.apify.com/v2/" + path, data=None if data is None else json.dumps(data).encode(),
                                 method=method or ("POST" if data is not None else "GET"),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def raw_call(c, tok, out):
    """Одна выдача: {"name","get"} — GET к API; {"name","actor","input","timeout"} — асинхронный запуск актора."""
    name = c["name"]; t0 = time.time(); meta = {"name": name}
    try:
        if "get" in c:
            data = api(c["get"], tok)
        else:
            run = api(f"acts/{c['actor']}/runs?timeout={c.get('timeout', 900)}", tok, c["input"])["data"]
            rid = run["id"]
            while run["status"] in ("READY", "RUNNING"):
                time.sleep(5); run = api(f"actor-runs/{rid}", tok)["data"]
            data = api(f"datasets/{run['defaultDatasetId']}/items?clean=1&format=json", tok, timeout=180)
            meta.update(status=run["status"], usd=run.get("usageTotalUsd"))
    except urllib.error.HTTPError as e:
        data = {"error": e.code, "body": e.read()[:600].decode("utf8", "ignore")}
    except Exception as e:
        data = {"error": str(e)[:300]}
    json.dump(data, open(os.path.join(out, name + ".json"), "w"), ensure_ascii=False)
    meta.update(n=len(data) if isinstance(data, list) else 1, sec=round(time.time() - t0))
    print(f"  {name}: {meta}", flush=True)
    return meta

def raw(spec):
    from concurrent.futures import ThreadPoolExecutor
    out = os.path.join(PIPE, spec["out"]); os.makedirs(out, exist_ok=True); tok = token()
    with ThreadPoolExecutor(max_workers=spec.get("parallel", 4)) as ex:
        metas = list(ex.map(lambda c: raw_call(c, tok, out), spec["calls"]))
    json.dump(metas, open(os.path.join(out, "_runs_" + time.strftime("%H%M%S") + ".json"), "w"), ensure_ascii=False, indent=1)
    print("готово raw:", out, "usd:", round(sum((m.get("usd") or 0) for m in metas), 3), flush=True)

def dl(spec):
    """{"mode":"dl","out":...,"items":[{"name","url"}]} — скачать файлы (видео выбросов), без Apify."""
    out = os.path.join(PIPE, spec["out"]); os.makedirs(out, exist_ok=True); ok = 0
    for it in spec["items"]:
        path = os.path.join(out, it["name"])
        if os.path.exists(path): ok += 1; continue
        try:
            get(it["url"], path); ok += 1
        except Exception as e:
            print("  не скачал", it["name"], str(e)[:120], flush=True)
    print(f"готово dl: {ok}/{len(spec['items'])} -> {out}", flush=True)

def hooks(spec):
    """{"mode":"hooks","dir":...,"sec":20} — для каждого mp4: расшифровка первых N с (GigaAM, пословно) + лист кадров 0/1/2/3.5 с."""
    FF = ffbin(); cfg = json.load(open(os.path.join(PIPE, "config.json")))
    d = os.path.join(PIPE, spec["dir"]); sec = spec.get("sec", 20)
    outj = os.path.join(d, "_hooks.json"); res = json.load(open(outj)) if os.path.exists(outj) else {}
    fr = os.path.join(d, "_frames"); os.makedirs(fr, exist_ok=True)
    for f in sorted(x for x in os.listdir(d) if x.endswith(".mp4")):
        if f in res: continue
        v = os.path.join(d, f); base = f[:-4]; rec = {}
        try:
            rec["dur"] = round(duration(FF, v), 1)
            run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", v, "-vf",
                 "select='eq(n\\,3)+eq(n\\,30)+eq(n\\,60)+eq(n\\,105)',scale=270:-2,tile=4x1", "-frames:v", "1", "-vsync", "0",
                 os.path.join(fr, base + ".jpg")])
            work = os.path.join(d, "_work"); os.makedirs(work, exist_ok=True)
            clip = os.path.join(work, "clip.mp4")
            for junk in [clip] + glob.glob(os.path.join(work, "*.wav")):
                if os.path.exists(junk): os.remove(junk)
            asrc = os.path.join(d, base + ".m4a") if os.path.exists(os.path.join(d, base + ".m4a")) else v
            run([FF, "-y", "-hide_banner", "-loglevel", "error", "-t", str(sec), "-i", asrc, "-vn", "-c:a", "aac", clip])
            if not os.path.exists(clip) or os.path.getsize(clip) < 2000:
                raise RuntimeError("нет звука")
            ws = asr_long(FF, clip, work, cfg)
            rec["words"] = [[w["word"], w["start"]] for w in ws]
            rec["text"] = " ".join(w["word"] for w in ws)
        except Exception as e:
            rec["err"] = str(e)[:200]
        res[f] = rec; json.dump(res, open(outj, "w"), ensure_ascii=False)
        print(f"  {f}: {rec.get('dur')}с | {rec.get('text','')[:90]}", flush=True)
    print("готово hooks:", len(res), flush=True)

def main():
    spec = json.load(open(sys.argv[1]))
    if spec.get("mode") == "dl":
        return dl(spec)
    if spec.get("mode") == "hooks":
        return hooks(spec)
    if spec.get("mode") == "raw":
        return raw(spec)
    main_refs(spec)

def main_refs(spec):
    out = os.path.join(PIPE, spec["out"]); os.makedirs(out, exist_ok=True)
    tok = token(); FF = ffbin(); cfg = json.load(open(os.path.join(PIPE, "config.json")))
    ig = [u.split("?")[0] for u in spec["urls"] if "instagram.com" in u]
    yt = [u for u in spec["urls"] if "youtu" in u]
    items = []
    if ig:
        print(f"Instagram: {len(ig)} ссылок", flush=True)
        items += [("ig", x) for x in apify("apify~instagram-scraper", {"directUrls": ig, "resultsType": "details", "resultsLimit": 1}, tok)]
    if yt:
        print(f"YouTube: {len(yt)} ссылок", flush=True)
        items += [("yt", x) for x in apify("streamers~youtube-scraper", {"startUrls": [{"url": u} for u in yt], "maxResults": 1,
                  "downloadSubtitles": True, "subtitlesLanguage": "any", "subtitlesFormat": "plaintext"}, tok)]
    summ = []
    for kind, x in items:
        sid = x.get("shortCode") or x.get("id") or str(len(summ))
        base = os.path.join(out, f"{kind}_{sid}")
        cap = x.get("caption") or x.get("text") or x.get("description") or ""
        rec = {"kind": kind, "id": sid, "url": x.get("url"), "author": x.get("ownerUsername") or x.get("channelName"),
               "caption": cap[:1500], "views": x.get("videoViewCount") or x.get("videoPlayCount") or x.get("viewCount"),
               "likes": x.get("likesCount"), "duration_meta": x.get("videoDuration") or x.get("duration"),
               "music": (x.get("musicInfo") or {}).get("song_name") if isinstance(x.get("musicInfo"), dict) else None}
        subs = x.get("subtitles")
        if subs:
            rec["transcript"] = " ".join(s.get("plaintext", "") if isinstance(s, dict) else str(s) for s in subs)[:20000]
        vurl = x.get("videoUrl")
        if vurl:
            try:
                get(vurl, base + ".mp4")
                cyr = bool(re.search("[а-яА-Я]", cap)) or True
                a = analyze(FF, cfg, base + ".mp4", base, cyr and "transcript" not in rec)
                rec.update(a)
            except Exception as e:
                rec["video_err"] = str(e)[:200]
        print(f"  {kind}_{sid}: @{rec['author']} {rec.get('dur')}с, склеек {rec.get('cuts')}, текст {len(rec.get('transcript',''))} зн.", flush=True)
        summ.append(rec)
    json.dump(summ, open(os.path.join(out, "refs_summary.json"), "w"), ensure_ascii=False, indent=1)
    print(f"готово: {len(summ)} роликов -> {out}/refs_summary.json", flush=True)

if __name__ == "__main__":
    main()
