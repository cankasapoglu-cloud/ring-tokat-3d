#!/usr/bin/env python3
"""YARDIMCI DENEY (aracin parcasi degil): 'Turkce konusan Ingiliz gibi' yargisinin olculebilir bir izi var mi?
Alti Parmak Ailesi kaydi AYNI sozleri soyluyor; bu yuzden ayni sozcukler kayitlar arasinda karsilastirilabilir.
Denenen fonetik izler (ayrilmis vokal kanali + dokumdeki sozcuk zamanlari, pyworld CheapTrick spektrum zarfi):
  1) 'parmak' sozcugunde Ingiliz 'r'si: dil kivrilarak soylenen r, ucuncu formanti (F3) ~1,6-2,0 kHz'e indirir. Vekil: sozcugun
     ilk %20-65'lik bolumunde (a-r) 1,4-2,1 kHz bandinin 2,3-3,3 kHz bandina ustunlugu (dB), en yuksek %10'luk cerceveler.
  2) 'buradayim' sonundaki 'i' (ı): Turkce'de art damak (F2 dusuk, ~1,3-1,6 kHz); Ingiliz agzinda 'i'ye kayar (F2 ~2,0-2,5 kHz).
     Vekil: sozcugun son %25-40'lik unlu bolumunde 1,8-2,8 kHz eksi 1,2-1,8 kHz (dB).
  3) sozcuk suresi duzeni: 'buradayim' / 'neredesin' / 'merhaba' sozcuk surelerinin degiskenligi.
n=2 (aksanli) ve n=4 (digerleri), sesler farkli sarkicilar: sonuc en fazla IPUCU olabilir.  Cikti: ara/aksan_deneyi.json"""
import os, sys, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
import numpy as np, soundfile as sf, pyworld as pw
import dinle_olcum as o

def vokal_kanali(yol):
    oz = o.dosya_ozeti(yol)[:16]
    v = glob.glob(os.path.join(o.ONBELLEK_BUYUK, oz, "ham", "*(Vocals)*.wav"))
    return v[0] if v else None

def cerceveler(x, sr, t0, t1):
    a, b = int(max(0, t0 - 0.03) * sr), int((t1 + 0.03) * sr)
    y = np.ascontiguousarray(x[a:b], dtype=np.float64)
    if len(y) < sr * 0.12:
        return None
    f0, tt = pw.harvest(y, sr, f0_floor=120.0, f0_ceil=900.0, frame_period=5.0)
    sp = pw.cheaptrick(y, f0, tt, sr)
    frek = np.linspace(0, sr / 2, sp.shape[1])
    L = 10 * np.log10(sp + 1e-12)
    en = 10 * np.log10(sp[:, frek < 5000].sum(axis=1) + 1e-12)
    rel = (tt - 0.03) / max(1e-3, (t1 - t0))                    # 0..1 sozcuk ici konum
    def bant(a_, b_):
        return L[:, (frek >= a_) & (frek < b_)].mean(axis=1)
    return {"rel": rel, "sesli": (f0 > 0) & (en > en.max() - 12), "f0": f0, "r_vekil": bant(1400, 2100) - bant(2300, 3300), "on_art": bant(1800, 2800) - bant(1200, 1800)}

HEDEF = ["parmak-ailesi__coskulu_1", "parmak-ailesi__duzgun_1", "parmak-ailesi__duzgun_2", "parmak-ailesi__turkce_2", "parmak-ailesi__yavas_2", "parmak-ailesi__sarki_2"]
C = {}
for ad in HEDEF:
    s = [x for x in SET if x["ad"] == ad][0]
    vy = vokal_kanali(s["tam_yol"])
    if not vy:
        print(ad, "vokal kanali yok"); continue
    x, sr = sf.read(vy)
    x = x.mean(axis=1) if x.ndim > 1 else x
    soz, _, kaynak, _ = dokum(s)
    r_list, i_list, f0s = [], [], []
    sure = {"buradayım": [], "neredesin": [], "merhaba": [], "parmak": []}
    for w in soz:
        n = w["normal"]
        if n in sure:
            sure[n].append(w["son"] - w["bas"])
        if n == "parmak" and 0.25 <= w["son"] - w["bas"] <= 1.6:
            c = cerceveler(x, sr, w["bas"], w["son"])
            if c is None: continue
            m = c["sesli"] & (c["rel"] >= 0.20) & (c["rel"] <= 0.65)
            if m.sum() >= 6:
                r_list.append(float(np.percentile(c["r_vekil"][m], 90)) - float(np.median(c["r_vekil"][c["sesli"]])))
                f0s.append(float(np.median(c["f0"][c["sesli"]])))
        if n == "buradayım" and 0.35 <= w["son"] - w["bas"] <= 2.5:
            c = cerceveler(x, sr, w["bas"], w["son"])
            if c is None: continue
            m = c["sesli"] & (c["rel"] >= 0.62) & (c["rel"] <= 0.85)
            if m.sum() >= 5:
                i_list.append(float(np.median(c["on_art"][m])))
    def oz(v):
        v = np.array(v, float)
        return {"n": int(len(v)), "medyan": round(float(np.median(v)), 1), "p25": round(float(np.percentile(v, 25)), 1), "p75": round(float(np.percentile(v, 75)), 1)} if len(v) else None
    C[ad] = {"karar": s["karar"], "gerekce": s["gerekce"], "dokum": kaynak, "vokal_f0_medyan_hz": round(float(np.median(f0s))) if f0s else None,
             "parmak_r_vekili_db": oz(r_list), "buradayim_son_unlu_on_art_db": oz(i_list),
             "sozcuk_suresi_sn": {k: (round(float(np.median(v)), 2), round(float(np.std(v) / (np.mean(v) + 1e-9)), 2), len(v)) for k, v in sure.items() if v}}
    print("%-28s %-8s f0~%s  parmak-r %s   buradayim-i %s   sure(medyan,cv,n) %s" % (ad, s["karar"], C[ad]["vokal_f0_medyan_hz"], C[ad]["parmak_r_vekili_db"], C[ad]["buradayim_son_unlu_on_art_db"], C[ad]["sozcuk_suresi_sn"]))
json.dump(C, open(os.path.join(KAL, "ara", "aksan_deneyi.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
