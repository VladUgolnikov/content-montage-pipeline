#!/usr/bin/env python3
"""Сценарии графики для 4 вариантов Манифеста (C095_m1..m4) по таймлайнам баз.
Все времена — из слов таймлайна (финальное время). python3 variants_gfx.py TL_DIR OUT_DIR"""
import json, sys, os

TL_DIR, OUT = sys.argv[1], sys.argv[2]
R = lambda x: round(x, 3)


def build(v):
    tl = json.load(open(os.path.join(TL_DIR, f"C095_{v}_timeline.json")))
    ws, cuts, dur = tl["words"], tl["cuts"], tl["duration"]
    low = [w["w"].lower() for w in ws]

    def W(text, after=-1.0, nxt=None):
        for i, w in enumerate(ws):
            if low[i] == text.lower() and w["t0"] > after and (nxt is None or (i + 1 < len(ws) and low[i + 1] == nxt)):
                return w
        raise KeyError(f"{v}: нет слова {text} после {after}")

    def cut_after(t):
        return min([c for c in cuts if c > t + 0.05] + [dur])

    def cut_before(t):
        return max(c for c in cuts if c <= t + 0.05)

    ov, sfx, nosubs, mutes = [], [], [], []
    # --- куски тела ---
    za = W("за"); vyr = W("выручка"); n15 = W("1,5"); prib = W("прибыль"); pros = W("просела"); n7 = W("7", prib["t0"])
    ah = W("АХ*ЕЛИ"); mute_t = ah["t0"] + 0.23; ah_end = cut_after(ah["t0"])
    chest = W("честно", nxt="очень"); mnog = W("многие"); mill = W("миллионы")
    ya = W("я", nxt="вот"); proizv = W("производства"); prod = W("продаваемую"); ross = W("России")
    n30 = W("30"); ofig = W("офигенных"); sov = W("советов"); sel = W("селлеру")
    kazh = W("каждом"); odn = W("одной"); skol = W("сколько"); prov = W("проверить"); ispr = W("исправить")
    kot = W("которая"); kontr = W("контролировать"); ut = W("утечки", kontr["t0"] - 0.01); marzh = W("маржи", kontr["t0"])
    sprint = W("спринт"); n100 = W("100"); posm = W("посмотрим"); perv = W("первая")

    num_start = cut_before(za["t0"]); num_end = cut_after(n7["t0"])

    def chart(t0, t1):
        ov.append({"type": "chart", "t0": R(t0), "t1": R(t1), "title": "За 2 года",
                   "rev": [R(vyr["t0"]), R(n15["t0"] + 0.06)], "prof": [R(prib["t0"]), R(n7["t0"] + 0.02)],
                   "revLabelT": R(n15["t0"]), "profLabelT": R(pros["t0"]), "divT": R(n7["t0"] - 0.08)})
        sfx.append({"t": R(n7["t0"] - 0.08), "src": "media/sfx_heartbeat_impact.mp3", "vol": 0.7})

    # --- хук ---
    if v == "m1":   # голос + заголовок: цифры
        ov.append({"type": "layout", "mode": "split", "t0": -0.5, "t1": R(num_end + 0.05)})
        ov.append({"type": "hook", "t0": 0, "t1": R(num_end), "top": 205, "lines": [
            {"text": "Выручка ×1,5", "size": 124, "t": R(n15["t0"])},
            {"text": "Прибыль ÷7", "red": True, "size": 176, "t": R(n7["t0"])}]})
        sfx.append({"t": R(n7["t0"] - 0.05), "src": "media/sfx_heartbeat_impact.mp3", "vol": 0.7})
        chip_from = num_end
    elif v == "m2":  # голос + заголовок: миллионы, потом цифры графиком
        ov.append({"type": "layout", "mode": "split", "t0": -0.5, "t1": R(num_end + 0.05)})
        c1 = cut_after(mill["t0"])
        ov.append({"type": "hook", "t0": 0, "t1": R(c1), "top": 225, "lines": [
            {"text": "Эти дыры обошлись", "size": 100},
            {"text": "мне в миллионы", "red": True, "size": 108, "t": R(mill["t0"])}]})
        sfx.append({"t": R(mill["t0"] - 0.03), "src": "media/sfx_heartbeat_impact.mp3", "vol": 0.6})
        chart(c1 - 0.1, num_end)
        chip_from = num_end
    elif v == "m3":  # только заголовок: молчаливый взгляд, голос со 2-й секунды
        ov.append({"type": "layout", "mode": "split", "t0": -0.5, "t1": R(num_end + 0.05)})
        ov.append({"type": "hook", "t0": 0, "t1": R(vyr["t0"] + 0.1), "top": 150, "lines": [
            {"text": "−12 000 000 ₽", "red": True, "size": 138},
            {"text": "за 2025 год.", "size": 100},
            {"text": "Ищу дыры", "size": 100}]})
        sfx.append({"t": 0.05, "src": "media/sfx_heartbeat_impact.mp3", "vol": 0.55})
        chart(vyr["t0"] - 0.15, num_end)
        chip_from = num_end
    else:            # m4: только голос — холодный старт на «АХ*ЕЛИ», без заголовка
        ov.append({"type": "zoom", "t0": 0.0, "t1": R(mute_t), "from": 1.0, "to": 1.08})
        ov.append({"type": "layout", "mode": "split", "t0": R(num_start), "t1": R(num_end + 0.05)})
        chart(num_start + 0.05, num_end)
        chip_from = num_end

    # --- АХ*ЕЛИ: слово на чёрном, звон, тишина ---
    ov.append({"type": "word", "t0": R(mute_t), "t1": R(ah_end), "text": "АХ*ЕЛИ"})
    sfx.append({"t": R(mute_t - 0.02), "src": "media/glass_mk.mp3", "vol": 0.9})
    nosubs.append([R(mute_t), R(ah_end)]); mutes.append([R(mute_t), R(ah_end)])

    # --- «многие стоили мне миллионы» — отчёт удержаний (кроме m2, где это хук) ---
    if v != "m2":
        m_end = cut_after(mill["t0"]); r0 = chest["t0"] - 0.05
        ov.append({"type": "layout", "mode": "split", "t0": R(cut_before(chest["t0"])), "t1": R(m_end)})
        rows = [("18.08–24.08", "2 102 568", "8 833.83"), ("25.08–31.08", "1 468 905", "21 540.10"), ("01.09–07.09", "2 931 740", "4 212.75"),
                ("08.09–14.09", "1 254 118", "17 905.40"), ("15.09–21.09", "2 407 351", "9 377.05")]
        ov.append({"type": "report", "t0": R(r0), "t1": R(m_end), "label": "Итого\nудержаний", "markT": R(mnog["t0"]), "totalT": R(mill["t0"]),
                   "rows": [{"week": a, "other": b, "fines": c, "t": R(r0 + 0.14 + 0.18 * i)} for i, (a, b, c) in enumerate(rows)]})
        sfx.append({"t": R(mnog["t0"]), "src": "media/sfx_scribble.mp3", "vol": 0.5})

    # --- кто я (сжато) ---
    ov.append({"type": "lower", "t0": R(ya["t0"] + 0.1), "t1": R(proizv["t1"] + 0.1), "name": "Влад Угольников", "role": "основатель ZUBRO"})
    ov.append({"type": "tag", "t0": R(prod["t0"]), "t1": R(cut_after(ross["t0"])), "text": "№1 в России", "y": 300})

    # --- 30 советов + кувшин ---
    th1 = sel["t0"] + 0.82
    ov.append({"type": "thirty", "t0": R(n30["t0"] - 0.13), "t1": R(th1), "t": R(n30["t0"]), "num": 30,
               "words": [{"text": "офигенных", "t": R(ofig["t0"])}, {"text": "советов", "t": R(sov["t0"])}, {"text": "селлеру", "t": R(sel["t0"])}]})
    nosubs.append([R(n30["t0"] - 0.1), R(th1 - 0.04)])
    j0 = th1 - 0.14
    ov.append({"type": "jug", "t0": R(j0), "t1": R(cut_after(sel["t0"] + 1.5))})
    sfx.append({"t": R(j0 + 0.35), "src": "media/sfx_papers.mp3", "vol": 0.5})

    # --- по одной утечке: карточки + чек-лист ---
    e0 = cut_before(kazh["t0"]); e1 = cut_after(ispr["t0"])
    ov.append({"type": "layout", "mode": "split", "t0": R(e0), "t1": R(e1)})
    ov.append({"type": "cards", "t0": R(e0 + 0.12), "t1": R(skol["t0"] - 0.3), "n": 5, "total": 30, "pickT": R(odn["t0"]), "y": 360, "s": 0.72})
    sfx.append({"t": R(e0 + 0.12), "src": "media/card_slide.ogg", "vol": 0.45})
    ov.append({"type": "checklist", "t0": R(skol["t0"] - 0.3), "t1": R(e1), "y": 170,
               "items": [{"text": "Цена вопроса", "t": R(skol["t0"])}, {"text": "Как проверить", "t": R(prov["t0"])}, {"text": "Как исправить", "t": R(ispr["t0"])}]})

    # --- система (после B-roll «а параллельно…системой») ---
    s1 = cut_after(marzh["t0"])
    ov.append({"type": "layout", "mode": "split", "t0": R(kot["t0"] - 0.1), "t1": R(s1)})
    ov.append({"type": "system", "t0": R(kot["t0"] - 0.05), "t1": R(s1), "center": "СИСТЕМА", "cx": 540, "cy": 330, "R": 300,
               "nodes": [{"text": "Утечки", "t": R(kontr["t0"])}, {"text": "Продажи", "t": R(ut["t0"])}, {"text": "Цифры", "t": R(marzh["t0"])}]})

    # --- спринт 100 дней ---
    d0 = cut_before(sprint["t0"])
    ov.append({"type": "layout", "mode": "split", "t0": R(d0), "t1": R(posm["t0"] + 0.1)})
    ov.append({"type": "days", "t0": R(d0 + 0.05), "t1": R(posm["t0"] + 0.1), "t": R(sprint["t0"]), "fillT": R(n100["t0"] + 0.2), "caption": "СПРИНТ ДО MVP"})
    sfx.append({"t": R(n100["t0"]), "src": "media/sfx_clock_tick.mp3", "vol": 0.6})
    ov.append({"type": "zoom", "t0": R(posm["t0"] + 0.1), "t1": R(cut_after(posm["t0"])), "from": 1.0, "to": 1.05})
    
    gfx = {"base": f"media/C095_{v}_base.mp4",
           "subs": {"max_chars": 36, "max_words": 6, "gap": 0.35, "min_dur": 1.2, "size": 72, "orphan_chars": 40},
           "chip": {"text": "100 ДНЕЙ", "from": R(chip_from), "min_gap": 2.0},
           "auto_sfx": False, "nosubs": nosubs,
           "music": {"src": "media/music_greed.mp3", "vol": 0.26, "duck": 0.11, "startFrom": 13.9, "mutes": mutes,
                     "fadeFrom": R(dur - 1.3), "fadeTo": R(dur)},
           "overlays": sorted(ov, key=lambda o: o["t0"]), "sfx": sorted(sfx, key=lambda x: x["t"])}
    json.dump(gfx, open(os.path.join(OUT, f"C095_{v}_gfx.json"), "w"), ensure_ascii=False, indent=1)
    print(v, f"{dur:.1f} с, плашек {len(ov)}, звуков {len(sfx)}")


for v in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["m1", "m2", "m3", "m4"]):
    build(v)
