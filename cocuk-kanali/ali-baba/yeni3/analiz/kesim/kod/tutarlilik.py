#!/usr/bin/env python3
"""Tekrarlanan dizelerde (L1, L4, 'Çiftliğinde', 'nasıl') hece surelerinin 7 kita arasindaki tutarliligi.
Ayni sozler 7 kez soylendigi icin sureler benzer olmali; ortancadan cok sapan hece = olasi sinir hatasi."""
import os, json, sys, numpy as np
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
kj = os.path.join(K, "kesim.json")
d = json.load(open(kj, encoding="utf8"))


def tablo(ad, secici):
    rows = []
    for v in d["verses"]:
        rows.append(secici(v))
    n = len(rows[0]); ad_ = [s["text"] for s in rows[0]]
    D = np.array([[s["end"] - s["start"] for s in r] for r in rows]) * 1000
    O = np.array([[s["start"] - r[0]["start"] for s in r] for r in rows]) * 1000
    M = np.array([[s["f0_midi"] if s["f0_midi"] is not None else np.nan for s in r] for r in rows])
    med = np.median(D, 0)
    print("\n== %s: hece sureleri (ms) ==" % ad)
    print("      " + " ".join("%6s" % a for a in ad_))
    for i, r in enumerate(D):
        print("K%d    " % (i + 1) + " ".join(("%5.0f%s" % (x, "*" if abs(x - m) > max(45, 0.35 * m) else " ")) for x, m in zip(r, med)))
    print("ort.  " + " ".join("%5.0f " % x for x in med))
    print("-- baslangic (dize basina gore, ms) --")
    for i, r in enumerate(O):
        print("K%d    " % (i + 1) + " ".join("%5.0f " % x for x in r))
    print("-- cekirdek perdesi (MIDI) --")
    for i, r in enumerate(M):
        print("K%d    " % (i + 1) + " ".join("%6.2f" % x for x in r))
    return int((np.abs(D - med) > np.maximum(45, 0.35 * med)).sum())


n = 0
n += tablo("L1", lambda v: v["lines"][0]["syllables"])
n += tablo("L2 'Çiftliğinde'", lambda v: v["lines"][1]["syllables"][:4])
n += tablo("L2 son 'var'", lambda v: v["lines"][1]["syllables"][-1:])
n += tablo("L3 'nasıl'", lambda v: [s for s in v["lines"][2]["syllables"] if s["word"] == "nasıl"])
n += tablo("L4", lambda v: v["lines"][3]["syllables"])
print("\nortancadan cok sapan hece sayisi (*):", n)
