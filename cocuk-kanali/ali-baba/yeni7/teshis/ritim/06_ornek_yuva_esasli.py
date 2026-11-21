#!/usr/bin/env python3
"""Kanıt örneği (sahibinin kulağı için A/B) + düzeltmenin ölçümle doğrulanması.
1) yeni4/vokal/vokal_dogal.wav, yeni6/03_psola.py ile AYNI yöntemle (Praat PSOLA) ama YUVA ESASLI hedeflerle (ara/hedefler_yuva_esasli.json) perdelenir
   -> ara/vokal_psola_yuva_esasli.wav   (zamanlama aynı; yalnız 83 hecenin hedef notası değişir)
2) yeni6/04_karisim.py ile aynı zincir ve düzeylerle 1.-2. kıta (8.0 - 46.0 s) karıştırılır:
   ornek_A_eski_hedef.mp3 (reddedilen karışımın aynısı) ve ornek_B_yuva_esasli.mp3
Mevcut hiçbir dosya değişmez; geçici dosyalar yalnız bu klasörün ara/ altına yazılır."""
import json, os, subprocess, sys, numpy as np, soundfile as sf, pyworld as pw, parselmouth
from parselmouth.praat import call
from ortak import *

Y = json.load(open(YERLESIM, encoding="utf8")); H = json.load(open(os.path.join(ARA, "hedefler_yuva_esasli.json"), encoding="utf8"))
CIK_VOK = os.path.join(ARA, "vokal_psola_yuva_esasli.wav"); FP = 5.0
if not os.path.exists(CIK_VOK):
    x, fs = sf.read(os.path.join(A, "yeni4", "vokal", "vokal_dogal.wav")); x = x.astype(np.float64); cikti = np.zeros_like(x); tablo = []
    for p in Y["pieces"]:
        a, b = int((p["dest_in"] - 0.06) * fs), int((p["dest_out"] + 0.06) * fs); seg = x[a:b]
        f0, t = pw.harvest(seg, fs, f0_floor=150, f0_ceil=720, frame_period=FP); f0 = pw.stonemask(seg, f0, t, fs)
        ta = t + a / fs; sesli = f0 > 0; lf = np.where(sesli, np.log2(np.maximum(f0, 1e-6)), np.nan)
        w = int(0.12 / (FP / 1000)) | 1; yavas = lf.copy()
        for i in np.where(sesli)[0]: yavas[i] = np.nanmedian(lf[max(0, i - w // 2):i + w // 2 + 1])
        hizli = np.clip(np.nan_to_num(lf - yavas), -0.5 / 12, 0.5 / 12)
        hs = [h for h in H if h["piece"] == p["id"]]; basamak = np.full(len(f0), np.nan)
        for h in hs:
            m = (ta >= h["dest_start"]) & (ta < h["dest_end"]); basamak[m] = np.log2(440.0 * 2 ** ((h["hedef_midi"] - 69) / 12))
        idx = np.where(~np.isnan(basamak))[0]; basamak = np.interp(np.arange(len(basamak)), idx, basamak[idx])
        cek = np.hanning(11); cek /= cek.sum(); basamak = np.convolve(np.pad(basamak, 5, "edge"), cek, "valid")
        hedef = 2 ** (basamak + hizli)
        snd = parselmouth.Sound(seg, sampling_frequency=fs); man = call(snd, "To Manipulation", 0.005, 150, 720)
        pt = call(man, "Extract pitch tier"); call(pt, "Remove points between", 0, snd.duration)
        for i in np.where(sesli)[0]: call(pt, "Add point", float(t[i]), float(hedef[i]))
        call([pt, man], "Replace pitch tier")
        y = call(man, "Get resynthesis (overlap-add)").values[0]; y = np.pad(y, (0, max(0, len(seg) - len(y))))[:len(seg)]
        y *= np.sqrt(np.mean(seg ** 2) / (np.mean(y ** 2) + 1e-12)); r = int(0.02 * fs); y[:r] *= np.linspace(0, 1, r); y[-r:] *= np.linspace(1, 0, r)
        cikti[a:a + len(y)] += y
    sf.write(CIK_VOK, cikti, fs, subtype="PCM_24"); print("yazıldı", CIK_VOK)

# ---- karışım: 04_karisim.py ile aynı zincir ----
T0, T1 = 8.0, 46.0; B = 240 / 105.0
b = oku_stereo = sf.read(RED_BAND)[0]; e = sf.read(RED_EZGI)[0]
pad = np.zeros((int(ON * FS), 2)); band = np.concatenate([pad, b]); ezgi = np.concatenate([pad, e]) * 10 ** (-4 / 20)
db = lambda q: 20 * np.log10(np.sqrt(np.mean(np.square(q))) + 1e-12)
def karistir(vok_yolu, cik):
    v, _ = sf.read(vok_yolu); n = max(len(band), len(v)); bb = np.pad(band, ((0, n - len(band)), (0, 0))); ee = np.pad(ezgi, ((0, n - len(ezgi)), (0, 0))); v = np.pad(v, (0, n - len(v)))
    w = int(0.05 * FS); env = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1; zemin = (bb + ee).mean(axis=1)
    hay = np.zeros((n, 2)); SIRA = ["inek", "koyun", "at", "horoz", "ordek", "kopek", "kedi"]
    for k in range(7):
        ob = [ON + (4 + 8 * k + i) * B for i in range(9)]
        for j, t in enumerate((ob[3], ob[4])):
            s, _ = sf.read(os.path.join(A, "yeni3", "ses", f"{SIRA[k]}_{j + 1}.wav")); s = s if s.ndim == 1 else s.mean(axis=1)
            ev = np.sqrt(np.convolve(s ** 2, np.ones(w) / w, "same")); yuk = ev > ev.max() * 10 ** (-10 / 20)
            g = min(10 ** ((-12.5 - db(s[yuk])) / 20), 1.0 / np.abs(s).max()); p = int((t - 0.04) * FS); hay[p:p + len(s)] += (s * g)[:, None]
    T = os.path.join(ARA, "_"); sf.write(T + "v0.wav", v, FS, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", T + "v0.wav", "-af", "highpass=f=130,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120:makeup=1,aecho=1.0:1.0:38:0.14", "-c:a", "pcm_f32le", T + "v1.wav"], check=True)
    vz, _ = sf.read(T + "v1.wav"); vz = np.pad(vz, (0, max(0, n - len(vz))))[:n]
    gv = 10 ** ((db(zemin[sesli]) + 8.5 - db(vz[sesli])) / 20); vz = vz * gv
    sf.write(T + "b.wav", bb + ee, FS, subtype="FLOAT"); sf.write(T + "v.wav", np.stack([vz, vz], axis=1), FS, subtype="FLOAT"); sf.write(T + "h.wav", hay, FS, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", T + "b.wav", "-i", T + "v.wav", "-i", T + "h.wav", "-filter_complex",
                    "[0:a][1:a][2:a]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.89:attack=5:release=60:level=disabled,volume=-4.1dB,atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS,afade=t=in:d=0.3,afade=t=out:st=%.3f:d=0.6[o]" % (T0, T1, T1 - T0 - 0.6),
                    "-map", "[o]", "-ar", "44100", "-b:a", "192k", cik], check=True)
    for q in ("v0", "v1", "b", "v", "h"): os.unlink(T + q + ".wav")
    print(cik, "vokal kazancı %.1f dB" % (20 * np.log10(gv)))
karistir(RED_VOK, os.path.join(D, "ornek_A_eski_hedef.mp3"))
karistir(CIK_VOK, os.path.join(D, "ornek_B_yuva_esasli.mp3"))
