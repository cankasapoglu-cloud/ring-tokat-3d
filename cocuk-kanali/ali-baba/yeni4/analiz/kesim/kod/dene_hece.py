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
for v in range(7):
    H = kita_heceleri(kita, v, vd[v])
    for adlar in (["L1"], ["L2"], ["diye", "L4"]):
        hs = [h for ad in adlar for h in H[ad]]
        bas = DZ[v][adlar[0]]["baslangic"]; bit = DZ[v][adlar[-1]]["bitis"]
        sin = hece.parca_sinirlari(hs, bas, bit)
        print("K%d %s" % (v + 1, "+".join(adlar)))
        for h in hs:
            eb = h["end_boundary"]
            print("   %-5s exp %.3f nuc %.3f core %.3f-%.3f (%+4.0f ms) | %.3f-%.3f %3.0f ms | %s" % (
                h["text"], h["t_exp"], h["nuc"], h["cs"], h["ce"], (h["cs"] - h["t_exp"]) * 1000, h["start"], h["end"], (h["end"] - h["start"]) * 1000,
                "" if eb is None else "%s %s/%s d=%s" % (eb["consonants"], eb["kind"], eb["where"], eb.get("depth_db"))))
