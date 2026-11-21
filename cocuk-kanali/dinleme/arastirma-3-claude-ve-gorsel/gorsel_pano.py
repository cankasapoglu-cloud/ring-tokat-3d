#!/usr/bin/env python3
"""gorsel_pano.py - Claude'un 'bakarak' inceleyebilecegi ses panosu (on-ornek).
Bir ses dosyasindan, ortak zaman eksenli 4 panel cizer (her panelde TEK dusey eksen):
  1) log-mel spektrogram (acik=sessiz, koyu=guclu) + ustte sozcuk etiketleri (Scribe JSON verilirse)
  2) kroma (12 nota sinifi) - akor/ton izlemek icin
  3) vurus gucu (onset) + bulunan vuruslar (dikey cizgi)
  4) ses duzeyi (RMS dBFS)
Resim 2000x1125 pikseldir: Claude Code'un Read araci uzun kenari 2000 pikselden buyuk
resimleri kuculttugu icin (olculdu) daha buyugu bosa gider.
Kullanim: python3 gorsel_pano.py <ses> <cikti.png> [--bas S] [--son S] [--sozcuk scribe.json] [--baslik "..."]
UYARI: Bu resim kulak degildir. Ne ZAMAN ne oldugunu, perdeyi, ritmi, duzeyi gosterir;
sesin dogal/yapay, guzel/kotu, aksanli/aksansiz oldugunu GOSTERMEZ.
"""
import os, sys, json, argparse
os.environ.setdefault("OMP_NUM_THREADS", "2"); os.environ.setdefault("NUMBA_NUM_THREADS", "2")
import numpy as np, librosa
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("ses"); ap.add_argument("cikti")
ap.add_argument("--bas", type=float, default=0.0); ap.add_argument("--son", type=float, default=None)
ap.add_argument("--sozcuk", default=None); ap.add_argument("--baslik", default=None)
a = ap.parse_args()

SR, HOP = 22050, 256
y, sr = librosa.load(a.ses, sr=SR, mono=True, offset=a.bas, duration=None if a.son is None else a.son - a.bas)
sure = len(y) / sr; t0 = a.bas
INK, INK2, GRID = "#0b0b0b", "#52514e", "#c3c2b7"; MAVI, TURUNCU = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID})
fig, axs = plt.subplots(4, 1, figsize=(20, 11.25), dpi=100, sharex=True, facecolor="#fcfcfb",
                        gridspec_kw={"height_ratios": [5, 2.2, 1.4, 1.4], "hspace": 0.10})
ext = [t0, t0 + sure]

# 1) log-mel
NM = 160; FMIN, FMAX = 60, 11000
S = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=HOP, n_mels=NM, fmin=FMIN, fmax=FMAX), ref=np.max)
axs[0].imshow(S, origin="lower", aspect="auto", cmap="Greys", vmin=-70, vmax=0, extent=[*ext, 0, NM], interpolation="nearest")
mf = librosa.mel_frequencies(n_mels=NM, fmin=FMIN, fmax=FMAX)
tik = [100, 200, 400, 800, 1600, 3200, 6400]
axs[0].set_yticks([np.interp(f, mf, np.arange(NM)) for f in tik]); axs[0].set_yticklabels([f"{f} Hz" if f < 1000 else f"{f/1000:g} kHz" for f in tik])
axs[0].set_ylabel("frekans (log-mel)")
if a.sozcuk:
    W = [w for w in json.load(open(a.sozcuk))["words"] if w["type"] != "spacing" and t0 <= w["start"] <= t0 + sure]
    for k, w in enumerate(W):
        olay = w["type"] == "audio_event"
        axs[0].axvline(w["start"], color=TURUNCU if olay else MAVI, lw=1.0, alpha=0.9, ymin=0.0, ymax=1.0)
        axs[0].text(w["start"] + sure * 0.002, NM * (1.02 + 0.055 * (k % 3)), w["text"].strip(), fontsize=11 if sure > 15 else 13,
                    color=INK, ha="left", va="bottom", clip_on=False)
    axs[0].plot([], [], color=MAVI, lw=1.5, label="sozcuk baslangici (Scribe)"); axs[0].plot([], [], color=TURUNCU, lw=1.5, label="ses olayi (Scribe)")
    axs[0].legend(loc="lower right", frameon=True, facecolor="#fcfcfb", edgecolor=GRID, fontsize=10)

# 2) kroma
C = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP * 2)
axs[1].imshow(C, origin="lower", aspect="auto", cmap="Greys", vmin=0, vmax=1, extent=[*ext, 0, 12], interpolation="nearest")
axs[1].set_yticks(np.arange(12) + 0.5); axs[1].set_yticklabels(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], fontsize=10)
axs[1].set_ylabel("kroma (nota sinifi)")

# 3) vurus gucu + vuruslar
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=HOP)
tz = librosa.times_like(oenv, sr=sr, hop_length=HOP) + t0
for b in librosa.frames_to_time(beats, sr=sr, hop_length=HOP) + t0:
    for A in axs: A.axvline(b, color=GRID if A is not axs[2] else INK2, lw=0.6, ls=(0, (2, 3)), zorder=1)
axs[2].plot(tz, oenv, color=MAVI, lw=1.6); axs[2].set_ylabel("vurus gucu"); axs[2].set_ylim(0, None)
bpm = float(np.atleast_1d(tempo)[0])
axs[2].text(0.005, 0.86, f"tahmini tempo {bpm:.0f} BPM, {len(beats)} vurus (kesikli cizgiler)", transform=axs[2].transAxes, fontsize=11)

# 4) duzey
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0]; db = 20 * np.log10(rms + 1e-6)
axs[3].plot(librosa.times_like(rms, sr=sr, hop_length=HOP) + t0, db, color=TURUNCU, lw=1.8)
axs[3].set_ylim(-60, 0); axs[3].set_yticks([-60, -40, -20, 0]); axs[3].set_ylabel("duzey (dBFS)")
axs[3].text(0.005, 0.80, f"tepe {20*np.log10(np.max(np.abs(y))+1e-9):.1f} dBFS, ortalama RMS {20*np.log10(np.sqrt(np.mean(y**2))+1e-9):.1f} dBFS", transform=axs[3].transAxes, fontsize=11)
adim = 1.0 if sure > 12 else 0.5 if sure > 5 else 0.25
axs[3].set_xticks(np.arange(np.ceil(t0 / adim) * adim, t0 + sure + 1e-6, adim)); axs[3].set_xlim(*ext); axs[3].set_xlabel("zaman (sn)")
for A in axs:
    for s in ("top", "right"): A.spines[s].set_visible(False)
fig.suptitle(a.baslik or f"{os.path.basename(a.ses)}  [{t0:.1f}-{t0+sure:.1f} sn]", x=0.045, ha="left", fontsize=15, y=0.995)
fig.subplots_adjust(left=0.055, right=0.995, top=0.90, bottom=0.055)
fig.savefig(a.cikti, facecolor=fig.get_facecolor()); print("yazildi:", a.cikti, f"| {sure:.1f} sn, {2000/sure:.0f} piksel/sn")
