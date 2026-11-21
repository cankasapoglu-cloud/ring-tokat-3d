#!/usr/bin/env python3
"""5. adim (istege bagli): tani cizimleri -> cizim/K3_atlari.png, cizim/L2_sonlari.png, cizim/diye_baslari.png
Insan gozu icin; olcumler kesim.json'dadir."""
import os, json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from zarf import x, fs, t, fi, R5, F2B, ELOW8, EHI, th, f0h, midi
from ortak import K

d = json.load(open(os.path.join(K, "kesim.json"), encoding="utf8"))
os.makedirs(os.path.join(K, "cizim"), exist_ok=True)


def panel(ax, a, b, isaretler=(), bolgeler=()):
    ia, ib = fi(a), fi(b)
    tt = t[ia:ib]
    ax.plot(tt, R5[ia:ib], color="k", lw=1.0, label="tam bant 5 ms RMS")
    ax.plot(tt, ELOW8[ia:ib], color="tab:blue", lw=0.8, label="100-1000 Hz")
    ax.plot(tt, F2B[ia:ib], color="tab:red", lw=0.8, label="1-3.4 kHz")
    ax.plot(tt, EHI[ia:ib], color="tab:green", lw=0.6, label="4-12 kHz")
    ax.set_ylim(-70, -5); ax.set_xlim(a, b); ax.set_ylabel("dBFS"); ax.grid(alpha=0.3)
    for (q, etiket, renk) in isaretler:
        ax.axvline(q, color=renk, lw=1.0, ls="--"); ax.text(q, -8, etiket, rotation=90, va="top", ha="right", fontsize=7, color=renk)
    for (q0, q1, renk) in bolgeler:
        ax.axvspan(q0, q1, color=renk, alpha=0.15)
    ax2 = ax.twinx()
    m = (th >= a) & (th < b) & (f0h > 0)
    ax2.plot(th[m], midi(f0h[m]), ".", ms=2, color="tab:purple"); ax2.set_ylim(57, 72); ax2.set_ylabel("MIDI", color="tab:purple")


# ---- atları
ac = d["atlari_check"]; lm = ac["landmarks"]; ex = ac["excision"]
fig, axs = plt.subplots(2, 1, figsize=(12, 7))
a, b = 39.30, 40.60
i0, i1 = int(a * fs), int(b * fs)
axs[0].plot(np.arange(i0, i1) / fs, x[i0:i1], lw=0.4, color="k"); axs[0].set_xlim(a, b); axs[0].set_title("3. kita L2: 'atları' (soylenen: a-tı-la-rı). Gri: kesip atilacak aralik")
axs[0].axvspan(ex["start"], ex["end"], color="gray", alpha=0.3)
for bt in (6, 6.5, 7, 7.25, 7.5):
    axs[0].axvline(d["verses"][2]["downbeat"] + bt * d["grid_check"]["beat_period_s"], color="tab:orange", lw=0.8)
    axs[0].text(d["verses"][2]["downbeat"] + bt * d["grid_check"]["beat_period_s"], axs[0].get_ylim()[1] * 0.9, "vurus %g" % bt, fontsize=7, color="tab:orange")
panel(axs[1], a, b,
      [(lm["first_a_end_t_closure_start"], "a biter", "gray"), (lm["t_burst_onset"], "t patlamasi", "gray"), (lm["voicing_onset_after_t"], "otum (ek unlu)", "tab:red"),
       (lm["extra_vowel_end_l_onset"], "l baslar", "tab:blue"), (lm["second_a_onset"], "'la'nin a'si", "tab:red")],
      [(ex["start"], ex["end"], "gray")])
axs[1].legend(loc="lower left", fontsize=7, ncol=4)
fig.tight_layout(); fig.savefig(os.path.join(K, "cizim", "K3_atlari.png"), dpi=110); plt.close(fig)

# ---- L2 sonlari
fig, axs = plt.subplots(7, 1, figsize=(11, 16))
for v, kt in enumerate(d["verses"]):
    hc = kt["hard_cuts"]["L2_end"]; p = kt["pieces"][1]
    ve = hc["var_end"]
    panel(axs[v], ve - 0.20, ve + 0.25,
          [(ve, "var biter", "k"), (hc["animal_first_vowel_onset"], "hayvan unlusu", "tab:red"), (p["cut_out"], "kesim", "tab:green")],
          [(p["fade_out_start"], p["cut_out"], "tab:green")])
    axs[v].set_title("K%d L2 sonu: %s, bosluk %.0f ms, sonumleme %.0f ms (yesil)" % (v + 1, hc["what_follows"], hc["gap_ms"], p["fade_out_ms"]), fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(K, "cizim", "L2_sonlari.png"), dpi=90); plt.close(fig)

# ---- diye baslari
fig, axs = plt.subplots(7, 1, figsize=(11, 16))
for v, kt in enumerate(d["verses"]):
    hc = kt["hard_cuts"]["diye_start"]; p = kt["pieces"][2]
    on = hc["diye_onset"]
    panel(axs[v], on - 0.25, on + 0.15,
          [(hc["animal_sound_end"], "hayvan sesi biter", "tab:red"), (on, "diye", "k"), (p["cut_in"], "kesim", "tab:green")],
          [(p["cut_in"], hc["fade_in_end"], "tab:green")])
    axs[v].set_title("K%d 'diye' basi: bosluk %.0f ms, cukur %.1f dBFS, giris sonumlemesi %.0f ms (yesil)" % (v + 1, hc["gap_ms"], hc["dip_dbfs"], hc["fade_in_ms"]), fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(K, "cizim", "diye_baslari.png"), dpi=90); plt.close(fig)
print("yazildi: cizim/K3_atlari.png, cizim/L2_sonlari.png, cizim/diye_baslari.png")
