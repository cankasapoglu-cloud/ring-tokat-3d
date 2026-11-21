#!/usr/bin/env python3
"""Perdeyi Praat'ın PSOLA (overlap-add) yöntemiyle hedef notalara çeker: zaman düzleminde çalıştığı için sesin tınısını
vokoderden daha iyi korur. Kullanım: python3 03_psola.py <girdi wav> <çıktı wav>   (hedefler.json'daki hece hedefleri)."""
import json, os, sys, numpy as np, soundfile as sf, pyworld as pw, parselmouth
from parselmouth.praat import call
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.dirname(D)
GIR, CIK = sys.argv[1], sys.argv[2]
Y = json.load(open(os.path.join(A, "yeni4", "vokal", "yerlesim.json"), encoding="utf8")); H = json.load(open(os.path.join(D, "hedefler.json"), encoding="utf8"))
x, fs = sf.read(GIR); x = x.astype(np.float64); cikti = np.zeros_like(x); FP = 5.0; tablo = []
for p in Y["pieces"]:
    a, b = int((p["dest_in"] - 0.06) * fs), int((p["dest_out"] + 0.06) * fs); seg = x[a:b]
    f0, t = pw.harvest(seg, fs, f0_floor=150, f0_ceil=720, frame_period=FP); f0 = pw.stonemask(seg, f0, t, fs)
    ta = t + a / fs; sesli = f0 > 0; lf = np.where(sesli, np.log2(np.maximum(f0, 1e-6)), np.nan)
    w = int(0.12 / (FP / 1000)) | 1; yavas = lf.copy()
    for i in np.where(sesli)[0]: yavas[i] = np.nanmedian(lf[max(0, i - w // 2):i + w // 2 + 1])
    hizli = np.clip(np.nan_to_num(lf - yavas), -0.5 / 12, 0.5 / 12)
    hs = [h for h in H if h["piece"] == p["id"]]; basamak = np.full(len(f0), np.nan)
    for h in hs:
        m = (ta >= h["dest_start"]) & (ta < h["dest_end"]); basamak[m] = np.log2(440.0 * 2 ** ((h["hedef_midi"] - 69) / 12))
    idx = np.where(~np.isnan(basamak))[0]; basamak = np.interp(np.arange(len(basamak)), idx, basamak[idx])
    cek = np.hanning(11); cek /= cek.sum(); basamak = np.convolve(np.pad(basamak, 5, "edge"), cek, "valid")
    hedef = 2 ** (basamak + hizli)
    snd = parselmouth.Sound(seg, sampling_frequency=fs)
    man = call(snd, "To Manipulation", 0.005, 150, 720)
    pt = call(man, "Extract pitch tier"); call(pt, "Remove points between", 0, snd.duration)
    for i in np.where(sesli)[0]: call(pt, "Add point", float(t[i]), float(hedef[i]))
    call([pt, man], "Replace pitch tier")
    y = call(man, "Get resynthesis (overlap-add)").values[0]; y = np.pad(y, (0, max(0, len(seg) - len(y))))[:len(seg)]
    y *= np.sqrt(np.mean(seg ** 2) / (np.mean(y ** 2) + 1e-12))
    r = int(0.02 * fs); y[:r] *= np.linspace(0, 1, r); y[-r:] *= np.linspace(1, 0, r)
    cikti[a:a + len(y)] += y
    f1, t1 = pw.harvest(y, fs, f0_floor=150, f0_ceil=720, frame_period=FP); t1 = t1 + a / fs
    for h in hs:
        m = (t1 >= h["dest_start"]) & (t1 < h["dest_end"]) & (f1 > 0)
        if m.sum() > 3: tablo.append((69 + 12 * np.log2(np.median(f1[m]) / 440) - h["hedef_midi"]) * 100)
sf.write(CIK, cikti, fs, subtype="PCM_24")
e = np.abs(np.array(tablo)); print("%s -> %s | hece %d | hedeften |sapma|: ortanca %.0f, %%90 %.0f, en çok %.0f sent; 50 sentten fazla %d" % (os.path.basename(GIR), os.path.basename(CIK), len(e), np.median(e), np.percentile(e, 90), e.max(), (e > 50).sum()))
