#!/usr/bin/env python3
"""ezgi_00e: adaylarin HARMONIK genliklerinin ozgunun tayf zarfina (cheaptrick) uyumu (yalniz okuma).
Kaydirilan hecelerin cekirdek karelerinde, 4 kHz'e kadar her harmonik icin:
  sapma = cikti harmonik genligi (dB) - ozgun zarfin o frekanstaki degeri (dB)   (kare basina ortalamasi cikarilir)
  zikzak = ardisik harmoniklerin ikinci farki / 2 (dB)  -> tarak / hayalet darbe izi
Cikti: ezgi_ara/harmonik.json"""
import os, json, sys, numpy as np, soundfile as sf, pyworld as pw, librosa
import ezgi_ortak as o, ezgi_olcum as ol
x, Y = o.oku()
plan = json.load(open(os.path.join(o.ARA, "egri.json"), encoding="utf8"))
pc = {c["id"]: c for c in plan["chunks"]}
adlar = sys.argv[1:] or ["A_dunya_tam", "B_dunya_karma", "C_psola"]
NF = 2048
win = np.hanning(NF)
fr = np.arange(NF // 2 + 1) * o.SR / NF
def harm(sig, k, f0, fmax=4000.0):
    a = k - NF // 2
    if a < 0 or a + NF > len(sig):
        return None
    S = np.abs(np.fft.rfft(sig[a:a + NF] * win))
    out = []
    nh = int(fmax / f0)
    for h in range(1, nh + 1):
        lo, hi = np.searchsorted(fr, (h - 0.25) * f0), np.searchsorted(fr, (h + 0.25) * f0)
        out.append(S[lo:hi + 1].max())
    return np.array(out)
res = {}
for ad in adlar:
    y, _ = sf.read(os.path.join(o.ARA, "aday_%s.wav" % ad), dtype="float64")
    rows = []
    for c in o.parcalar(Y):
        sx, t, f0x, _, _, levx = o.parca_cozumle(x, c)
        sy = np.concatenate([np.zeros(o.PAD), y[c["a"]:c["b"]], np.zeros(o.PAD)])
        ty, f0y, levy = ol.harvest_onbellek(sy, ad)
        t0 = o.seg_zaman(c)
        fx5 = np.ascontiguousarray(f0x[::5]); fy5 = np.ascontiguousarray(f0y[::5]); t5 = np.ascontiguousarray(t[::5])
        spx = pw.cheaptrick(sx, fx5, t5, o.SR)
        fenv = np.arange(spx.shape[1]) * o.SR / (2 * (spx.shape[1] - 1))
        for h in pc[c["id"]]["syllables"]:
            if abs(h["shift"]) <= o.KOPYA_ESIK:
                continue
            m = min(0.03, 0.2 * (h["core_end"] - h["core_start"]))
            idx = np.where((t5 >= h["core_start"] - t0 + m) & (t5 < h["core_end"] - t0 - m) & (fx5 > 0) & (fy5 > 0))[0]
            dv, zz, zzo, h1, lv = [], [], [], [], []
            for i in idx:
                k = int(round(t5[i] * o.SR))
                A = harm(sy, k, fy5[i]); Ao = harm(sx, k, fx5[i])
                if A is None or Ao is None or len(A) < 4:
                    continue
                a_db = 20 * np.log10(A + 1e-12)
                e_db = 10 * np.log10(np.interp(np.arange(1, len(A) + 1) * fy5[i], fenv, spx[i]) + 1e-20)
                d = a_db - e_db
                d = d - d.mean()
                dv.append(np.sqrt(np.mean(d ** 2))); h1.append(d[0])
                zz.append(np.mean(np.abs(a_db[:-2] - 2 * a_db[1:-1] + a_db[2:])) / 2)
                ao_db = 20 * np.log10(Ao + 1e-12)
                zzo.append(np.mean(np.abs(ao_db[:-2] - 2 * ao_db[1:-1] + ao_db[2:])) / 2)
            if len(dv) >= 2:
                rows.append(dict(verse=h["verse"], line=h["line"], text=h["text"], shift=h["shift"], dev=float(np.mean(dv)), h1=float(np.mean(h1)),
                                 zig=float(np.mean(zz)), zig_orig=float(np.mean(zzo))))
    cls = (("L4 (+7)", lambda h: h["line"] == 4), ("L3 (+3)", lambda h: h["line"] == 3),
           ("L1/L2 up", lambda h: h["line"] in (1, 2) and h["shift"] > 0), ("L1/L2 down", lambda h: h["line"] in (1, 2) and h["shift"] < 0), ("all", lambda h: True))
    res[ad] = {}
    print("==", ad)
    for nm, fn in cls:
        hh = [r for r in rows if fn(r)]
        res[ad][nm] = dict(n=len(hh), harmonic_dev_from_original_envelope_db=round(float(np.mean([r["dev"] for r in hh])), 2),
                           fundamental_dev_db=round(float(np.mean([r["h1"] for r in hh])), 2),
                           zigzag_db=round(float(np.mean([r["zig"] for r in hh])), 2), zigzag_original_db=round(float(np.mean([r["zig_orig"] for r in hh])), 2))
        print("  %-11s n=%3d  harmonik sapma %.2f dB | temel (H1) sapmasi %+.2f dB | zikzak %.2f dB (ozgun kendi harmoniklerinde %.2f)" % (
            nm, len(hh), res[ad][nm]["harmonic_dev_from_original_envelope_db"], res[ad][nm]["fundamental_dev_db"], res[ad][nm]["zigzag_db"], res[ad][nm]["zigzag_original_db"]))
json.dump(res, open(os.path.join(o.ARA, "harmonik.json"), "w"), indent=1)
