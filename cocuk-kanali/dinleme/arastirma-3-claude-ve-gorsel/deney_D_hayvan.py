#!/usr/bin/env python3
"""Deney D: Claude bir sesin NE oldugunu spektrogram resminden anlayabilir mi?
Depodaki gercek hayvan sesleri (7 tur) karistirilir, adlari gizlenir, her biri
log-mel spektrogram paneli olarak cizilir. Kor test: dogru cevap gizli/ altinda.
Kullanim: python3 deney_D_hayvan.py <tohum>"""
import os, sys, json, random, glob
os.environ.setdefault("OMP_NUM_THREADS", "2"); os.environ.setdefault("NUMBA_NUM_THREADS", "2")
import numpy as np, librosa
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
B = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(B, "..", "..", "ali-baba", "yeni", "ses"))
dosyalar = sorted(glob.glob(os.path.join(KOK, "alternatif", "*.mp3")) + glob.glob(os.path.join(KOK, "kirpilmis", "*.wav")))
rnd = random.Random(int(sys.argv[1])); rnd.shuffle(dosyalar); dosyalar = dosyalar[:24]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#c3c2b7"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2})
dogru = {}
for sayfa in range(3):
    fig, axs = plt.subplots(2, 4, figsize=(20, 10), dpi=100, facecolor="#fcfcfb")
    for j, ax in enumerate(axs.ravel()):
        k = sayfa * 8 + j; yol = dosyalar[k]; ad = f"S{k + 1}"
        y, sr = librosa.load(yol, sr=22050, mono=True); y = y[: int(4.0 * sr)]
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=1024, hop_length=128, n_mels=160, fmin=60, fmax=11000)
        D = librosa.power_to_db(S, ref=np.max)
        mel_f = librosa.mel_frequencies(n_mels=160, fmin=60, fmax=11000)
        ax.imshow(D, origin="lower", aspect="auto", cmap="Greys", vmin=-70, vmax=0, extent=[0, len(y) / sr, 0, 160], interpolation="nearest")
        tik = [100, 200, 400, 800, 1600, 3200, 6400]
        ax.set_yticks([np.interp(f, mel_f, np.arange(160)) for f in tik]); ax.set_yticklabels([f"{f} Hz" if f < 1000 else f"{f/1000:g} kHz" for f in tik])
        ax.set_title(f"{ad}  (sure {len(y)/sr:.2f} sn)", loc="left", fontsize=14); ax.set_xlabel("zaman (sn)")
        dogru[ad] = os.path.basename(yol).split("_")[0].split(".")[0]
    fig.suptitle("Log-mel spektrogram (koyu = guclu). Her panel hangi hayvan? (kopek, kedi, ordek, at, koyun, inek, horoz)", x=0.01, ha="left", fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(B, "deney-D-hayvan-sesi", f"hayvan_sayfa{sayfa + 1}.png"), facecolor=fig.get_facecolor()); plt.close(fig)
json.dump(dogru, open(os.path.join(B, "gizli", "D_dogru.json"), "w"), indent=1)
print("3 sayfa yazildi; sinif dagilimi gizli.")
