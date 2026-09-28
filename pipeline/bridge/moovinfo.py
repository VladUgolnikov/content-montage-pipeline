#!/usr/bin/env python3
"""Читает только индекс MOV/MP4 (moov): по каждой дорожке — timescale, число сэмплов, длительность по таймстемпам,
edit list и «дыры» в видео (кадры с длительностью больше нормы = пропущенные камерой кадры, с их временем).
  python3 bridge/moovinfo.py FILE [FILE ...]"""
import struct, sys, os

def boxes(f, start, end):
    pos = start
    while pos < end - 8:
        f.seek(pos); hdr = f.read(8)
        if len(hdr) < 8: return
        size, typ = struct.unpack(">I4s", hdr); hl = 8
        if size == 1: size = struct.unpack(">Q", f.read(8))[0]; hl = 16
        elif size == 0: size = end - pos
        yield typ.decode("latin1"), pos + hl, pos + size
        pos += size

def find(f, s, e, path):
    for t, a, b in boxes(f, s, e):
        if t == path[0]:
            return (a, b) if len(path) == 1 else find(f, a, b, path[1:])
    return None

def analyse(fn):
    size = os.path.getsize(fn)
    with open(fn, "rb") as f:
        mv = find(f, 0, size, ["moov"])
        if not mv: print(fn, "moov не найден"); return
        print(f"== {os.path.basename(fn)}")
        for t, a, b in boxes(f, *mv):
            if t != "trak": continue
            md = find(f, a, b, ["mdia"]); hd = find(f, *md, ["hdlr"]); f.seek(hd[0] + 8); kind = f.read(4).decode("latin1")
            mh = find(f, *md, ["mdhd"]); f.seek(mh[0]); ver = f.read(1)[0]
            f.seek(mh[0] + (20 if ver == 1 else 12)); ts = struct.unpack(">I", f.read(4))[0]
            st = find(f, *md, ["minf", "stbl", "stts"]); f.seek(st[0] + 4); n = struct.unpack(">I", f.read(4))[0]
            ent = [struct.unpack(">II", f.read(8)) for _ in range(n)]
            tot = sum(c * d for c, d in ent); cnt = sum(c for c, _ in ent)
            el = find(f, a, b, ["edts", "elst"]); els = []
            if el:
                f.seek(el[0]); ver = f.read(1)[0]; f.read(3); ne = struct.unpack(">I", f.read(4))[0]
                for _ in range(ne):
                    if ver == 1: d, mt = struct.unpack(">Qq", f.read(16))
                    else: d, mt = struct.unpack(">Ii", f.read(8))
                    f.read(4); els.append((d, mt))
            print(f" [{kind}] timescale {ts}, сэмплов {cnt}, длина по таймстемпам {tot/ts:.3f} с, записей stts {n}, elst {els}")
            if kind == "vide":
                from collections import Counter
                dist = Counter()
                for c, d in ent: dist[d] += c
                norm = dist.most_common(1)[0][0]
                print(f"   длительности кадров (тики:кол-во): {dict(dist.most_common(8))}; норма {norm} = {ts/norm:.3f} fps")
                t = 0; gaps = []
                for c, d in ent:
                    if d != norm:
                        for i in range(c): gaps.append((t + i * d, d))
                    t += c * d
                # кластеры нерегулярных кадров (≠ норма): время, число кадров, сумма отклонения от нормы
                cl = []
                for x, d in gaps:
                    if cl and x / ts - cl[-1][1] < 2.0:
                        cl[-1][1] = x / ts; cl[-1][2] += 1; cl[-1][3] += (d - norm) / ts
                    else:
                        cl.append([x / ts, x / ts, 1, (d - norm) / ts])
                print(f"   кластеры нерегулярных кадров ({len(cl)}): " + "; ".join(f"{a:.1f}-{b:.1f}с n{n} {s*1000:+.0f}мс" for a, b, n, s in cl))
                big = [(x / ts, d / ts) for x, d in gaps if d > norm * 1.5]
                small = sum(1 for x, d in gaps if d < norm)
                print(f"   кадров длиннее нормы ×1.5: {len(big)}, суммарно лишнего {sum(d - norm/ts for _, d in big):.3f} с; короче нормы: {small}")
                if big:
                    print("   первые/последние дыры (время с, длина с):", [(round(x, 2), round(d, 3)) for x, d in big[:12]], "...",
                          [(round(x, 2), round(d, 3)) for x, d in big[-6:]])
                    # накопленный сдвиг по минутам
                    acc = 0; rows = []; bi = 0; step = 60
                    for m in range(0, int(tot / ts) + step, step):
                        while bi < len(big) and big[bi][0] < m:
                            acc += big[bi][1] - norm / ts; bi += 1
                        rows.append(f"{m//60}м:{acc:.2f}")
                    print("   накоплено дыр к минуте:", " ".join(rows))

for fn in sys.argv[1:]:
    try: analyse(fn)
    except Exception as e: print(fn, "ошибка", e)
