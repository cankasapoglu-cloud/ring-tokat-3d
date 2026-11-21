#!/usr/bin/env python3
"""Kesif cizimi (yalniz okur): bir zaman araliginin dalga bicimi + spektrogrami + 2 ms RMS.
Kullanim: 02_ciz.py <wav> <cikti.png> <t0> <t1> [isaret1 isaret2 ...]"""
import sys, numpy as np, soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

wav, out, t0, t1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
marks = [float(a) for a in sys.argv[5:]]
x, sr = sf.read(wav, dtype="float64")
if x.ndim > 1:
    x = x.mean(1)
a, b = int(t0 * sr), int(t1 * sr)
seg = x[a:b]
t = np.arange(a, b) / sr
fig, ax = plt.subplots(3, 1, figsize=(16, 9), sharex=True)
ax[0].plot(t, seg, lw=0.5)
ax[0].set_ylabel("dalga")
n = int(0.002 * sr)
m = len(seg) // n
r = 20 * np.log10(np.sqrt(np.mean(seg[: m * n].reshape(m, n) ** 2, axis=1)) + 1e-10)
ax[1].plot(t0 + (np.arange(m) + 0.5) * n / sr, r, lw=0.8)
ax[1].set_ylim(-95, 0)
ax[1].set_ylabel("2 ms RMS dBFS")
ax[1].grid(alpha=0.3)
ax[2].specgram(seg, NFFT=1024, Fs=sr, noverlap=1024 - 64, xextent=(t0, t1), vmin=-140, vmax=-40, cmap="magma")
ax[2].set_ylim(0, 6000)
ax[2].set_ylabel("Hz")
for q in marks:
    for k in ax:
        k.axvline(q, color="c", lw=0.8)
ax[2].set_xlim(t0, t1)
ax[2].xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.05 if t1 - t0 < 1.5 else 0.2))
plt.tight_layout()
plt.savefig(out, dpi=70)
