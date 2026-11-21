#!/usr/bin/env python3
"""ezgi_00d: 'otumsuz' sayilip ozgun perdesinde KOPYALANAN ama yuksek duzeyli ve yari donemsel kareler
(kaydirilan heceler icinde). Bunlar kisa sureli eski-perde kalintisi olabilir. Yalniz okuma."""
import os, json, numpy as np
import ezgi_ortak as o
x, Y = o.oku()
plan = json.load(open(os.path.join(o.ARA, "egri.json"), encoding="utf8"))
pc = {c["id"]: c for c in plan["chunks"]}
tot = 0.0; rows = []
for c in o.parcalar(Y):
    seg, t, f0, f0r, ncc, lev = o.parca_cozumle(x, c)
    s = np.load(os.path.join(o.ARA, "egri_%s.npy" % c["id"].replace("+", "_")))
    t0 = o.seg_zaman(c)
    sk = s[np.clip(np.round(t * o.SR).astype(int), 0, len(s) - 1)]
    bad = (f0 == 0) & (lev > -25.0) & (np.abs(sk) >= 1.0)
    i = 0
    while i < len(t):
        if bad[i]:
            j = i
            while j < len(t) and bad[j]:
                j += 1
            if j - i >= 8:
                seln = slice(i, j)
                rows.append((c["id"], t[i] + t0, (j - i), float(lev[seln].max()), float(np.median(ncc[seln])), float(np.mean(f0r[seln] > 0)), float(np.median(sk[seln]))))
                tot += (j - i)
            i = j
        else:
            i += 1
print("kaydirilan bolgelerde, > -25 dBFS, otumsuz sayilan (kopyalanan) kesimler (>= 8 ms): %d adet, toplam %.0f ms" % (len(rows), tot))
for r in sorted(rows, key=lambda r: -r[2])[:40]:
    print("  %-8s t=%.3f  %3d ms  en yuksek %.0f dBFS  ortanca ncc %.2f  harvest sesli orani %.2f  kaydirma %+.1f" % r)
