#!/usr/bin/env python3
"""Sonuc cizimleri (yalniz okur): (1) 3. kita L2 'atlari' once (kaynak) / sonra (cikti), ayni zaman olcegi;
(2) bir kitanin (K3) cikti dalga bicimi, olcu cizgileri ve hayvan sesi yuvalariyla; (3) yedi kitanin L2 sonu (cikti) + sonraki hayvan sesi yuvasi.
Cikti: cizim/K3_L2_once_sonra.png, cizim/K3_kita_yerlesim.png, cizim/cikti_L2_sonlari.png"""
import sys, os, numpy as np, scipy.signal as ss, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

x = oku_vokal()
y, _ = sf.read(CIKTI_WAV, dtype="float64")
Y = oku_json(CIKTI_JSON)
g = Y["audio"]["global_gain_linear"]
os.makedirs(os.path.join(V, "cizim"), exist_ok=True)


def spek(ax, sig, t0, t1, olcek=1.0):
    a, b = int(t0 * SR), int(t1 * SR)
    f, t, Z = ss.spectrogram(sig[a:b] / olcek, fs=SR, window="hann", nperseg=441, noverlap=441 - 44, nfft=2048, mode="magnitude")
    ax.pcolormesh(t + t0, f, 20 * np.log10(Z + 1e-7), vmin=-95, vmax=-35, cmap="magma", shading="auto")
    ax.set_ylim(0, 6000)


# ---- (1) K3 L2 once / sonra
p = [q for q in Y["pieces"] if q["id"] == "K3_P2"][0]
kay = p["shift_sec"]
L = [q for q in Y["lines"] if q["verse"] == 3 and q["line"] == "L2"][0]
t0, t1 = 39.25, 40.62
fig, axs = plt.subplots(4, 1, figsize=(12, 11))
tt = np.arange(int(t0 * SR), int(t1 * SR)) / SR
axs[0].plot(tt, x[int(t0 * SR):int(t1 * SR)], lw=0.4, color="k"); axs[0].set_title("ONCE (kaynak vokal, kaynak zamani): 'a-ti-la-ri var'"); axs[0].set_xlim(t0, t1)
spek(axs[1], x, t0, t1)
axs[2].plot(tt, y[int((t0 + kay) * SR):int((t1 + kay) * SR)] / g, lw=0.4, color="k"); axs[2].set_title("SONRA (vokal_dogal.wav, kaynak zamanina geri kaydirilmis): 'at' + sus + 'lari var'"); axs[2].set_xlim(t0, t1)
spek(axs[3], y, t0 + kay, t1 + kay, g)
r = Y["repairs"][0]
for ax, kayma in ((axs[0], 0.0), (axs[1], 0.0), (axs[2], 0.0), (axs[3], kay)):
    ax.axvspan(r["excision"]["src_from"] + kayma, r["excision"]["src_to"] + kayma, color="red" if kayma == 0.0 and ax is not axs[1] else "white", alpha=0.12)
    for h in L["syllables"][4:]:
        ax.axvline(h["src_start"] + kayma, color="tab:blue" if ax in (axs[0], axs[2]) else "w", lw=0.6, ls=":")
    for b in (2, 2.5, 3, 3.25, 3.5):
        ax.axvline(p["src_bar_downbeat"] + b * 0.5714133 + kayma, color="tab:orange", lw=0.8)
    ax.set_xlim(t0 + kayma, t1 + kayma)
for h in L["syllables"][4:]:
    axs[2].text(h["src_start"] + 0.005, 0.8 * np.max(np.abs(x[int(t0 * SR):int(t1 * SR)])), h["text"], fontsize=9, color="tab:blue")
fig.tight_layout(); fig.savefig(os.path.join(V, "cizim", "K3_L2_once_sonra.png"), dpi=75); plt.close(fig)

# ---- (2) K3 kita yerlesimi
fig, ax = plt.subplots(1, 1, figsize=(15, 3.6))
b0 = 4 + 8 * 2
a, b = olcu_basi_n(b0) - 8820, olcu_basi_n(b0 + 8) + 4410
ax.plot(np.arange(a, b)[::8] / SR, y[a:b][::8], lw=0.3, color="k")
for i in range(9):
    ax.axvline(olcu_basi_n(b0 + i) / SR, color="tab:orange", lw=1.0)
    if i < 8:
        ax.text(olcu_basi_n(b0 + i) / SR + 0.02, 0.62, "olcu %d\n%s" % (i, ["L1", "calgi cevap", "L2", "hayvan 1", "hayvan 2", "dolgu | diye", "L4", "calgi cevap"][i]), fontsize=8, color="tab:orange")
for sl in Y["animal_call_slots"]:
    if sl["verse"] == 3:
        for c in ("call_1", "call_2"):
            ax.axvspan(sl[c]["start"], sl[c]["start"] + 1.85, color="green", alpha=0.10)
for q in Y["pieces"]:
    if q["verse"] == 3:
        ax.axvline(q["dest_in"], color="tab:blue", lw=0.6, ls="--"); ax.axvline(q["dest_out"], color="tab:blue", lw=0.6, ls="--")
ax.set_xlim(a / SR, b / SR); ax.set_ylim(-0.75, 0.75)
ax.set_title("3. kita, vokal_dogal.wav: turuncu = olcu cizgileri, mavi kesik = parca sinirlari, yesil = gercek hayvan sesi yuvalari (en cok 1.85 s)")
fig.tight_layout(); fig.savefig(os.path.join(V, "cizim", "K3_kita_yerlesim.png"), dpi=75); plt.close(fig)

# ---- (3) L2 sonlari (cikti)
fig, axs = plt.subplots(7, 1, figsize=(11, 15))
for vi, ax in enumerate(axs):
    q = [q for q in Y["pieces"] if q["verse"] == vi + 1 and q["piece"] == 2][0]
    d = q["dest_out"]
    spek(ax, y, d - 0.32, d + 0.16, g)
    ax.axvline(q["fade_out"]["src_from"] + q["shift_sec"], color="lime"); ax.axvline(d, color="lime")
    ax.axvline(olcu_basi_n(q["dest_bar"] + 1) / SR - 0.040, color="c", ls="--"); ax.axvline(olcu_basi_n(q["dest_bar"] + 1) / SR, color="orange")
    ax.set_title("K%d L2 sonu (cikti): yesil = gecis bas/son, camgobegi = gercek hayvan sesinin baslayacagi an, turuncu = olcu cizgisi" % (vi + 1), fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(V, "cizim", "cikti_L2_sonlari.png"), dpi=75); plt.close(fig)
print("yazildi: cizim/K3_L2_once_sonra.png, cizim/K3_kita_yerlesim.png, cizim/cikti_L2_sonlari.png")
