#!/usr/bin/env python3
"""Deney E: Claude, sesin 'yapay/dogal' duyulmasina yol acan islemleri resimden ayirt edebilir mi?
Gercek bir vokal kaydindan 8 rastgele 3 sn'lik kesit alinir; her kesite GIZLI ve rastgele bir islem uygulanir:
  ham        : dokunulmamis
  world      : WORLD ile coz-yeniden uret (hafif vokoder rengi; insan kulagi cogu zaman fark eder)
  duz_perde  : perde en yakin yari tona kilitlenir, titresim silinir (sert autotune / robot)
  vizilti    : aperiyodiklik sifirlanir (tam periyodik, vizildayan vokoder sesi)
  formant15  : spektral zarf %15 yukari kaydirilir (cocuksu / 'sincap' tini), perde ayni
Her kesit icin log-mel spektrogram + perde egrisi cizilir. Dogru cevap gizli/ altinda.
Kullanim: python3 deney_E_tini.py <vokal.wav> <tohum>"""
import os, sys, json, random
os.environ.setdefault("OMP_NUM_THREADS", "2"); os.environ.setdefault("NUMBA_NUM_THREADS", "2")
import warnings; warnings.filterwarnings("ignore")
import numpy as np, librosa, soundfile as sf, pyworld as pw
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
B = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(B, "deney-E-tini-bozulma")
rnd = random.Random(int(sys.argv[2])); SR = 22050
y, _ = librosa.load(sys.argv[1], sr=SR, mono=True)
# sesli bolgelerden kesit sec
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
aday = [s for s in np.arange(0, len(y) / SR - 3.2, 0.5) if np.mean(rms[int(s * SR / 512): int((s + 3) * SR / 512)] > 0.25 * rms.max()) > 0.6]
rnd.shuffle(aday); basl = sorted(aday[:8]); rnd.shuffle(basl)
TUR = ["ham", "world", "duz_perde", "vizilti", "formant15"]
def isle(x, tur):
    if tur == "ham": return x
    x64 = x.astype(np.float64)
    f0, t = pw.dio(x64, SR, frame_period=5.0); f0 = pw.stonemask(x64, f0, t, SR)
    sp = pw.cheaptrick(x64, f0, t, SR); ap = pw.d4c(x64, f0, t, SR)
    if tur == "duz_perde":
        v = f0 > 0; m = np.round(librosa.hz_to_midi(np.where(v, f0, 440.0)))
        f0 = np.where(v, librosa.midi_to_hz(m), 0.0)
    if tur == "vizilti": ap = np.zeros_like(ap) + 1e-6
    if tur == "formant15":
        n = sp.shape[1]; src = np.clip(np.arange(n) / 1.15, 0, n - 1)
        sp = np.stack([np.interp(src, np.arange(n), fr) for fr in sp]); ap = np.stack([np.interp(src, np.arange(n), fr) for fr in ap])
    o = pw.synthesize(f0, np.ascontiguousarray(sp), np.ascontiguousarray(ap), SR, 5.0)
    return o[: len(x)].astype(np.float32)
INK, INK2, GRID, MAVI = "#0b0b0b", "#52514e", "#c3c2b7", "#2a78d6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2})
dogru = {}
for sayfa in range(2):
    fig, axs = plt.subplots(2, 4, figsize=(20, 11), dpi=100, facecolor="#fcfcfb", gridspec_kw={"height_ratios": [3, 2], "hspace": 0.16, "wspace": 0.2})
    for j in range(4):
        k = sayfa * 4 + j; ad = f"T{k + 1}"; tur = rnd.choice(TUR); s = basl[k]
        x = isle(y[int(s * SR): int((s + 3) * SR)].copy(), tur); x = x / (np.max(np.abs(x)) + 1e-9) * 0.7
        sf.write(os.path.join(OUT, f"{ad}.wav"), x, SR); dogru[ad] = {"islem": tur, "kesit_bas_sn": float(s)}
        S = librosa.power_to_db(librosa.feature.melspectrogram(y=x, sr=SR, n_fft=1024, hop_length=128, n_mels=200, fmin=60, fmax=11000), ref=np.max)
        mf = librosa.mel_frequencies(n_mels=200, fmin=60, fmax=11000); ax = axs[0, j]
        ax.imshow(S, origin="lower", aspect="auto", cmap="Greys", vmin=-75, vmax=0, extent=[0, 3, 0, 200], interpolation="nearest")
        tik = [100, 200, 400, 800, 1600, 3200, 6400]
        ax.set_yticks([np.interp(f, mf, np.arange(200)) for f in tik]); ax.set_yticklabels([f"{f} Hz" if f < 1000 else f"{f/1000:g} kHz" for f in tik])
        ax.set_title(f"{ad}: log-mel spektrogram", loc="left", fontsize=14)
        fo, vf, _ = librosa.pyin(x, fmin=librosa.note_to_hz("A2"), fmax=librosa.note_to_hz("C6"), sr=SR, frame_length=2048, hop_length=128)
        m = librosa.hz_to_midi(fo); tt = librosa.times_like(fo, sr=SR, hop_length=128); ax2 = axs[1, j]
        lo, hi = int(np.floor(np.nanmin(m))) - 1, int(np.ceil(np.nanmax(m))) + 1
        for q in range(lo, hi + 1): ax2.axhline(q, color=GRID, lw=0.7)
        ax2.plot(tt, m, color=MAVI, lw=2); ax2.set_ylim(lo, hi); ax2.set_xlim(0, 3)
        ax2.set_yticks(range(lo, hi + 1)); ax2.set_yticklabels([librosa.midi_to_note(q, unicode=False) for q in range(lo, hi + 1)], fontsize=9)
        ax2.set_title(f"{ad}: perde egrisi (pYIN), yatay cizgiler = yari tonlar", loc="left", fontsize=12); ax2.set_xlabel("zaman (sn)")
    fig.suptitle("Her kesite hangi islem uygulandi?  (ham / world / duz_perde / vizilti / formant15)", x=0.01, ha="left", fontsize=15)
    fig.subplots_adjust(left=0.045, right=0.995, top=0.92, bottom=0.05)
    fig.savefig(os.path.join(OUT, f"tini_sayfa{sayfa + 1}.png"), facecolor=fig.get_facecolor()); plt.close(fig)
json.dump(dogru, open(os.path.join(B, "gizli", "E_dogru.json"), "w"), indent=1)
print("2 sayfa yazildi; islemler gizli.")
