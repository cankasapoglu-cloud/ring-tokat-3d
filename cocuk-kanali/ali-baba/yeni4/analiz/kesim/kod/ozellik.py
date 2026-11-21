#!/usr/bin/env python3
"""1. adim: v2_2_vokal.wav (yeni4/vokal/kaynak) icin ozellikleri cikarir ve ara/ozellik.npz olarak saklar.
- rms      : 10 ms pencereli RMS zarfi (2 ms adim)
- b_*      : STFT bant enerjileri (2 ms adim, 23 ms pencere)
- flux     : log-mel spektral aki (pozitif fark, 10 ms geriye)
- f0       : pyworld harvest (150-700 Hz, 5 ms), ayrica dio+stonemask (capraz kontrol)
Hicbir uzak servis kullanilmaz."""
import os, numpy as np, soundfile as sf, pyworld as pw
from scipy.signal import stft

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # .../yeni4/analiz/kesim
A = os.path.dirname(os.path.dirname(os.path.dirname(K)))                 # .../ali-baba
os.makedirs(os.path.join(K, "ara"), exist_ok=True)
x, fs = sf.read(os.path.join(A, "yeni4", "vokal", "kaynak", "v2_2_vokal.wav"))
if x.ndim > 1:
    x = x.mean(axis=1)
x = x.astype(np.float64)
HOP = 88                       # 1.995 ms
NW = 1024                      # 23.2 ms

# --- kisa RMS (10 ms) ---
w10 = int(0.010 * fs)
c = np.concatenate([[0.0], np.cumsum(x ** 2)])
nfr = 1 + len(x) // HOP
ctr = np.arange(nfr) * HOP
lo = np.clip(ctr - w10 // 2, 0, len(x)); hi = np.clip(ctr + w10 // 2, 0, len(x))
rms = np.sqrt((c[hi] - c[lo]) / np.maximum(hi - lo, 1))

# --- STFT ---
f, tt, Z = stft(x, fs, window="hann", nperseg=NW, noverlap=NW - HOP, boundary="zeros", padded=True)
P = np.abs(Z) ** 2
P = P[:, :nfr]
if P.shape[1] < nfr:
    P = np.pad(P, ((0, 0), (0, nfr - P.shape[1])))


def band(a, b):
    m = (f >= a) & (f < b)
    return P[m].sum(axis=0)


bands = {
    "b_full": band(60, 12000),
    "b_low": band(100, 1000),      # temel + F1: seslilerde yuksek
    "b_mid": band(300, 3400),      # F1-F3: unlu cekirdegi
    "b_f2": band(1000, 3400),      # F2-F3: unlu ile l/n/r/y arasindaki fark burada
    "b_hi": band(4000, 12000),     # s, ş, ç, f, t patlamalari
}

# --- log-mel aki ---
nmel = 40
mel = lambda h: 2595 * np.log10(1 + h / 700.0)
imel = lambda m: 700 * (10 ** (m / 2595.0) - 1)
edges = imel(np.linspace(mel(80), mel(8000), nmel + 2))
FB = np.zeros((nmel, len(f)))
for i in range(nmel):
    a, b, c2 = edges[i], edges[i + 1], edges[i + 2]
    FB[i] = np.clip(np.minimum((f - a) / (b - a), (c2 - f) / (c2 - b)), 0, None)
M = FB @ P
LM = np.log(M + 1e-10)
LM = np.maximum(LM, LM.max() - 11.5)        # ~ -50 dB taban: sessizlikteki gurultu akiya girmesin
D = 5                                        # 10 ms
d = np.zeros_like(LM); d[:, D:] = LM[:, D:] - LM[:, :-D]
flux = np.maximum(d, 0).sum(axis=0)          # baslangic (onset) akisi
fluxabs = np.abs(d).sum(axis=0)              # iki yonlu spektral degisim (unlu-unlu gecisi icin)

# --- f0 ---
FP = 5.0
f0h, th = pw.harvest(x, fs, f0_floor=150.0, f0_ceil=700.0, frame_period=FP)
f0d, td = pw.dio(x, fs, f0_floor=150.0, f0_ceil=700.0, frame_period=FP)
f0s = pw.stonemask(x, f0d, td, fs)

np.savez_compressed(os.path.join(K, "ara", "ozellik.npz"), fs=fs, hop=HOP, t=ctr / fs, rms=rms,
                    flux=flux, fluxabs=fluxabs, logmel=LM.astype(np.float32), mel_edges=edges,
                    f0h=f0h, th=th, f0s=f0s, td=td, **bands)
print("fs", fs, "sure", len(x) / fs, "kare", nfr, "harvest sesli orani", float((f0h > 0).mean()),
      "dio sesli orani", float((f0s > 0).mean()))
