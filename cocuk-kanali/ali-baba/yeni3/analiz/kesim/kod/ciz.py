#!/usr/bin/env python3
"""Tani cizimi: log-mel spektrogram + bant zarflari + f0 + (varsa) kesim.json'daki hece sinirlari.
Kullanim: ciz.py BASLANGIC BITIS CIKTI.png   (saniye)
Yalnizca gozle kontrol (spektrogram) icindir; sesi kimse dinlemedi."""
import os, sys, json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.dirname(os.path.dirname(os.path.dirname(K)))
z = np.load(os.path.join(K, "ara", "ozellik.npz"))
t = z["t"]; LM = z["logmel"]; edges = z["mel_edges"]
a, b, out = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
m = (t >= a) & (t <= b)
db = lambda p: 10 * np.log10(p + 1e-12)
fig, ax = plt.subplots(3, 1, figsize=(20, 11), sharex=True, gridspec_kw={"height_ratios": [3, 2, 1.3]})
ax[0].imshow(LM[:, m], origin="lower", aspect="auto", extent=[a, b, 0, LM.shape[0]], cmap="magma",
             vmin=LM.max() - 11, vmax=LM.max())
yt = [0, 5, 10, 15, 20, 25, 30, 35, 39]
ax[0].set_yticks(yt); ax[0].set_yticklabels(["%d" % edges[i + 1] for i in yt]); ax[0].set_ylabel("Hz (mel)")
for k, c in (("b_low", "tab:blue"), ("b_mid", "tab:green"), ("b_f2", "tab:orange"), ("b_hi", "tab:red")):
    ax[1].plot(t[m], db(z[k][m]), c, lw=1.2, label=k)
ax[1].plot(t[m], 20 * np.log10(z["rms"][m] + 1e-9), "k", lw=0.8, label="rms")
ax[1].set_ylim(-62, -5); ax[1].legend(loc="upper right", ncol=5, fontsize=8); ax[1].grid(alpha=0.3)
th = z["th"]; f0 = z["f0h"]; mm = (th >= a) & (th <= b)
midi = np.where(f0 > 0, 69 + 12 * np.log2(np.maximum(f0, 1) / 440.0), np.nan)
ax[2].plot(th[mm], midi[mm], "b.", ms=3)
f0s = z["f0s"]; midis = np.where(f0s > 0, 69 + 12 * np.log2(np.maximum(f0s, 1) / 440.0), np.nan)
ax[2].plot(z["td"][mm], midis[mm], "r.", ms=1.5)
ax[2].set_ylim(57, 68); ax[2].grid(alpha=0.4); ax[2].set_ylabel("MIDI (mavi harvest, kirmizi dio)")
ax2 = ax[1].twinx(); ax2.plot(t[m], z["fluxabs"][m], color="gray", lw=0.6, alpha=0.7); ax2.set_ylim(0, 400)
# kelimeler
w = json.load(open(os.path.join(A, "dinle_2_words.json"), encoding="utf8")); w = w["words"] if isinstance(w, dict) else w
for q in w:
    if q.get("type") == "word" and q["end"] > a and q["start"] < b:
        for x in ax:
            x.axvline(q["start"], color="cyan", lw=0.8, ls="--"); x.axvline(q["end"], color="cyan", lw=0.8, ls=":")
        ax[0].text(max(q["start"], a), 41, q["text"], color="blue", fontsize=10, va="bottom", clip_on=False) if q["start"] < b - 0.05 else None
kj = os.path.join(K, "kesim.json")
if os.path.exists(kj) and "--ham" not in sys.argv:
    kd = json.load(open(kj, encoding="utf8"))
    RENK = {"dip": "white", "spectral": "cyan", "midpoint": "red", "model": "orange"}
    for kt in kd["verses"]:
        for ds in kt["lines"]:
            if ds["end"] < a or ds["start"] > b:
                continue
            for x in ax:
                x.axvline(ds["start"], color="lime", lw=2.5); x.axvline(ds["end"], color="lime", lw=2.5, ls="--")
                for key in ("cut_in", "cut_out"):
                    if ds.get(key) is not None:
                        x.axvline(ds[key], color="magenta", lw=1.5, ls="-.")
            for h in ds["syllables"]:
                if h["end"] < a or h["start"] > b:
                    continue
                eb = h.get("end_boundary")
                if eb:
                    ax[0].axvline(eb["t"], color=RENK[eb["kind"]], lw=1.6)
                    ax[1].axvline(eb["t"], color="k" if eb["kind"] == "dip" else "r", lw=1.2)
                    ax[2].axvline(eb["t"], color="k" if eb["kind"] == "dip" else "r", lw=1.0)
                ax[0].text((h["start"] + h["end"]) / 2, 36, h["text"], color="white", fontsize=11, ha="center", clip_on=True,
                           bbox=dict(facecolor="red" if h.get("flag") else "black", alpha=0.6, pad=1))
                ax[1].plot([h["nucleus"]], [-8], "kv", ms=6)
                ax[1].plot([h["core_start"], h["core_end"]], [-10, -10], "k-", lw=2)
                if h.get("f0_midi") is not None:
                    ax[2].plot([h["start"], h["end"]], [h["f0_midi"]] * 2, "g-", lw=1.5, alpha=0.7)
ax[0].set_xlim(a, b); ax[2].set_xlabel("s")
ax[2].set_xticks(np.arange(np.ceil(a * 10) / 10, b, 0.1))
plt.subplots_adjust(left=0.04, right=0.97, top=0.96, bottom=0.05, hspace=0.08); plt.savefig(out, dpi=70); print(out)
