#!/usr/bin/env python3
"""timeline.json (montage.py, режим base) + сценарий графики -> props.json для Remotion (композиция Reel).
  python3 build_props.py reels/output/NAME_timeline.json plans/NAME_gfx.json remotion/props/NAME.json
Сценарий графики ссылается на якоря id из plan["graphics"] (время уже в финальном таймлайне).
"""
import json, re, sys

ACC = ["выручк", "прибыл", "настолк", "продаваем", "марж", "морж", "ах*ел", "миллион", "утечк", "систем",
       "завтра", "дыр", "ошиб"]

SMALL = {"в", "на", "а", "и", "за", "до", "от", "с", "по", "у", "к", "о", "об", "что", "как", "мы", "я", "моя", "не"}

def chunks(words, cuts, max_chars=18, max_words=4, gap=0.35):
    """Строки субтитров: по паузам и склейкам, ≤ max_chars; строка не заканчивается предлогом/союзом."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur:
            prev = cur[-1]
            txt = " ".join(x["w"] for x in cur + [w])
            cut_between = any(prev["t0"] < c <= w["t0"] + 1e-3 for c in cuts)
            hard = w["t0"] - prev["t1"] > gap or cut_between
            if hard or len(txt) > max_chars or len(cur) >= max_words:
                carry = []
                if not hard and len(cur) > 1 and cur[-1]["w"].lower() in SMALL:
                    carry = [cur.pop()]
                out.append(cur); cur = carry
        cur.append(w)
    if cur:
        out.append(cur)
    return out

def is_acc(w):
    lw = w["w"].lower()
    return (bool(re.search(r"\d", lw)) and lw not in ("2", "1")) or any(lw.startswith(p) for p in ACC)

def main(tl_path, gfx_path, out_path):
    tl = json.load(open(tl_path)); gfx = json.load(open(gfx_path))
    dur = tl["duration"]; cuts = tl.get("cuts", [])
    G = {g["id"]: g for g in tl.get("graphics", []) if "id" in g}
    words = [w for w in tl["words"] if w["w"].strip()]
    S = gfx.get("subs", {})   # {max_chars, max_words, gap, min_dur, size}
    subs = []
    ch = chunks(words, cuts, S.get("max_chars", 18), S.get("max_words", 4), S.get("gap", 0.35))
    if S.get("merge_orphans", True) and S.get("min_dur"):
        # хвост из 1–2 слов короче 0.8 с приклеиваем к предыдущей строке (если та же склейка и влезает в 2 строки)
        m = []
        for c in ch:
            if m:
                p_ = m[-1]; txt = " ".join(x["w"] for x in p_ + c)
                dur_c = c[-1]["t1"] - c[0]["t0"]; gap_ = c[0]["t0"] - p_[-1]["t1"]
                cut_b = any(p_[-1]["t0"] < k <= c[0]["t0"] + 1e-3 for k in cuts)
                if len(c) <= 2 and dur_c < 0.8 and gap_ < S.get("orphan_gap", 0.35) and len(txt) <= S.get("orphan_chars", S.get("max_chars", 18) + 6):
                    m[-1] = p_ + c; continue
            m.append(c)
        ch = m
    for i, c in enumerate(ch):
        nxt = ch[i + 1][0]["t0"] if i + 1 < len(ch) else dur
        t1 = nxt if nxt - c[-1]["t1"] < 0.6 else c[-1]["t1"] + 0.3
        t1 = max(t1, min(nxt, c[0]["t0"] + S.get("min_dur", 0)))   # блок держится не меньше min_dur, но не наезжает на следующий
        acc_done = False; ws = []
        for w in c:
            a = (not acc_done) and is_acc(w)
            acc_done = acc_done or a
            ws.append({"text": w["w"], "t": round(max(w["t0"] - 0.03, 0), 3), "acc": a})
        subs.append({"t0": round(max(c[0]["t0"] - 0.03, 0), 3), "t1": round(min(t1, dur), 3), "words": ws})

    def T(ref, end=False, dt=0.0):
        g = G[ref]
        return round((g.get("t_end", g["t"]) if end else g["t"]) + dt, 3)

    ov = []
    for o in gfx["overlays"]:
        o = dict(o)
        for k in list(o.keys()):
            v = o[k]
            if isinstance(v, str) and v.startswith("@"):      # "@id" / "@id:end" / "@id:end+0.5" / "@cut1"
                m = re.match(r"@([\w]+)(:end)?([+-][\d.]+)?$", v)
                ref, end, dt = m.group(1), bool(m.group(2)), float(m.group(3) or 0)
                if ref.startswith("cut"):
                    o[k] = round(cuts[int(ref[3:])] + dt, 3)
                elif ref == "dur":
                    o[k] = round(dur + dt, 3)
                else:
                    o[k] = T(ref, end, dt)
        for lst in ("rows", "items"):
            for it in o.get(lst, []):
                for k, v in list(it.items()):
                    if isinstance(v, str) and v.startswith("@"):
                        m = re.match(r"@([\w]+)(:end)?([+-][\d.]+)?$", v)
                        it[k] = T(m.group(1), bool(m.group(2)), float(m.group(3) or 0))
        o["t1"] = min(o["t1"], dur)
        ov.append(o)

    # якорь серии — в паузах между верхними плашками
    TOP = ("bars", "spot", "bignum", "checklist", "endcard", "layout", "chart", "chips", "word", "report", "badge", "cards",
           "system", "windows", "days", "jug", "stage", "logos", "thirty", "hook")
    top = sorted((o["t0"] - 0.25, o["t1"] + 0.25) for o in ov if o["type"] in TOP)
    chip = gfx.get("chip")
    if chip:
        f = chip.get("from", 0.0)
        t = round(cuts[int(f[4:])], 3) if isinstance(f, str) else f
        for a, b in top + [(dur, dur)]:
            if a - t >= chip.get("min_gap", 3.0):
                ov.append({"type": "chip", "t0": round(t, 3), "t1": round(a, 3), "text": chip["text"]})
            t = max(t, b)

    sfx = []
    for b in tl.get("broll", []):
        sfx.append({"t": round(max(0, b["t0"] - 0.12), 3), "src": "media/whoosh.wav", "vol": 0.35})
    for o in ov:
        if o["type"] in ("bars", "lower", "bignum", "endcard", "checklist"):
            sfx.append({"t": o["t0"], "src": "media/pop.wav", "vol": 0.3})
        if o["type"] == "spot":
            sfx.append({"t": o["t0"], "src": "media/hit.wav", "vol": 0.45})
        for it in o.get("items", [])[1:]:
            sfx.append({"t": it["t"], "src": "media/pop.wav", "vol": 0.25})

    if gfx.get("auto_sfx") is False:      # все звуки задаются вручную в gfx["sfx"]
        sfx = []
    for x in gfx.get("sfx", []):          # звуки из сценария графики (время — число или @якорь)
        x = dict(x)
        if isinstance(x["t"], str):
            m = re.match(r"@([\w]+)(:end)?([+-][\d.]+)?$", x["t"]); x["t"] = T(m.group(1), bool(m.group(2)), float(m.group(3) or 0))
        sfx.append(x)
    # интервалы речи для дакинга музыки
    speech = []
    for w in words:
        if speech and w["t0"] - speech[-1][1] < 0.35:
            speech[-1][1] = w["t1"]
        else:
            speech.append([w["t0"], w["t1"]])
    props = {"duration": dur, "base": gfx["base"], "subs": subs, "overlays": ov, "sfx": sfx,
             "speech": [[round(a, 3), round(b, 3)] for a, b in speech]}
    for k in ("music", "nosubs"):
        if k in gfx:
            props[k] = gfx[k]
    if S.get("size"):
        props["subSize"] = S["size"]
    json.dump(props, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(f"props: {len(subs)} строк субтитров, {len(ov)} плашек, {len(sfx)} звуков, {dur:.1f} с -> {out_path}")

if __name__ == "__main__":
    main(*sys.argv[1:4])
