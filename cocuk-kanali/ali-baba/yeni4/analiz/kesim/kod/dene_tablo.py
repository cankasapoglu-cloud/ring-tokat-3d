"""Tani araci (ciktiya girmez): hece cekirdekleri ve sinirlarinin dokumu / 7 kitanin yan yana tablosu."""
import numpy as np, sys
import hece
from zarf import *
from ortak import *
from izgara import kita_heceleri, BEAT_OLC
from dize import dizeleri_bul
kita = kitalari_esle(kelimeleri_oku()); vd = kita_vuruslari()
DZ, SEV = dizeleri_bul(kita)
hece.SUNG = SEV["soylenen_rms_dbfs"]
voi = np.interp(t, th, (f0h > 0).astype(float)) > 0.5
hece.VOIG = voi & (ELOW8 > hece.SUNG - 11.0)          # kesim.py ile ayni kapi
K = {"dip": "d", "spectral": "s", "pitch_step": "p", "grid": "G"}
for adlar in (["L1"], ["L2"], ["diye", "L4"]):
    rows = []
    for v in range(7):
        H = kita_heceleri(kita, v, vd[v])
        hs = [h for ad in adlar for h in H[ad]]
        hece.parca_sinirlari(hs, DZ[v][adlar[0]]["baslangic"], DZ[v][adlar[-1]]["bitis"])
        rows.append(hs)
    print("==", "+".join(adlar), ": sinirin sonraki hecenin beklenen unlu baslangicina gore yeri (ms) ve turu; alt satir: hece suresi (ms)")
    for v, hs in enumerate(rows):
        print("K%d " % (v + 1) + " ".join("%4s|%-4s%+4.0f%s" % (h["text"][:4], hs[i + 1]["text"][:4], (h["end"] - hs[i + 1]["t_exp"]) * 1000, K[h["end_boundary"]["kind"]]) for i, h in enumerate(hs[:-1])))
        print("    " + " ".join("%13.0f " % ((h["end"] - h["start"]) * 1000) for h in hs))
