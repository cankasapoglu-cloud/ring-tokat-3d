#!/usr/bin/env python3
"""ezgi_00c: bir zaman araliginda ozgun / beklenen / adaylarin f0'ini kare kare dok (yalniz okuma).
Kullanim: ezgi_00c_karsilastir.py <parca> <t0> <t1> [adim_ms]"""
import sys, os, numpy as np, soundfile as sf
import ezgi_ortak as o, ezgi_olcum as ol
cid, ta, tb = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
st = int(sys.argv[4]) if len(sys.argv) > 4 else 5
x, Y = o.oku()
c = [q for q in o.parcalar(Y) if q["id"] == cid][0]
sx, t, f0x, f0r, ncc, levx = o.parca_cozumle(x, c)
s = np.load(os.path.join(o.ARA, "egri_%s.npy" % cid.replace("+", "_")))
t0 = o.seg_zaman(c)
cols = {}
for ad in ("A_dunya_tam", "B_dunya_karma", "C_psola"):
    y, _ = sf.read(os.path.join(o.ARA, "aday_%s.wav" % ad), dtype="float64")
    sy = np.concatenate([np.zeros(o.PAD), y[c["a"]:c["b"]], np.zeros(o.PAD)])
    ty, f0y, levy = ol.harvest_onbellek(sy, ad)
    tp, pf, pv = ol.pyin_onbellek(sy, ad)
    cols[ad] = (f0y, levy, tp, pf, pv)
print("   t      ozgun  s(t)  beklenen | A harv  pyin | B harv  pyin  dzy | C harv  pyin  dzy | ozgun dzy ncc")
for i in range(0, len(t), st):
    tt = t[i] + t0
    if not (ta <= tt <= tb):
        continue
    k = int(round(t[i] * o.SR))
    mo = o.midi(f0x[i])
    row = "%8.3f %6s %+5.2f %6s  |" % (tt, "%.2f" % mo if f0x[i] > 0 else "--", s[k], "%.2f" % (mo + s[k]) if f0x[i] > 0 else "--")
    for ad in ("A_dunya_tam", "B_dunya_karma", "C_psola"):
        f0y, levy, tp, pf, pv = cols[ad]
        j = int(np.argmin(np.abs(tp - t[i])))
        row += " %6s %6s" % ("%.2f" % o.midi(f0y[i]) if f0y[i] > 0 else "--", "%.2f" % o.midi(pf[j]) if (pv[j] and np.isfinite(pf[j])) else "--")
        if ad != "A_dunya_tam":
            row += " %4d |" % levy[i]
        else:
            row += " |"
    row += " %4d %3d" % (levx[i], ncc[i] * 99)
    print(row)
