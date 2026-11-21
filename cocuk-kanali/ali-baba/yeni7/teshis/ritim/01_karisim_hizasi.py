#!/usr/bin/env python3
"""Soru 1a: Bitmiş mp3'ün İÇİNDE vokal ile orkestra, tasarlanan yerde mi? (0.100 s dolgu, vokal zinciri, mp3 kodlayıcı gecikmesi)
Yöntem: mp3 çözülür; orkestra kökü (altyapi+ezgi) ve vokal kökü ile ayrı ayrı çapraz ilişki; iki gecikmenin FARKI = vokalin orkestraya göre kayması."""
import json, os, numpy as np
from scipy import signal
from ortak import *

km = mp3_coz(RED_MP3, os.path.join(ARA, "red.wav"))
band = oku_mono(RED_BAND) + oku_mono(RED_EZGI) * 10 ** (-4 / 20)
vok = oku_mono(RED_VOK)
sonuc = {}

def gecikme(mix, kok, t0, t1, kok_kaydirma=0.0, maxlag=0.25):
    a = mix[int(t0 * FS):int(t1 * FS)]; b0 = int((t0 - kok_kaydirma) * FS); b = kok[b0:b0 + len(a)]
    c = signal.fftconvolve(a, b[::-1], "full"); lags = np.arange(-len(b) + 1, len(a))
    m = np.abs(lags) <= int(maxlag * FS); i = np.argmax(np.abs(c[m])); l = lags[m][i]
    return l / FS * 1000, float(c[m][i] / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

# orkestra: yalnız orkestranın çaldığı giriş (0.1 - 9.2 s) ve bir cevap ölçüsü (vokalsiz); vokal: yüksek geçiren zincirden geçtiği için 300 Hz üstü
olc = []
for ad, t0, t1 in [("giris", 0.6, 9.0), ("kita4_cevap", ON + (4 + 8 * 3 + 1) * OLCU, ON + (4 + 8 * 3 + 2) * OLCU), ("bitis", 138.0, 145.0)]:
    l, r = gecikme(km, band, t0, t1, kok_kaydirma=ON); olc.append((ad, l, r))
sonuc["orkestra_mp3_icinde_gecikme_ms"] = [{"bolge": a, "gecikme_ms": round(l, 3), "iliski": round(r, 3)} for a, l, r in olc]
kv = bant(km, 300, 5000); vv = bant(vok, 300, 5000); olv = []
for k in range(7):
    for ad, o in (("L1", 0), ("L2", 2), ("L4", 6)):
        t0 = ON + (4 + 8 * k + o) * OLCU; l, r = gecikme(kv, vv, t0, t0 + OLCU, maxlag=0.25); olv.append((k + 1, ad, l, r))
sonuc["vokal_mp3_icinde_gecikme_ms"] = [{"kita": k, "satir": a, "gecikme_ms": round(l, 3), "iliski": round(r, 3)} for k, a, l, r in olv]
lo = np.median([l for _, l, _ in olc]); lv = np.array([l for *_, l, r in olv if abs(r) > 0.3])
sonuc["ozet"] = {"orkestra_gecikme_ortanca_ms": round(float(lo), 3), "vokal_gecikme_ortanca_ms": round(float(np.median(lv)), 3), "vokal_gecikme_min_ms": round(float(lv.min()), 3), "vokal_gecikme_max_ms": round(float(lv.max()), 3),
                  "vokal_eksi_orkestra_ms": round(float(np.median(lv) - lo), 3), "kullanilan_vokal_satiri": int(len(lv)),
                  "aciklama": "gecikme = mp3 içindeki konum - tasarlanan konum (orkestra = wav + 0.100 s; vokal = vokal_psola.wav zamanı). vokal_eksi_orkestra 0 ise karışım hiçbir kayma eklememiştir."}
json.dump(sonuc, open(os.path.join(ARA, "01_karisim_hizasi.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(sonuc["ozet"], ensure_ascii=False, indent=1)); print(sonuc["orkestra_mp3_icinde_gecikme_ms"]); print([(d["kita"], d["satir"], d["gecikme_ms"], d["iliski"]) for d in sonuc["vokal_mp3_icinde_gecikme_ms"]])
