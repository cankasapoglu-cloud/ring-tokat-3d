#!/usr/bin/env python3
"""Kesif cizimi (yalniz okur): L2 sonlari ve L1 'var,' sonlari spektrogramlari (kaynak vokal), kesim noktasiyla.
Cikti: cizim/kaynak_L2_sonlari.png, cizim/kaynak_L1_var_sonlari.png"""
import sys, os, numpy as np, scipy.signal as ss
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

x = oku_vokal()
K = oku_json(KESIM)
os.makedirs(os.path.join(V, "cizim"), exist_ok=True)


def spek(ax, t0, t1):
    a, b = int(t0 * SR), int(t1 * SR)
    f, t, Z = ss.spectrogram(x[a:b], fs=SR, window="hann", nperseg=441, noverlap=441 - 44, nfft=2048, mode="magnitude")
    D = 20 * np.log10(Z + 1e-9)
    ax.pcolormesh(t + t0, f, D, vmin=D.max() - 60, vmax=D.max(), cmap="magma", shading="auto")
    ax.set_ylim(0, 6000)


fig, axs = plt.subplots(7, 1, figsize=(11, 16))
for V_, ax in zip(K["verses"], axs):
    h = V_["hard_cuts"]["L2_end"]
    ve, co, fs = h["var_end"], h["recommended"]["cut_out"], h["recommended"]["fade_start"]
    var = [s for s in V_["lines"][1]["syllables"] if s["text"] == "var"][0]
    spek(ax, ve - 0.32, ve + 0.16)
    ax.axvline(var["start"], color="w", ls=":"); ax.axvline(ve, color="c", ls="--"); ax.axvline(fs, color="lime", ls="-"); ax.axvline(co, color="lime", ls="-")
    ax.axvline(h["animal_first_vowel_onset"], color="r", ls="--")
    ax.set_title("K%d L2 sonu: beyaz=var basi, yesil=gecis (fade) bas/son, camgobegi=var_end, kirmizi=hayvan unlusu" % V_["verse"], fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(V, "cizim", "kaynak_L2_sonlari.png"), dpi=80); plt.close(fig)

fig, axs = plt.subplots(7, 1, figsize=(11, 16))
for V_, ax in zip(K["verses"], axs):
    var = [s for s in V_["lines"][0]["syllables"] if s["text"] == "var"][0]
    e = var["end"]
    spek(ax, e - 0.32, e + 0.16)
    ax.axvline(var["start"], color="w", ls=":"); ax.axvline(e, color="c", ls="--")
    ax.set_title("K%d L1 'var,' sonu (karsilastirma): beyaz=var basi, camgobegi=var sonu; ardindan 'c' kapanisi" % V_["verse"], fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(V, "cizim", "kaynak_L1_var_sonlari.png"), dpi=80); plt.close(fig)
print("yazildi")
