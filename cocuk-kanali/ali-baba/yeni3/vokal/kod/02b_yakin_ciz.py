#!/usr/bin/env python3
"""Kesif cizimi (yalniz okur): birkac kisa araligin yakin plan dalga bicimi + genis bantli spektrogrami (0-10 kHz).
Kullanim: 02b_yakin_ciz.py <wav> <cikti.png> <t0> <t1> [<t0> <t1> ...]"""
import sys, numpy as np, soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

wav, out = sys.argv[1], sys.argv[2]
segs = [(float(a), float(b)) for a, b in zip(sys.argv[3::2], sys.argv[4::2])]
x, sr = sf.read(wav, dtype="float64")
fig, ax = plt.subplots(2, len(segs), figsize=(6 * len(segs), 8), squeeze=False)
for i, (t0, t1) in enumerate(segs):
    a, b = int(t0 * sr), int(t1 * sr)
    seg = x[a:b]
    ax[0, i].plot(np.arange(a, b) / sr, seg, lw=0.6)
    ax[0, i].set_xlim(t0, t1)
    ax[0, i].grid(alpha=0.3)
    ax[1, i].specgram(seg, NFFT=256, Fs=sr, noverlap=256 - 16, xextent=(t0, t1), vmin=-140, vmax=-50, cmap="magma")
    ax[1, i].set_ylim(0, 10000)
    ax[1, i].set_xlim(t0, t1)
    for k in (0, 1):
        ax[k, i].xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.02))
        ax[k, i].tick_params(labelsize=7)
plt.tight_layout()
plt.savefig(out, dpi=70)
