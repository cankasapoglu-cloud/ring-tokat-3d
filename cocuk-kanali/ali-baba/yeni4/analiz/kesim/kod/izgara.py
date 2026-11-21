#!/usr/bin/env python3
"""2. adim: VURUS IZGARASI SABLONU ile hece cekirdeklerinin (unlulerin) bulunmasi.

yeni3'te bu is icin kayittan kendi kendine egitilen bir harf-HMM'i (hizala.py) kullanilmisti. v2_2'de ayni HMM
denendi ve "çiftliğinde" ile tek gecen hayvan kelimelerinde guvenilmez cikti (unluyu komsu genizsiye / patlamaya
kaydirdi). v2_2'nin ise yeni3'teki kayitta olmayan bir ozelligi var: tempo.json'a gore sarki 105.000 BPM'lik
kesin bir makine izgarasinda ve her hece on altilik izgaraya oturuyor. Bu yuzden hece CEKIRDEKLERI izgaradan
beklenen yerlerin yakininda aranir; hece SINIRLARI yine yalniz sesten bulunur (kesim.py).

Sablon (kita ilk vurusundan itibaren VURUS cinsinden, unlunun basladigi yer):
  L1   : A 0 | li 0.5 | Ba 1 | ba 1.25 | nın 1.5 | bir 2 | çift 2.5 | li 3 | ği 3.25 | var 3.5
  L2   : çift 4 | li 4.5 | ğin 5 | de 5.5 | hayvan kelimesi 6, 6.5, 7, 7.25 (3 heceli "kedisi": 6, 6.5, 7) | var 7.5
  diye : di 10 | ye 10.5 | ba 11 | ğı 11.25 | rır 11.5
  L4   : çift 12 | li 12.5 | ğin 13 | de 13.5 | A 14 | li 14.5 | Ba 15 | ba 15.25 | nın 15.5
Sablon 1. kitanin izlerinden okundu ve 7 kitanin hepsinde olculen unlu baslangiclariyla dogrulanir
(`python3 izgara.py` sapma tablosunu yazdirir; kesim.json -> grid_check)."""
import json, os, numpy as np
from ortak import (A, K, BOLUM, SAKLANAN, kelimeleri_oku, kitalari_esle, kucuk, hecele, UNLU, SOYLENEN, ozellik, tempo_oku)

LAT = json.load(open(os.path.join(A, "yeni4", "analiz", "tempo", "lattice.json")))
BEAT_OLC = float(LAT["beat_period_s"])        # mp3 uzerinde olculen vurus suresi (0.5714133 s)

SABLON = {
    "L1": [0, 0.5, 1, 1.25, 1.5, 2, 2.5, 3, 3.25, 3.5],
    "L2_on": [4, 4.5, 5, 5.5],
    "L2_hayvan": {4: [6, 6.5, 7, 7.25], 3: [6, 6.5, 7]},
    "L2_var": [7.5],
    "diye": [10, 10.5, 11, 11.25, 11.5],
    "L4": [12, 12.5, 13, 13.5, 14, 14.5, 15, 15.25, 15.5],
}


def hece_yapisi(soz):
    """Kelimeyi hecelere ve her heceyi (onset harfleri, unlu, koda harfleri) parcalarina ayirir."""
    out = []
    for h in hecele(soz):
        hk = kucuk(h)
        vi = [j for j, ch in enumerate(hk) if ch in UNLU]
        assert len(vi) == 1, (soz, h)
        out.append({"text": h, "onset": hk[:vi[0]], "vowel": hk[vi[0]], "coda": hk[vi[0] + 1:]})
    return out


def kita_heceleri(kita, v, vurus):
    """v. kitanin saklanan bolumlerindeki heceler, beklenen unlu baslangiciyla (s).
    3. kitanin hayvan kelimesi SOYLENDIGI gibi (ortak.SOYLENEN) hecelenir."""
    out = {}
    for ad in SAKLANAN:
        heceler = []
        if ad == "L2":
            vur = list(SABLON["L2_on"])
            hay = SOYLENEN.get(v, kita[v]["L2"][1]["soz"])
            nh = len(hecele(hay))
            vur += SABLON["L2_hayvan"][nh] + SABLON["L2_var"]
        else:
            vur = SABLON[ad]
        i = 0
        for j, q in enumerate(kita[v][ad]):
            soz = q["soz"]
            if ad == "L2" and j == 1:
                soz = SOYLENEN.get(v, soz)
            for hi, h in enumerate(hece_yapisi(soz)):
                h = dict(h)
                h.update({"bolum": ad, "word_i": j, "word": q["soz"], "word_sung": soz, "syl_i": hi, "q": q,
                          "beat": vur[i], "t_exp": vurus + vur[i] * BEAT_OLC})
                heceler.append(h); i += 1
        assert i == len(vur), (v + 1, ad, i, len(vur))
        out[ad] = heceler
    return out
