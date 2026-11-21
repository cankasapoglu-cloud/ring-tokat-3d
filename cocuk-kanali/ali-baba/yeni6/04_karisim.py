#!/usr/bin/env python3
"""Karışım: Old MacDonald orkestrası (yeni4/altyapi/altyapi_G.wav, 105 vuruş/dk, Sol majör) + vokalin altında çalan hafif ezgi
(ezgi_alti_G.wav) + ezgiyi söyleyen vokal + gerçek hayvan sesleri (kıtanın 3. ve 4. ölçüsünün başında).
Kullanım: python3 04_karisim.py <vokal wav> <çıktı mp3>"""
import os, subprocess, sys, numpy as np, soundfile as sf
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.dirname(D); Y4 = os.path.join(A, "yeni4")
VOK, CIK = sys.argv[1], sys.argv[2]; ON, B = 0.100, 240 / 105.0
b, fs = sf.read(os.path.join(Y4, "altyapi", "altyapi_G.wav")); e, _ = sf.read(os.path.join(Y4, "altyapi", "ezgi_alti_G.wav")); v, fv = sf.read(VOK); assert fs == fv == 44100
pad = np.zeros((int(ON * fs), 2)); band = np.concatenate([pad, b]); ezgi = np.concatenate([pad, e]) * 10 ** (-4 / 20)
n = max(len(band), len(v)); band = np.pad(band, ((0, n - len(band)), (0, 0))); ezgi = np.pad(ezgi, ((0, n - len(ezgi)), (0, 0))); v = np.pad(v, (0, n - len(v)))
db = lambda x: 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)
w = int(0.05 * fs); env = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1
zemin = (band + ezgi).mean(axis=1)
hay = np.zeros((n, 2)); SIRA = ["inek", "koyun", "at", "horoz", "ordek", "kopek", "kedi"]
for k in range(7):
    ob = [ON + (4 + 8 * k + i) * B for i in range(9)]
    for j, t in enumerate((ob[3], ob[4])):
        s, _ = sf.read(os.path.join(A, "yeni3", "ses", f"{SIRA[k]}_{j + 1}.wav")); s = s if s.ndim == 1 else s.mean(axis=1)
        ev = np.sqrt(np.convolve(s ** 2, np.ones(w) / w, "same")); yuk = ev > ev.max() * 10 ** (-10 / 20)
        g = min(10 ** ((-12.5 - db(s[yuk])) / 20), 1.0 / np.abs(s).max()); p = int((t - 0.04) * fs); hay[p:p + len(s)] += (s * g)[:, None]
T = os.path.join(D, "_"); sf.write(T + "v0.wav", v, fs, subtype="FLOAT")
# vokal zinciri (yüksek geçiren, hafif sıkıştırma, kısa yankı) ayrı uygulanır; düzey ZİNCİRDEN SONRA ölçülüp ayarlanır
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", T + "v0.wav", "-af",
                "highpass=f=130,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120:makeup=1,aecho=1.0:1.0:38:0.14", "-c:a", "pcm_f32le", T + "v1.wav"], check=True)
vz, _ = sf.read(T + "v1.wav"); vz = np.pad(vz, (0, max(0, n - len(vz))))[:n]
HEDEF = float(os.environ.get("VOKAL_USTU_DB", "8.5"))                     # söylenen karelerde vokal, orkestranın bu kadar dB üstünde
gv = 10 ** ((db(zemin[sesli]) + HEDEF - db(vz[sesli])) / 20); vz = vz * gv
print("zincir sonrası vokal %.1f dB, orkestra %.1f dB (söylenen karelerde)" % (db(vz[sesli]), db(zemin[sesli])))
sf.write(T + "b.wav", band + ezgi, fs, subtype="FLOAT"); sf.write(T + "v.wav", np.stack([vz, vz], axis=1), fs, subtype="FLOAT"); sf.write(T + "h.wav", hay, fs, subtype="FLOAT")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", T + "b.wav", "-i", T + "v.wav", "-i", T + "h.wav", "-filter_complex",
                "[0:a][1:a][2:a]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.89:attack=5:release=60:level=disabled,volume=-4.1dB[o]",
                "-map", "[o]", "-ar", "44100", "-b:a", "192k", CIK], check=True)
# denetim: bitmiş mp3'te vokal gerçekten duyulur düzeyde mi?
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", CIK, T + "k.wav"], check=True); km, _ = sf.read(T + "k.wav"); km = km.mean(axis=1)[:n]
print("bitmiş karışım: söylenen karelerde %.1f dB, vokalsiz (cevap) ölçülerinde %.1f dB; vokal ile ilişki %.2f" % (
    db(km[sesli[:len(km)]]), db(km[int((ON + 5 * B) * fs):int((ON + 6 * B) * fs)]), np.corrcoef(km[sesli[:len(km)]], vz[:len(km)][sesli[:len(km)]])[0, 1]))
for x in ("v0", "v1", "k"): os.unlink(T + x + ".wav")
for x in "bvh": os.unlink(T + x + ".wav")
print(CIK, "vokal kazancı %.1f dB" % (20 * np.log10(gv)))
