#!/usr/bin/env python3
"""On dinlemenin 'gercek kanal' olcumunde vokal neden dinle_2'dekinden daha daginik perdeli cikti? Ayni sarkicinin dort hali:
  a) aracin dinle_2'den ayirdigi vokal (MDX, onbellek)      b) ali-baba/dinle_2_vokal.wav (eski ayirma; on dinlemenin kaynagi)
  c) yeni3/vokal/vokal_dogal.wav (kaynagin yerlestirilmis hali) d) c x 4,7 dB kazanc, 16 bit WAV'a yazilmis (kirpilma var mi?)
Olcu: aracin kendi perde izleyicisi + nota bolucusu; perdenin yarim ses izgarasina yapisma R'si (izgara kaymasindan bagimsiz) ve nota ici oynaklik."""
import os, sys, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
import numpy as np, soundfile as sf
import dinle_olcum as o
GEC = sys.argv[1]
A_ = os.path.join(KOK, "ali-baba")
s2 = [x for x in SET if x["ad"] == "ali-baba__dinle_2"][0]
mdx = glob.glob(os.path.join(o.ONBELLEK_BUYUK, o.dosya_ozeti(s2["tam_yol"])[:16], "ham", "*(Vocals)*.wav"))[0]
dosyalar = [("a) aracin MDX vokali (dinle_2)", mdx), ("b) dinle_2_vokal.wav (eski ayirma)", os.path.join(A_, "dinle_2_vokal.wav")),
            ("c) vokal_dogal.wav (yerlestirilmis)", os.path.join(A_, "yeni3", "vokal", "vokal_dogal.wav")), ("d) c x kazanc, 16 bit (2. asamada kullanilan)", os.path.join(GEC, "onizleme_vokal.wav"))]
C = {}
for ad, yol in dosyalar:
    x, sr = o.ses_coz(yol)
    ham, hsr = sf.read(yol)
    kirp = float((np.abs(ham) >= 0.999).mean())
    v = o.tek_kanal(x, sr)
    t, hz, guven, sesli, f0b = o.f0_izle(v)
    midi = 69 + 12 * np.log2(np.where(hz > 0, hz, 440.0) / 440.0)
    notalar = o.notalara_bol(t, midi, sesli)
    cek = np.concatenate([n["cekirdek"] for n in notalar])
    sap = (midi[cek] - np.round(midi[cek])) * 100
    z_ = np.exp(2j * np.pi * sap / 100.0).mean()
    merkez = float(np.angle(z_) / (2 * np.pi) * 100)
    kalan = (sap - merkez + 50) % 100 - 50
    uz = [n["ic_std_cent"] for n in notalar if n["sure"] >= 0.2]
    C[ad] = {"dosya": os.path.relpath(yol, KOK) if yol.startswith(KOK) else os.path.basename(yol), "ornekleme_hz": int(hsr), "tam_olcek_ornek_orani": round(kirp, 5), "nota": len(notalar),
             "izgara_R": round(float(abs(z_)), 2), "akort_merkezi_cent": round(merkez, 1), "merkeze_gore_medyan_sapma_cent": round(float(np.median(np.abs(kalan))), 1),
             "yuzde_25cent_icinde_merkeze_gore": round(100 * float((np.abs(kalan) < 25).mean()), 1), "nota_ici_oynaklik_cent": round(float(np.median(uz)), 1) if uz else None,
             "medyan_hz": round(float(np.median(hz[sesli])), 1), "pyin_uyum": f0b.get("pyin_ile_uyum_yuzde_50cent"), "sesli_cerceve_orani": f0b.get("sesli_cerceve_orani")}
    print(ad, C[ad], flush=True)
json.dump(C, open(os.path.join(KAL, "ara", "vokal_perde_karsilastirma.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
