#!/usr/bin/env python3
"""Deney B: bilinen bir ezgiye GIZLI hatalar konur (detone, yanlis nota, gec/erken
giris, eksik nota, vibratosuz 'robot' nota). Claude yalnizca resme bakarak hatalari
bulabiliyor mu? Sayisal olcum ayni hatalari buluyor mu?
Uretir:  deney-B-ezgi-hata/<ad>_kontur.png   (Claude'un bakacagi resim)
         deney-B-ezgi-hata/<ad>_olcum.json   (sayisal olcum; resimden SONRA okunur)
         gizli/B_dogru_<ad>.json              (dogru cevap; en son okunur)
Kullanim: python3 deney_B_ezgi.py <ad> <tekrar> <tohum> [alt_nota ust_nota]
"""
import os, sys, json, random
os.environ.setdefault("OMP_NUM_THREADS", "2"); os.environ.setdefault("NUMBA_NUM_THREADS", "2")
import numpy as np, librosa, soundfile as sf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import lfilter, iirpeak

AD, TEKRAR, TOHUM = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ALT = sys.argv[4] if len(sys.argv) > 4 else "B3"
UST = sys.argv[5] if len(sys.argv) > 5 else "C5"
B = os.path.dirname(os.path.abspath(__file__))
rnd = random.Random(TOHUM); nrnd = np.random.default_rng(TOHUM)
SR = 22050; BPM = 100; BEAT = 60 / BPM

# Twinkle (Daha Dun Annemizin) ilk iki dize: (nota, vurus)
DIZE = [("C4",1),("C4",1),("G4",1),("G4",1),("A4",1),("A4",1),("G4",2),
        ("F4",1),("F4",1),("E4",1),("E4",1),("D4",1),("D4",1),("C4",2)]
notalar = []; t = 0.5
for r in range(TEKRAR):
    for n, v in DIZE:
        notalar.append({"i": len(notalar) + 1, "nota": n, "midi": float(librosa.note_to_midi(n)),
                        "bas": round(t, 3), "sure": round(v * BEAT * 0.92, 3)})
        t += v * BEAT
TOPLAM = t + 0.5

# ---- gizli hatalar ----
TURLER = ["+50c", "-40c", "+100c", "-200c", "gec180ms", "erken120ms", "eksik", "duz"]
n_hata = rnd.randint(2, 4) * TEKRAR + rnd.randint(-1, 1) * (TEKRAR > 1)
secilen = sorted(rnd.sample(range(len(notalar)), n_hata))
hatalar = {}
for k in secilen:
    hatalar[notalar[k]["i"]] = rnd.choice(TURLER)

# ---- sentez: harmonik + formant + vibrato + kayma ----
N = int(TOPLAM * SR); f0 = np.zeros(N); amp = np.zeros(N)
for no in notalar:
    h = hatalar.get(no["i"])
    if h == "eksik": continue
    midi = no["midi"] + {"+50c": .5, "-40c": -.4, "+100c": 1.0, "-200c": -2.0}.get(h, 0.0)
    bas = no["bas"] + {"gec180ms": .18, "erken120ms": -.12}.get(h, 0.0)
    a, b = int(bas * SR), int((bas + no["sure"]) * SR)
    tt = np.arange(b - a) / SR
    vib_derinlik = 0.0 if h == "duz" else 0.25  # yari ton cinsinden (+-25 cent)
    vib = vib_derinlik * np.sin(2 * np.pi * 5.5 * tt) * np.clip((tt - 0.12) / 0.15, 0, 1)
    surukle = 0.0 if h == "duz" else 0.05 * np.cumsum(nrnd.standard_normal(len(tt))) / np.sqrt(SR) * 8
    giris = -0.8 * np.exp(-tt / 0.03) * (0.0 if h == "duz" else 1.0)  # alttan girme (scoop)
    f0[a:b] = librosa.midi_to_hz(midi + vib + surukle + giris)
    env = np.minimum(1, tt / 0.03) * np.minimum(1, (tt[-1] - tt) / 0.06)
    amp[a:b] = env
faz = 2 * np.pi * np.cumsum(f0) / SR
y = np.zeros(N)
for k in range(1, 25):
    y += (1.0 / k) * np.sin(k * faz) * (k * f0 < SR / 2 - 500)
y *= amp
for fc, q, g in [(750, 5, 1.0), (1250, 7, 0.7), (2800, 9, 0.35)]:  # 'a' benzeri formantlar
    bb, aa = iirpeak(fc, q, fs=SR); y = y + g * 3 * lfilter(bb, aa, y)
y = y / np.max(np.abs(y)) * 0.6 + 0.003 * nrnd.standard_normal(N)
os.makedirs(os.path.join(B, "deney-B-ezgi-hata"), exist_ok=True)
sf.write(os.path.join(B, "deney-B-ezgi-hata", f"{AD}.wav"), y.astype(np.float32), SR)

# ---- analiz (gercek sarkida da ayni): pYIN + RMS ----
HOP = 256
fo, vflag, vprob = librosa.pyin(y, fmin=librosa.note_to_hz("C3"), fmax=librosa.note_to_hz("C6"),
                                sr=SR, frame_length=2048, hop_length=HOP)
tz = librosa.times_like(fo, sr=SR, hop_length=HOP)
midi_o = librosa.hz_to_midi(fo)
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0]
rms_db = 20 * np.log10(rms + 1e-6)
sesli = (rms_db > rms_db.max() - 30) & vflag

olcum = []
for no in notalar:
    a, b = no["bas"], no["bas"] + no["sure"]
    ic = (tz >= a + 0.10) & (tz <= b - 0.06) & sesli
    cevre = (tz >= a - 0.30) & (tz <= b + 0.05) & sesli
    kayit = {"i": no["i"], "nota": no["nota"], "hedef_bas": no["bas"]}
    kayit["sesli_oran"] = round(float(np.mean(sesli[(tz >= a) & (tz <= b)])), 2)
    if ic.sum() >= 5:
        sap = (midi_o[ic] - no["midi"]) * 100
        kayit["medyan_sapma_cent"] = round(float(np.nanmedian(sap)), 1)
        kayit["perde_oynakligi_cent_std"] = round(float(np.nanstd(sap - np.nanmedian(sap))), 1)
    else:
        kayit["medyan_sapma_cent"] = None; kayit["perde_oynakligi_cent_std"] = None
    kayit["giris_farki_ms"] = round(float((tz[cevre][0] - a) * 1000)) if cevre.any() else None
    olcum.append(kayit)
json.dump(olcum, open(os.path.join(B, "deney-B-ezgi-hata", f"{AD}_olcum.json"), "w"), ensure_ascii=False, indent=1)
os.makedirs(os.path.join(B, "gizli"), exist_ok=True)
json.dump({"hatalar": hatalar, "n": len(notalar)}, open(os.path.join(B, "gizli", f"B_dogru_{AD}.json"), "w"), ensure_ascii=False, indent=1)

# ---- resim: piyano rulosu ustunde perde egrisi (tek eksen), altta ayri panelde ses duzeyi ----
INK, INK2, GRID = "#0b0b0b", "#52514e", "#c3c2b7"
MAVI, TURUNCU = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID})
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(20, 10), dpi=100, sharex=True,
                              gridspec_kw={"height_ratios": [5, 1], "hspace": 0.06}, facecolor="#fcfcfb")
lo, hi = librosa.note_to_midi(ALT), librosa.note_to_midi(UST)
for m in range(lo, hi + 1):
    ax.axhline(m, color=GRID, lw=1.4 if m % 12 == 0 else 0.7, zorder=1)
for k in range(int(TOPLAM / BEAT) + 1):
    tb = 0.5 + k * BEAT
    for A in (ax, ax2): A.axvline(tb, color=GRID, lw=0.7, ls=(0, (2, 3)), zorder=1)
for no in notalar:  # hedef notalar: +-50 cent seridi + merkez cizgisi
    ax.add_patch(plt.Rectangle((no["bas"], no["midi"] - 0.5), no["sure"], 1.0, fc="#e6e5df", ec=INK2, lw=1.0, zorder=2))
    ax.plot([no["bas"], no["bas"] + no["sure"]], [no["midi"]] * 2, color=INK2, lw=1.0, zorder=3)
    ax.text(no["bas"] + 0.02, no["midi"] + 0.62, f"N{no['i']}", fontsize=12 if TEKRAR == 1 else 9, color=INK, zorder=5)
ax.plot(tz, np.where(sesli, midi_o, np.nan), color=MAVI, lw=2.2, zorder=4, label="olculen perde (pYIN)")
ax.plot([], [], color=INK2, lw=6, alpha=0.3, label="hedef nota (kutu = +-50 cent)")
ax.set_ylim(lo - 0.6, hi + 0.6)
ax.set_yticks(range(lo, hi + 1)); ax.set_yticklabels([librosa.midi_to_note(m, unicode=False) for m in range(lo, hi + 1)])
ax.set_ylabel("perde (yari ton izgarasi)"); ax.legend(loc="upper right", frameon=False)
ax.set_title(f"Perde egrisi ve hedef notalar - {AD} ({TOPLAM:.1f} sn, {BPM} BPM, kesikli dikey cizgi = vurus)", loc="left", fontsize=15)
ax2.plot(tz, rms_db, color=TURUNCU, lw=2); ax2.set_ylabel("duzey (dB)"); ax2.set_ylim(rms_db.max() - 45, rms_db.max() + 3)
ax2.set_xlabel("zaman (sn)"); ax2.set_xlim(0, TOPLAM)
ax2.set_xticks(np.arange(0, TOPLAM + 0.01, 0.5 if TEKRAR == 1 else 1.0))
for A in (ax, ax2):
    for s in ("top", "right"): A.spines[s].set_visible(False)
fig.subplots_adjust(left=0.05, right=0.995, top=0.95, bottom=0.07)
out = os.path.join(B, "deney-B-ezgi-hata", f"{AD}_kontur.png"); fig.savefig(out, facecolor=fig.get_facecolor())
print("yazildi:", out, "| nota sayisi:", len(notalar))
