#!/usr/bin/env python3
"""YARDIMCI DENEY (aracin parcasi degil): soylenen hayvan sesi hecesindeki UNLUNUN tinisi olculebilir mi?
Soru: dokum 'koyun: me me' yaziyor ama kullanici 'koyun mo diyor' diyor. Ayni kayitta inegin 'mo'su ile koyunun hecesi
ayni unlu mu? Yontem: ayrilmis vokal kanalinda, Scribe'in verdigi hece zamanlarinda, sesli cercevelerin perdeden arindirilmis
spektrum zarfi (pyworld CheapTrick) -> F1/F2 tepe tahmini + 1200-1800 / 1800-2800 Hz bant farki. 'o' (yuvarlak): F2 ~1500-1700,
'e' (duz): F2 ~1900-2300 (kadin sesinde). Kucuk ornek, ayrilmis kanal: KANIT DEGIL, ipucu.
Cikti: ara/unlu_tinisi.json"""
import os, sys, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
import numpy as np, soundfile as sf, pyworld as pw, librosa
import dinle_olcum as o

def vokal_kanali(yol):
    oz = o.dosya_ozeti(yol)[:16]
    v = glob.glob(os.path.join(o.ONBELLEK_BUYUK, oz, "ham", "*(Vocals)*.wav"))
    return v[0] if v else None

def zarf(x, sr, t0, t1):
    a, b = int(max(0, t0 - 0.02) * sr), int((t1 + 0.02) * sr)
    y = np.ascontiguousarray(x[a:b], dtype=np.float64)
    if len(y) < sr * 0.08:
        return None
    f0, tt = pw.harvest(y, sr, f0_floor=120.0, f0_ceil=900.0, frame_period=5.0)
    sp = pw.cheaptrick(y, f0, tt, sr)
    en = 10 * np.log10(sp.sum(axis=1) + 1e-12)
    m = (f0 > 0) & (en > en.max() - 15)
    if m.sum() < 6:
        return None
    frek = np.linspace(0, sr / 2, sp.shape[1])
    L = 10 * np.log10(sp[m] + 1e-12).mean(axis=0)
    return frek, L, float(np.median(f0[m])), int(m.sum())

def ozet(frek, L):
    def bant(a, b):
        return float(L[(frek >= a) & (frek < b)].mean())
    def tepe(a, b):
        mm = (frek >= a) & (frek < b)
        return float(frek[mm][np.argmax(L[mm])])
    ys = L - np.convolve(L, np.ones(9) / 9, "same") * 0
    return {"F1_tepe_hz": round(tepe(250, 1000)), "F2_tepe_hz": round(tepe(1000, 2900)), "bant_1800_2800_eksi_1200_1800_db": round(bant(1800, 2800) - bant(1200, 1800), 1),
            "bant_2000_3000_eksi_500_1500_db": round(bant(2000, 3000) - bant(500, 1500), 1)}

def profil(frek, L):
    mel = librosa.filters.mel(sr=int(frek[-1] * 2), n_fft=(len(frek) - 1) * 2, n_mels=24, fmin=250, fmax=3500)
    p = np.log(mel @ (10 ** (L / 10)) + 1e-12)
    return p - p.mean()

C = {}
D = json.load(open(os.path.join(KAL, "ara", "soz_denetimi.json"), encoding="utf8"))
for ad in sys.argv[1:] or ["ali-baba__v2_2", "ali-baba__coskulu_1", "ali-baba__coskulu_2"]:
    s = [x for x in SET if x["ad"] == ad][0]
    vy = vokal_kanali(s["tam_yol"])
    if not vy:
        print(ad, "vokal kanali yok (once dinle.py --ayir)"); continue
    x, sr = sf.read(vy)
    x = x.mean(axis=1) if x.ndim > 1 else x
    soz, olay, kaynak, ham = dokum(s)
    kit = D[ad]["kitalar"]
    sat = []
    for k in kit:
        if not k.get("ses_zamani"):
            continue
        heceler = [w for w in soz if k["ses_zamani"][0] - 0.01 <= w["bas"] <= k["ses_zamani"][1]]
        for w in heceler:
            z_ = zarf(x, sr, w["bas"], w["son"])
            if z_ is None:
                continue
            frek, L, f0m, n = z_
            sat.append({"hayvan": k["hayvan"], "dokumdeki_hece": w["metin"].strip('".,“” '), "bas": round(w["bas"], 2), "son": round(w["son"], 2), "f0_hz": round(f0m), "cerceve": n,
                        **ozet(frek, L), "_p": profil(frek, L)})
    # ayni kayitta inegin 'mo' heceleriyle benzerlik (zarf profili iliskisi)
    inek = [r["_p"] for r in sat if r["hayvan"] == "inek"]
    for r in sat:
        r["inek_mo_profiline_benzerlik"] = round(float(np.mean([np.corrcoef(r["_p"], q)[0, 1] for q in inek])), 2) if inek and r["hayvan"] != "inek" else None
    for r in sat:
        r.pop("_p")
    C[ad] = sat
    print("==", ad)
    for r in sat:
        print("   %-6s %-6s %6.2f-%6.2f f0=%3d  F1~%4d F2~%4d  bant(1.8-2.8k eksi 1.2-1.8k)=%+5.1f dB  inek'e benzerlik=%s" % (
            r["hayvan"], r["dokumdeki_hece"], r["bas"], r["son"], r["f0_hz"], r["F1_tepe_hz"], r["F2_tepe_hz"], r["bant_1800_2800_eksi_1200_1800_db"], r["inek_mo_profiline_benzerlik"]))
eski = {}
yol = os.path.join(KAL, "ara", "unlu_tinisi.json")
if os.path.exists(yol):
    eski = json.load(open(yol, encoding="utf8"))
eski.update(C)
json.dump(eski, open(yol, "w", encoding="utf8"), ensure_ascii=False, indent=1)
