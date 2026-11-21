#!/usr/bin/env python3
"""PSOLA hedef konturunun 'doğallık' ayarı (ses üretmez; yalnız hedef eğrileri hesaplar).
yeni6/03_psola.py: hedef = basamak (hece notası) + hızlı bileşen; hızlı = log f0 - kayan ortanca(120 ms), +-50 sente kırpılmış.
Bu betik, doğal f0 (vokal_dogal.wav, Praat) üzerinde pencere ve kırpma değerlerini tarar ve hece içi f0 standart sapmasını
(sent) ve hecenin ortancasının hedeften kayışını verir. Kıyas: referans (doğal) hece içi ss ortancası ~20.6 sent; reddedilen 12.5 sent.
Çıktı: ara/09_kontur_ayari.json"""
import json, os, numpy as np
from ortak import *

Y, S, Z = yukle(); t, f0 = f0_izi(DOGAL_VOK, "dogal"); cik = []
gl = {}
for L in Y["lines"]:
    for h in L["syllables"]: gl[(L["verse"], L["line"], h["index"])] = bool(h.get("is_glide"))
print(" pencere_ms  kırpma_sent | hece içi ss ortanca (hepsi / kaymasız / kaymalı heceler) | ortanca kayışı |ortanca| sent")
for pen in (120, 200, 300, 450):
    for kirp in (50, 75, 100, 150):
        ss = []; ssk = []; ssg = []; kay = []
        for p in Y["pieces"]:
            m = (t >= p["dest_in"] - 0.06) & (t < p["dest_out"] + 0.06); tt = t[m]; ff = f0[m]; ses = ff > 0; lf = np.where(ses, np.log2(np.maximum(ff, 1e-6)), np.nan)
            w = int(pen / 5) | 1; yav = lf.copy()
            for i in np.where(ses)[0]: yav[i] = np.nanmedian(lf[max(0, i - w // 2):i + w // 2 + 1])
            hiz = np.clip(np.nan_to_num(lf - yav), -kirp / 1200, kirp / 1200)
            for s in S:
                if s["piece"] != p["id"]: continue
                k = (tt >= s["dest_start"]) & (tt < s["dest_end"]) & ses
                if k.sum() < 6: continue
                idx = np.where(k)[0]; a = int(len(idx) * 0.15); c = idx[a:len(idx) - a]; v = hiz[c] * 1200; ss.append(np.std(v)); kay.append(abs(np.median(hiz[idx]) * 1200))
                (ssg if gl[(s["verse"], s["line"], s["index"])] else ssk).append(np.std(v))
        d = {"pencere_ms": pen, "kirpma_sent": kirp, "ss_ortanca": round(float(np.median(ss)), 1), "ss_kaymasiz": round(float(np.median(ssk)), 1), "ss_kaymali": round(float(np.median(ssg)), 1), "ortanca_kayisi_sent": round(float(np.median(kay)), 1), "ortanca_kayisi_p90": round(float(np.percentile(kay, 90)), 1)}
        cik.append(d); print("   %4d        %4d     |   %5.1f / %5.1f / %5.1f   |  %4.1f (p90 %.1f)" % (pen, kirp, d["ss_ortanca"], d["ss_kaymasiz"], d["ss_kaymali"], d["ortanca_kayisi_sent"], d["ortanca_kayisi_p90"]))
json.dump(cik, open(os.path.join(ARA, "09_kontur_ayari.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
