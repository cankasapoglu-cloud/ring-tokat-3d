#!/usr/bin/env python3
"""Deney B, duzeltilmis sayisal olcum. Ilk surumdeki 'giris_farki_ms' HATALIYDI
(arama penceresi onceki notayi yakaliyordu; butun notalar -295 ms cikti). Bu hatayi
tablo degil RESIM ele verdi. Burada giris zamani, bagimsiz bir baslangic (onset)
dedektorunden alinip hedefe en yakin olanla eslestirilir.
Kullanim: python3 deney_B_olcum_v2.py <ad> <tekrar>"""
import os, sys, json
os.environ.setdefault("OMP_NUM_THREADS", "2"); os.environ.setdefault("NUMBA_NUM_THREADS", "2")
import numpy as np, librosa
AD, TEKRAR = sys.argv[1], int(sys.argv[2])
B = os.path.dirname(os.path.abspath(__file__))
BEAT = 0.6
DIZE = [("C4",1),("C4",1),("G4",1),("G4",1),("A4",1),("A4",1),("G4",2),("F4",1),("F4",1),("E4",1),("E4",1),("D4",1),("D4",1),("C4",2)]
notalar = []; t = 0.5
for r in range(TEKRAR):
    for n, v in DIZE:
        notalar.append((len(notalar) + 1, n, float(librosa.note_to_midi(n)), t, v * BEAT * 0.92)); t += v * BEAT
y, sr = librosa.load(os.path.join(B, "deney-B-ezgi-hata", f"{AD}.wav"), sr=None)
HOP = 256
fo, vf, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C3"), fmax=librosa.note_to_hz("C6"), sr=sr, frame_length=2048, hop_length=HOP)
tz = librosa.times_like(fo, sr=sr, hop_length=HOP); midi = librosa.hz_to_midi(fo)
rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=HOP)[0]; db = 20 * np.log10(rms + 1e-6)
sesli = (db > db.max() - 30) & vf
# baslangiclar: duzey egrisinin dipten yukari gectigi anlar (esik: tepe-9 dB), dedektorden bagimsiz basit kural
ust = db > db.max() - 9
bas = tz[1:][(~ust[:-1]) & ust[1:]]
olcum = []
for i, n, m, a, sure in notalar:
    k = {"i": i, "nota": n, "hedef_bas": round(a, 2)}
    k["sesli_oran"] = round(float(np.mean(sesli[(tz >= a) & (tz <= a + sure)])), 2)
    ic = (tz >= a + 0.10) & (tz <= a + sure - 0.06) & sesli
    if ic.sum() >= 5:
        sap = (midi[ic] - m) * 100
        k["medyan_sapma_cent"] = round(float(np.nanmedian(sap)), 1); k["perde_oynakligi_cent_std"] = round(float(np.nanstd(sap)), 1)
    else:
        k["medyan_sapma_cent"] = None; k["perde_oynakligi_cent_std"] = None
    yakin = bas[np.abs(bas - a) <= 0.25]
    k["giris_farki_ms"] = int(round(float(yakin[np.argmin(np.abs(yakin - a))] - a) * 1000)) if len(yakin) else None
    olcum.append(k)
json.dump(olcum, open(os.path.join(B, "deney-B-ezgi-hata", f"{AD}_olcum.json"), "w"), ensure_ascii=False, indent=1)
print(AD, "olcum v2 yazildi;", "giris farklari(ms):", [k["giris_farki_ms"] for k in olcum])
