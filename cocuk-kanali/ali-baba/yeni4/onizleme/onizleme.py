#!/usr/bin/env python3
"""Ön dinleme (doğal sürüm, düz armoni): altyapi_C (0,100 sn geciktirilerek) + vokal_dogal + gerçek hayvan sesleri.
Ekibin armonisi uyarlanmış ve denetlenmiş karışımı bitmeden hızlı dinleme/karşılaştırma için."""
import os, subprocess, numpy as np, soundfile as sf
Y = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); A = os.path.dirname(Y); O = os.path.join(Y, "onizleme")
ON, B = 0.100, 240 / 105.0
b, fs = sf.read(os.path.join(Y, "altyapi", "altyapi_C.wav")); v, fv = sf.read(os.path.join(Y, "vokal", "vokal_dogal.wav")); assert fs == fv == 44100
band = np.concatenate([np.zeros((int(ON * fs), 2)), b]); n = max(len(band), len(v))
band = np.pad(band, ((0, n - len(band)), (0, 0))); v = np.pad(v, (0, n - len(v)))
db = lambda x: 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)
w = int(0.05 * fs); env = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1
gv = 10 ** ((db(band.mean(axis=1)[sesli]) + 5.0 - db(v[sesli])) / 20)
print("vokal kazancı %.2f dB" % (20 * np.log10(gv)))
sf.write(os.path.join(O, "_band.wav"), band, fs); sf.write(os.path.join(O, "_vokal.wav"), v * gv, fs)
hay = np.zeros((n, 2)); SIRA = ["inek", "koyun", "at", "horoz", "ordek", "kopek", "kedi"]
for k in range(7):
    ob = [ON + (4 + 8 * k + i) * B for i in range(9)]
    slot = band[int(ob[3] * fs):int(ob[5] * fs)].mean(axis=1)
    for j, t in enumerate((ob[3], ob[4])):
        s, f2 = sf.read(os.path.join(A, "yeni3", "ses", f"{SIRA[k]}_{j + 1}.wav")); s = s if s.ndim == 1 else s.mean(axis=1)
        ev = np.sqrt(np.convolve(s ** 2, np.ones(w) / w, "same")); yuk = ev > ev.max() * 10 ** (-10 / 20)
        g = min(10 ** ((db(slot) + 11.0 - db(s[yuk])) / 20), 0.95 / np.abs(s).max())
        p = int((t - 0.04) * fs); hay[p:p + len(s)] += (s * g)[:, None]
        assert p + len(s) < (ob[5] + 2 * 60 / 105.0) * fs, (SIRA[k], "diye bağırır'a taşıyor")
sf.write(os.path.join(O, "_hayvan.wav"), hay, fs)
cikti = os.path.join(O, "ali-baba-ilk-ses-onizleme.mp3")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(O, "_band.wav"), "-i", os.path.join(O, "_vokal.wav"), "-i", os.path.join(O, "_hayvan.wav"),
                "-filter_complex", "[1:a]highpass=f=130,acompressor=threshold=-18dB:ratio=2.5:attack=8:release=120:makeup=1,aecho=0.8:0.4:35:0.12,pan=stereo|c0=c0|c1=c0[v];"
                "[0:a][v][2:a]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[o]", "-map", "[o]", "-ar", "44100", "-b:a", "192k", cikti], check=True)
for f in ("_band.wav", "_vokal.wav", "_hayvan.wav"): os.unlink(os.path.join(O, f))
print(cikti)
