#!/usr/bin/env python3
"""Deneme: konuşma sesini (TTS) ezgiye oturtur. Her heceyi notasının süresine uzatır/kısaltır,
perdesini notaya sabitler (WORLD vokoder). Çıktı: vokal/kita1_ham.wav (altyapıyla aynı zaman çizgisi)."""
import json, os, numpy as np, soundfile as sf, pyworld as pw
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # vokal/
Y = os.path.dirname(D)
z = json.load(open(os.path.join(Y, "zaman.json"), encoding="utf8"))
notalar = z["kitalar"][0]["notalar"]
x, fs = sf.read(os.path.join(D, "tts_kita1.wav")); x = x.astype(np.float64)
SATIR = [(1, 0.0, 2.40), (2, 2.92, 5.11), ("diye", 5.56, 6.52), (3, 7.02, len(x) / fs)]   # TTS içindeki dize aralıkları
FP = 5.0                                                                  # ms
UNLU = set("aeıioöuüAEIİOÖUÜ")
toplam = int((z["kitalar"][1]["baslangic"] + 0.5) * fs)
cikti = np.zeros(toplam)
rapor = []
for satir, a, b in SATIR:
    seg = x[int(a * fs):int(b * fs)]
    # baştaki/sondaki sessizliği at
    e = np.convolve(seg ** 2, np.ones(441) / 441, "same"); es = e > e.max() * 0.004
    i0, i1 = np.argmax(es), len(es) - np.argmax(es[::-1]); seg = seg[max(0, i0 - 220):i1 + 220]
    f0, t = pw.harvest(seg, fs, f0_floor=90, f0_ceil=500, frame_period=FP)
    sp = pw.cheaptrick(seg, f0, t, fs); ap = pw.d4c(seg, f0, t, fs)
    N = len(f0)
    ns = [n for n in notalar if n["satir"] == satir]
    # hece sınırları: harf sayısına göre ağırlıklı bölme, sonra enerji çukuruna yaslama
    w = np.array([len(n["hece"].replace("'", "")) + 0.6 for n in ns], float)
    sinir = np.concatenate([[0], np.cumsum(w) / w.sum()]) * N
    en = np.log(sp.sum(axis=1) + 1e-12); en = np.convolve(en, np.ones(5) / 5, "same")
    for k in range(1, len(sinir) - 1):
        c = int(sinir[k]); lo, hi = max(int(sinir[k - 1]) + 8, c - 12), min(N - 8, c + 12)
        if hi > lo: sinir[k] = lo + int(np.argmin(en[lo:hi]))
    sinir = sinir.astype(int)
    t0 = ns[0]["baslangic"]
    idx, hedef_f0 = [], []
    for k, n in enumerate(ns):
        s, e_ = sinir[k], sinir[k + 1]; L = e_ - s
        H = max(4, int(round(n["sure"] * 1000 / FP)))
        if k == len(ns) - 1: H = int(H * 0.85)                            # dize sonunda nefes payı
        on = min(int(L * 0.35), 14, H // 2)                               # baştaki ünsüz: doğal hızda
        son = min(int(L * 0.2), 8, H // 4)                                # sondaki ünsüz
        orta = np.linspace(s + on, e_ - son - 1, max(1, H - on - son))
        m = np.concatenate([np.arange(s, s + on), orta, np.arange(e_ - son, e_)])[:H]
        idx.append(m); hedef_f0.append(np.full(len(m), 440.0 * 2 ** ((n["midi"] - 69) / 12)))
    idx = np.concatenate(idx); hf = np.concatenate(hedef_f0)
    # notalar arası yumuşak geçiş + uzun notalarda hafif titreşim
    cek = np.hanning(13); cek /= cek.sum(); hf = np.exp(np.convolve(np.log(np.pad(hf, 6, "edge")), cek, "valid"))
    tt = np.arange(len(hf)) * FP / 1000; hf *= 2 ** (0.012 * np.sin(2 * np.pi * 5.5 * tt))
    lo, fr = np.floor(idx).astype(int), idx - np.floor(idx); hi = np.minimum(lo + 1, N - 1)
    sp2 = sp[lo] * (1 - fr)[:, None] + sp[hi] * fr[:, None]; ap2 = ap[lo] * (1 - fr)[:, None] + ap[hi] * fr[:, None]
    sesli = f0[np.round(idx).astype(int).clip(0, N - 1)] > 0
    f02 = np.where(sesli, hf, 0.0)
    y = pw.synthesize(f02, np.ascontiguousarray(sp2), np.ascontiguousarray(ap2), fs, FP)
    y[:220] *= np.linspace(0, 1, 220); y[-880:] *= np.linspace(1, 0, 880)
    p = int(t0 * fs); cikti[p:p + len(y)] += y[:max(0, len(cikti) - p)]
    rapor.append((satir, N * FP / 1000, len(y) / fs, [(n["hece"], round(sinir[k] * FP / 1000, 2)) for k, n in enumerate(ns)],
                  float(np.median(f0[f0 > 0])), float(sesli.mean())))
cikti *= 0.9 / np.abs(cikti).max()
sf.write(os.path.join(D, "kita1_ham.wav"), cikti, fs)
for r in rapor: print(r)
