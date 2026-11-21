#!/usr/bin/env python3
"""Kesif (yalniz okur): bu sarkicinin OTUMSUZ unsuzden sonra gelen l / otumlu baslangiclarinin dogal yukselme suresi.
Amac: 3. kita onariminda sustained /l/ icine girilen giris gecisinin (fade-in) uzunlugunu olcume dayandirmak.
Olcu: 100-1000 Hz bandinin 3 ms RMS zarfi; otum baslangicindan sonraki 70 ms icindeki 15-35 ms sonraki duzeye gore %10 -> %90 genlik yukselme suresi.
Yukseltilmis kosinus gecis F icin %10-%90 genlik suresi = 0.59 F."""
import sys, os, json, numpy as np, scipy.signal as ss
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *

x = oku_vokal()
K = oku_json(KESIM)
S = lambda t: int(round(t * SR))
sos = ss.butter(4, [100, 1000], btype="band", fs=SR, output="sos")
e = zarf(ss.sosfiltfilt(sos, x), 3)
rows = []
for V_ in K["verses"]:
    for Ln in V_["lines"]:
        sy = Ln["syllables"]
        for i, h in enumerate(sy[:-1]):
            eb = h.get("end_boundary") or {}
            if eb.get("where") != "voicing_onset" or not sy[i + 1]["kept"] or h.get("excise"):
                continue
            t = eb["t"]
            # dayanak duzey: otum baslangicindan 15-35 ms sonraki (l / unlu basi) zarfin medyani
            ref = float(np.median(e[S(t + 0.015):S(t + 0.035)]))
            a = S(t - 0.030)
            seg = e[a:S(t + 0.040)]
            i90 = next((j for j in range(len(seg)) if seg[j] >= 0.9 * ref and np.all(seg[j:j + S(0.003)] >= 0.7 * ref)), None)
            if i90 is None:
                continue
            i10 = i90
            while i10 > 0 and seg[i10] >= 0.1 * ref:
                i10 -= 1
            if seg[i10] >= 0.1 * ref:
                continue                      # onceki ses bu bantta yeterince alcak degil: olculemez
            m, pk = ref, i90
            rows.append(dict(verse=V_["verse"], line=Ln["name"], pair=h["text"] + "|" + sy[i + 1]["text"], t=t, peak_dbfs=round(db(m), 1),
                             rise_10_90_ms=round((i90 - i10) / SR * 1000, 1), level_at_t_db_re_peak=round(db(e[S(t)] / m), 1)))
r = np.array([q["rise_10_90_ms"] for q in rows])
for q in rows:
    print("K%d %-4s %-9s t=%.4f tepe %.1f dBFS  yukselme %%10-%%90 = %5.1f ms" % (q["verse"], q["line"], q["pair"], q["t"], q["peak_dbfs"], q["rise_10_90_ms"]))
print("n=%d  medyan %.1f ms, ceyrekler %.1f / %.1f, en kisa %.1f, en uzun %.1f" % (len(r), np.median(r), np.percentile(r, 25), np.percentile(r, 75), r.min(), r.max()))
print("esdeger yukseltilmis kosinus uzunlugu (yukselme / 0.59): medyan %.1f ms, ceyrekler %.1f / %.1f" % (np.median(r) / 0.59, np.percentile(r, 25) / 0.59, np.percentile(r, 75) / 0.59))
os.makedirs(ARA, exist_ok=True)
json.dump(dict(rows=rows, median_ms=float(np.median(r)), q25_ms=float(np.percentile(r, 25)), q75_ms=float(np.percentile(r, 75)),
               equivalent_raised_cosine_ms=dict(median=float(np.median(r) / 0.59), q25=float(np.percentile(r, 25) / 0.59), q75=float(np.percentile(r, 75) / 0.59))),
          open(os.path.join(ARA, "dogal_baslangic.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
