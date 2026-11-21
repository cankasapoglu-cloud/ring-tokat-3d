#!/usr/bin/env python3
"""Ikinci asama: elde GERCEK kanallari (kuru vokal + orkestra) olan iki reddedilmis kaydi, otomatik ayirma yerine o kanallarla
yeniden olcer. Amac: --ayir ile bulunan farkin ne kadari gercek, ne kadari ayirma (MDX) artigi?
  ali-baba__dogal_onizleme : vokal_dogal.wav (dinle_2'nin vokali, ISLENMEMIS) + altyapi_dogal + ezgi_alti_dogal, 116,015 BPM
  ali-baba__sarki_birlesik : yeni2/vokal.wav (ayni vokal, WORLD ile esnetilmis + perdesi ezgiye cekilmis) + altyapi.wav, 134 BPM
Gecici kanal dosyalari gecici klasore yazilir (depoya degil). Cikti: raporlar/<ad>__gercek_kanallar/"""
import os, sys, subprocess, json, time
import numpy as np, soundfile as sf
BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
from set import SET, KAL, KOK
GEC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/kal_gecici"
os.makedirs(GEC, exist_ok=True)
ad2 = {s["ad"]: s for s in SET}
db = lambda x: 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)

def kos(ad, vokal, altyapi, bpm, ilk):
    s = ad2[ad]
    cikti = s["cikti"] + "__gercek_kanallar"
    if os.path.exists(os.path.join(cikti, "rapor.json")):
        print("atlandi:", ad); return
    komut = [sys.executable, os.path.join(BURASI, "dinle_sarici.py"), s["tam_yol"], "--vokal", vokal, "--altyapi", altyapi, "--bpm", str(bpm), "--ilk-vurus", str(ilk),
             "--cikti", cikti, "--sozler", s["sozler_yol"]]
    t = time.time()
    with open(os.path.join(KAL, "gunluk", ad + "__gercek_kanallar.log"), "w") as g:
        r = subprocess.run(komut, stdout=subprocess.DEVNULL, stderr=g)
    print("%-40s cikis=%d %4.0f sn" % (ad + "__gercek_kanallar", r.returncode, time.time() - t), flush=True)

# --- dogal onizleme: orkestra = altyapi + ezgi alti; vokal duzeyi onizleme.py'deki kuralla (soylenen karelerde orkestra + 5 dB)
Y = os.path.join(KOK, "ali-baba", "yeni3")
b, fs = sf.read(os.path.join(Y, "altyapi", "altyapi_dogal.wav")); e, _ = sf.read(os.path.join(Y, "altyapi", "ezgi_alti_dogal.wav"))
v, fv = sf.read(os.path.join(Y, "vokal", "vokal_dogal.wav")); assert fs == fv
n = len(b); v = np.pad(v, (0, max(0, n - len(v))))[:n]
band = b + e
w = int(0.05 * fs); env = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1
gv = 10 ** ((db(band.mean(axis=1)[sesli]) + 5.0 - db(v[sesli])) / 20)
sf.write(os.path.join(GEC, "onizleme_vokal.wav"), v * gv, fs); sf.write(os.path.join(GEC, "onizleme_orkestra.wav"), band, fs)
print("onizleme: vokal kazanci %.1f dB" % (20 * np.log10(gv)), flush=True)
kos("ali-baba__dogal_onizleme", os.path.join(GEC, "onizleme_vokal.wav"), os.path.join(GEC, "onizleme_orkestra.wav"), 116.015, 0.0)
# --- sarki_birlesik
Y2 = os.path.join(KOK, "ali-baba", "yeni2")
v2, f2 = sf.read(os.path.join(Y2, "vokal.wav")); a2, f3 = sf.read(os.path.join(Y2, "altyapi.wav")); assert f2 == f3
sf.write(os.path.join(GEC, "birlesik_vokal.wav"), v2[:len(a2)], f2)
kos("ali-baba__sarki_birlesik", os.path.join(GEC, "birlesik_vokal.wav"), os.path.join(Y2, "altyapi.wav"), 134.0, 0.0)
