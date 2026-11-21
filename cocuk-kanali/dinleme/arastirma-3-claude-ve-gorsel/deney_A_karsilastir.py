#!/usr/bin/env python3
"""Deney A sonucu: Claude'un okumasi ile gizli dogru cevaplari karsilastirir."""
import json, os
B = os.path.dirname(os.path.abspath(__file__))
okuma = json.load(open(os.path.join(B, "deney-A-okunabilirlik", "claude_okumasi.json")))
ozet = {}
for boyut, o in okuma.items():
    t = json.load(open(os.path.join(B, "gizli", f"A_dogru_{boyut}.json")))
    print("==", boyut, "|", o["not"])
    oz = {"yazi": {}, "kayma": {}}
    for px, dogru in t["satirlar"].items():
        ok = sum(a == b for a, b in zip(dogru, o["satirlar"][px]))
        yanlis = [(a, b) for a, b in zip(dogru, o["satirlar"][px]) if a != b]
        oz["yazi"][px] = f"{ok}/8"
        print(f"  yazi {px:>2}px: {ok}/8 dogru", ("yanlislar (dogru,okunan): %s" % yanlis) if yanlis else "")
    grup = {}
    for k, off in t["kaymalar"].items():
        g = o["kaymalar"][k]
        sgn = lambda v: (v > 0) - (v < 0)
        a = grup.setdefault(abs(off), {"n": 0, "yon_dogru": 0, "tam_dogru": 0, "hata": []})
        a["n"] += 1
        a["yon_dogru"] += sgn(off) == sgn(g)
        a["tam_dogru"] += off == g
        if off != g: a["hata"].append((k, off, g))
    for m in sorted(grup):
        a = grup[m]
        oz["kayma"][str(m)] = {"n": a["n"], "yon_dogru": a["yon_dogru"], "tam_dogru": a["tam_dogru"]}
        print(f"  kayma |{m:>2}|px: n={a['n']} yon dogru={a['yon_dogru']} buyukluk tam dogru={a['tam_dogru']}  hatalar(hucre,dogru,okunan)={a['hata']}")
    ozet[boyut] = oz
json.dump(ozet, open(os.path.join(B, "deney-A-okunabilirlik", "sonuc.json"), "w"), indent=1)
