#!/usr/bin/env python3
"""Kesif (yalniz okur): kesim noktalarinin kendi olcumum.
 (a) L2 sonu: 'var' -> soylenen hayvan sesi. Kesim.json'daki var_end'i BAGIMSIZ bir yontemle sinar:
     log-mel spektrum sablonu ('var' unlusu / sonraki ses) capraz gecis ani.
 (b) L1 'var,' sonlari (karsilastirma: bu sarkicida 'var' nasil biter).
 (c) 'diye' giris gecisi penceresi.
 (d) 3. kita 'atlari' kesip atma kenarlari.
Cikti: ara/inceleme.json + ekrana tablo."""
import sys, os, json, numpy as np, scipy.signal as ss
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
import warnings; warnings.filterwarnings("ignore")
import librosa

x = oku_vokal()
K = oku_json(KESIM)
SUNG = K["levels"]["sung_rms_dbfs"]
S = lambda t: int(round(t * SR))

# ---- log-mel, 1 ms adim, 12 ms pencere
N_FFT, HOP, WIN = 1024, 44, 529
M = librosa.feature.melspectrogram(y=x, sr=SR, n_fft=N_FFT, hop_length=HOP, win_length=WIN, n_mels=40, fmin=100, fmax=8000, power=2.0, center=True)
LM = 10 * np.log10(M + 1e-10)
tf = np.arange(LM.shape[1]) * HOP / SR


def bant(lo, hi):
    sos = ss.butter(4, [lo, hi], btype="band", fs=SR, output="sos")
    return ss.sosfiltfilt(sos, x)


B_LO, B_F2, B_HI = bant(100, 1000), bant(1000, 3400), bant(4000, 12000)
E5, E_LO, E_F2, E_HI = zarf(x, 5), zarf(B_LO, 5), zarf(B_F2, 5), zarf(B_HI, 5)
L = lambda e, t: db(e[S(t)])


def sablon(t0, t1):
    i = (tf >= t0) & (tf < t1)
    return LM[:, i].mean(axis=1)


def uzaklik(t, sab):
    j = int(round(t * SR / HOP))
    v = LM[:, j]
    d = v - sab
    d = d - d.mean()                      # duzeyden bagimsiz (yalniz bicim)
    return float(np.sqrt(np.mean(d ** 2)))


out = dict(l2_end=[], l1_var=[], diye=[], atlari={})
print("== (a) L2 SONU: 'var' -> hayvan sesi ==")
print("kita var_end  kesim  | capraz_gecis(bagimsiz) fark_ms | duzey: -30ms -20 -10 0 +10 +20 +30 (5 ms RMS, dBFS) | F2: -30 -20 -10 0 +10 +20")
for V in K["verses"]:
    v = V["verse"]
    h = V["hard_cuts"]["L2_end"]
    ve, co = h["var_end"], h["recommended"]["cut_out"]
    av = h["animal_first_vowel_onset"]
    var = [s_ for s_ in V["lines"][1]["syllables"] if s_["text"] == "var"][0]
    # sablonlar: 'var' unlusunun cekirdegi; sonraki ses = var_end+15 ms .. hayvan unlusu - 10 ms
    sab_var = sablon(var["core_start"], min(var["core_end"], ve - 0.030))
    sab_son = sablon(ve + 0.015, max(ve + 0.030, av - 0.010))
    ts = np.arange(ve - 0.060, ve + 0.060, 0.001)
    dv = np.array([uzaklik(t, sab_var) for t in ts])
    dn = np.array([uzaklik(t, sab_son) for t in ts])
    fark = dv - dn                         # < 0: 'var'a daha yakin
    # ilk kalici isaret degisimi
    cg = None
    for i in range(len(ts)):
        if fark[i] > 0 and np.all(fark[i:i + 8] > 0):
            cg = float(ts[i]); break
    lev = [round(L(E5, ve + d), 1) for d in (-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03)]
    f2 = [round(L(E_F2, ve + d), 1) for d in (-0.03, -0.02, -0.01, 0, 0.01, 0.02)]
    # gecis penceresindeki (fade) cerceveler 'var'a mi yakin?
    fs, fe = h["recommended"]["fade_start"], co
    ic = [(float(t), float(f)) for t, f in zip(ts, fark) if fs <= t <= fe]
    out["l2_end"].append(dict(verse=v, var_end=ve, cut_out=co, fade_start=fs, what_follows=h["what_follows"],
                              spectral_crossover=cg, crossover_minus_var_end_ms=None if cg is None else round((cg - ve) * 1000, 1),
                              crossover_minus_cut_out_ms=None if cg is None else round((cg - co) * 1000, 1),
                              level_5ms_dbfs=lev, f2_band_dbfs=f2,
                              frames_in_fade_closer_to_var=sum(1 for t, f in ic if f < 0), frames_in_fade=len(ic),
                              var_core=[var["core_start"], var["core_end"]], var_start=var["start"]))
    print("K%d  %.4f %.4f | %s  %s | %s | %s | gecis cerceveleri var'a yakin %d/%d" % (
        v, ve, co, "%.4f" % cg if cg else "yok", "%+.1f" % ((cg - ve) * 1000) if cg else "-", lev, f2,
        sum(1 for t, f in ic if f < 0), len(ic)))

print()
print("== (b) L1 'var,' sonlari (ardindan 'c' kapanisi gelir; karsilastirma) ==")
for V in K["verses"]:
    v = V["verse"]
    var = [s_ for s_ in V["lines"][0]["syllables"] if s_["text"] == "var"][0]
    var2 = [s_ for s_ in V["lines"][1]["syllables"] if s_["text"] == "var"][0]
    e = var["end"]
    # F2 bandinin unlu tepesinden 12 dB dustugu an (ayni tanim)
    a, b = S(var["core_start"]), S(e + 0.03)
    seg = 20 * np.log10(E_F2[a:b] + 1e-10)
    pk = seg[:S(var["core_end"]) - a].max()
    i12 = None
    for i in range(int(np.argmax(seg[:S(var["core_end"]) - a])), len(seg)):
        if seg[i] < pk - 12 and np.all(seg[i:i + S(0.02)] < pk - 12):
            i12 = i; break
    t12 = (a + i12) / SR if i12 is not None else None
    out["l1_var"].append(dict(verse=v, l1_var_start=var["start"], l1_var_end=e, l1_var_ms=round((e - var["start"]) * 1000, 1),
                              l1_f2_minus12_t=t12, l1_voiced_ms_until_f2_drop=None if t12 is None else round((t12 - var["start"]) * 1000, 1),
                              l2_var_ms=round((var2["end"] - var2["start"]) * 1000, 1)))
    print("K%d L1 var: %.4f-%.4f = %.0f ms (F2 -12 dB ani %s -> %s ms) | L2 var (var_end'e kadar): %.0f ms" % (
        v, var["start"], e, (e - var["start"]) * 1000, "%.4f" % t12 if t12 else "-", "%.0f" % ((t12 - var["start"]) * 1000) if t12 else "-",
        (var2["end"] - var2["start"]) * 1000))

print()
print("== (c) 'diye' giris gecisi ==")
for V in K["verses"]:
    v = V["verse"]
    h = V["hard_cuts"]["diye_start"]
    ci, fe = h["cut_in"], h["fade_in_end"]
    n = S(fe) - S(ci)
    g = kos_yuksel(n)
    seg = x[S(ci):S(fe)]
    ham = db(np.sqrt(np.mean(seg ** 2)))
    son = db(np.sqrt(np.mean((seg * g) ** 2)))
    once = rms_db(x, ci - 0.03, ci)
    out["diye"].append(dict(verse=v, cut_in=ci, fade_in_end=fe, diye_onset=h["diye_onset"], raw_rms_in_fade_dbfs=round(ham, 1),
                            faded_rms_in_fade_dbfs=round(son, 1), rms_30ms_before_cut_in_dbfs=round(once, 1),
                            animal_sound_end=h["animal_sound_end"], animal_body_end=h["animal_sound_body_end"]))
    print("K%d cut_in %.4f fade_end %.4f onset %.4f | gecis ici ham %.1f dBFS, gecisle %.1f dBFS | kesimden onceki 30 ms %.1f dBFS | hayvan sesi govde sonu %.4f, sonu %.4f" % (
        v, ci, fe, h["diye_onset"], ham, son, once, h["animal_sound_body_end"], h["animal_sound_end"]))

print()
print("== (d) 3. kita 'atlari' ==")
ex = K["atlari_check"]["excision"]
lm = K["atlari_check"]["landmarks"]
e0, e1 = ex["start"], ex["end"]
for ad, t in (("t surtunme sonu", lm["t_frication_end"]), ("kesip atma basi", e0), ("otum basi", lm["voicing_onset_after_t"]), ("kesip atma sonu", e1), ("'la' a'si", lm["second_a_onset"])):
    print("  %-18s %.4f : 5 ms RMS %.1f dBFS (1 ms: %.1f)" % (ad, t, L(E5, t), db(zarf(x[S(t) - 400:S(t) + 400], 1)[400])))
print("  1 ms RMS, kesip atma basi cevresi (-25..+8 ms, 1 ms adim):")
z1 = zarf(x, 1)
print("   ", [round(db(z1[S(e0 + d / 1000)]), 1) for d in range(-25, 9)])
print("  1 ms RMS, kesip atma sonu cevresi (-10..+60 ms, 2 ms adim):")
print("   ", [round(db(z1[S(e1 + d / 1000)]), 1) for d in range(-10, 61, 2)])
import pyworld as pw
a, b = S(39.30), S(40.60)
f0, tt = pw.harvest(x[a:b], SR, f0_floor=150, f0_ceil=600, frame_period=5.0)
tt = tt + a / SR
mm = np.where(f0 > 0, 69 + 12 * np.log2(np.maximum(f0, 1) / 440), np.nan)
def med(t0, t1):
    i = (tt >= t0) & (tt < t1) & np.isfinite(mm)
    return float(np.nanmedian(mm[i])) if i.any() else None
out["atlari"] = dict(excision=[e0, e1], level_at_start_dbfs=round(L(E5, e0), 1), level_at_end_dbfs=round(L(E5, e1), 1),
                     f0_at_vowel=med(39.41, 39.57), f0_kept_l=med(e1, lm["second_a_onset"]), f0_la=med(lm["second_a_onset"], 40.14),
                     f0_excised_vowel=med(lm["voicing_onset_after_t"], lm["extra_vowel_end_l_onset"]), f0_excised_l=med(lm["extra_vowel_end_l_onset"], e1))
print("  f0 (MIDI): 'at' unlusu %.2f | atilan ek unlu %.2f | atilan l %.2f | KALAN l (%.3f-%.3f) %.2f | 'la' %.2f" % (
    out["atlari"]["f0_at_vowel"], out["atlari"]["f0_excised_vowel"], out["atlari"]["f0_excised_l"], e1, lm["second_a_onset"], out["atlari"]["f0_kept_l"], out["atlari"]["f0_la"]))
print("  f0 izi 39.93-40.06 (5 ms):", [None if not np.isfinite(q) else round(float(q), 2) for q in mm[(tt >= 39.93) & (tt < 40.06)]])

os.makedirs(ARA, exist_ok=True)
with open(os.path.join(ARA, "inceleme.json"), "w", encoding="utf8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
