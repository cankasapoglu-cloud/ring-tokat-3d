#!/usr/bin/env python3
"""Ön dinleme karışımı (doğal sürüm): altyapi_dogal + ezgi_alti_dogal + vokal_dogal + hayvan sesleri.
Ajan ekibinin denetimli karışımı bitmeden kullanıcıya dinletmek için; düzeyler ölçülerek ayarlanır."""
import json, os, subprocess, numpy as np, soundfile as sf
Y = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); O = os.path.join(Y, "onizleme")
z = json.load(open(os.path.join(Y, "altyapi", "zaman_dogal.json"), encoding="utf8"))
b, fs = sf.read(os.path.join(Y, "altyapi", "altyapi_dogal.wav")); e, _ = sf.read(os.path.join(Y, "altyapi", "ezgi_alti_dogal.wav"))
v, fv = sf.read(os.path.join(Y, "vokal", "vokal_dogal.wav")); assert fs == fv == 44100
n = len(b); v = np.pad(v, (0, max(0, n - len(v))))[:n]
band = b + e
db = lambda x: 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)
# vokal düzeyi: söylenen karelerde vokal RMS = orkestra RMS + 5 dB
w = int(0.05 * fs); env = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1
gv = 10 ** ((db(band.mean(axis=1)[sesli]) + 5.0 - db(v[sesli])) / 20)
print("vokal kazancı %.2f dB (vokal %.1f dB, orkestra %.1f dB)" % (20 * np.log10(gv), db(v[sesli]), db(band.mean(axis=1)[sesli])))
sf.write(os.path.join(O, "_vokal.wav"), v * gv, fs)
# hayvan sesleri: kıta ö6 ve ö7 başından 40 ms önce; boşluk ölçülerindeki orkestranın 11 dB üstü
hay = np.zeros((n, 2)); SIRA = ["inek", "koyun", "at", "horoz", "ordek", "kopek", "kedi"]; rapor = []
for k, kita in enumerate(z["kitalar"]):
    ob = kita["olcu_baslangiclari"]; bit = kita["bitis"]
    slot = band[int(ob[6] * fs):int(bit * fs)].mean(axis=1)
    for j, t in enumerate((ob[6], ob[7])):
        s, f2 = sf.read(os.path.join(Y, "ses", f"{SIRA[k]}_{j + 1}.wav")); assert f2 == fs
        s = s if s.ndim == 1 else s.mean(axis=1)
        ev = np.sqrt(np.convolve(s ** 2, np.ones(w) / w, "same")); yuk = ev > ev.max() * 10 ** (-10 / 20)
        g = 10 ** ((db(slot) + 11.0 - db(s[yuk])) / 20); g = min(g, 0.95 / np.abs(s).max())
        p = int((t - 0.04) * fs); hay[p:p + len(s)] += (s * g)[:, None]
        rapor.append((SIRA[k], j + 1, round(t - 0.04, 2), round(len(s) / fs, 2), round(20 * np.log10(g), 1), round(db((s * g)[yuk]) - db(slot), 1)))
        assert p + len(s) < (z["kitalar"][k + 1]["baslangic"] if k < 6 else z["bitis"]["baslangic"]) * fs + 0.05 * fs or j == 0, (SIRA[k], "sonraki kıtaya taşıyor")
sf.write(os.path.join(O, "_hayvan.wav"), hay, fs)
for r in rapor: print(r)
cikti = os.path.join(O, "ali-baba-dogal-onizleme.mp3")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(Y, "altyapi", "altyapi_dogal.wav"), "-i", os.path.join(Y, "altyapi", "ezgi_alti_dogal.wav"),
                "-i", os.path.join(O, "_vokal.wav"), "-i", os.path.join(O, "_hayvan.wav"), "-filter_complex",
                "[2:a]highpass=f=130,acompressor=threshold=-18dB:ratio=2.5:attack=8:release=120:makeup=1,aecho=0.8:0.4:35:0.12,pan=stereo|c0=c0|c1=c0[v];"
                "[0:a][1:a][v][3:a]amix=inputs=4:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[o]",
                "-map", "[o]", "-ar", "44100", "-b:a", "192k", cikti], check=True)
print(cikti)
