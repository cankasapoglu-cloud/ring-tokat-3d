#!/usr/bin/env python3
"""Soru 2-3 (iki tarafta AYNI ölçüm): Vokalin o an söylediği perde sınıfı, orkestranın o anki kromasında (hangi notalar çalıyor) ne kadar var,
ve bu uyum vokal kaç ms kaydırılınca en yüksek oluyor?
  RED: vokal_psola.wav  <->  0.100 s dolgulu altyapi_G + ezgi_alti_G (karışımdaki oranla)
  REF: MDX vokal kökü   <->  MDX enstrüman kökü (v2_2)
Yalnız yerlesim.json'daki aynı 229 hecenin süreleri kullanılır (REF'te söylenen hayvan sesleri dışarıda).
Uyum = vokalin perde sınıfına düşen kroma payı (kare başına kroma toplamı 1'e ölçeklenir; rastgele beklenti 1/12 = 0.083).
İki bant: tam (C2-C7) ve yalnız pes (C2-B3; vokalin temel sesi 290 Hz ve üstü olduğundan MDX kökündeki vokal sızıntısı bu banda giremez)."""
import json, os, numpy as np, librosa, parselmouth
from ortak import *

Y = json.load(open(YERLESIM, encoding="utf8")); SR = 22050; HOP = 256; KARE = HOP / SR
hec = [dict(s, shift=L["shift_sec"], verse=L["verse"], line=L["line"]) for L in Y["lines"] for s in L["syllables"]]

def kroma(x, n_oct):
    y = librosa.resample(x, orig_sr=FS, target_sr=SR)
    C = np.abs(librosa.cqt(y, sr=SR, hop_length=HOP, fmin=librosa.note_to_hz("C2"), n_bins=12 * n_oct, bins_per_octave=12))
    ch = np.zeros((12, C.shape[1]))
    for b in range(C.shape[0]): ch[b % 12] += C[b] ** 2          # C2 = perde sınıfı 0 (C)
    return ch / (ch.sum(axis=0, keepdims=True) + 1e-12)

def vokal_ps(x, n):
    p = parselmouth.Sound(x, sampling_frequency=FS).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=720)
    f = p.selected_array["frequency"]; t = p.xs(); tt = np.arange(n) * KARE
    i = np.clip(np.searchsorted(t, tt), 0, len(t) - 1); ff = f[i]
    return np.where(ff > 0, np.round(69 + 12 * np.log2(np.maximum(ff, 1) / 440)) % 12, -1).astype(int)

def egri(ps, ch, maske, kaymalar):
    c = {}
    idx = np.where(maske & (ps >= 0))[0]
    for k in kaymalar:
        s = int(round(k / 1000 / KARE)); j = idx - s                      # vokal(t) ile orkestra(t - kayma): kayma>0 = vokal geride
        g = (j >= 0) & (j < ch.shape[1]); c[k] = float(ch[ps[idx[g]], j[g]].mean())
    return c, len(idx)

def taraf(vok, ens, bas_anahtar, bit_anahtar, kaydir):
    cikti = {}
    for ad, n_oct in (("tam_C2_C7", 5), ("pes_C2_B3", 2)):
        ch = kroma(ens, n_oct); ps = vokal_ps(vok, ch.shape[1]); t = np.arange(ch.shape[1]) * KARE; m = np.zeros(len(t), bool)
        for h in hec:
            a = h[bas_anahtar] - (h["shift"] if kaydir else 0); b = h[bit_anahtar] - (h["shift"] if kaydir else 0); m |= (t >= a) & (t <= b)
        K = list(range(-600, 601, 25)); e, n = egri(ps, ch, m, K); en = max(e, key=e.get)
        cikti[ad] = {"kare": n, "sure_sn": round(n * KARE, 1), "uyum_kayma_0": round(e[0], 4), "en_iyi_kayma_ms": en, "en_iyi_uyum": round(e[en], 4), "uyum_+275": round(e[275], 4), "uyum_-275": round(e[-275], 4),
                      "kayma0_bolu_en_iyi": round(e[0] / e[en], 3), "egri_her_100ms": {str(k): round(e[k], 4) for k in range(-600, 601, 100)}, "egri": {str(k): round(v, 4) for k, v in e.items()}}
    return cikti

sonuc = {"tanim": __doc__}
band = np.concatenate([np.zeros(int(ON * FS)), oku_mono(RED_BAND) + oku_mono(RED_EZGI) * 10 ** (-4 / 20)])
sonuc["RED_orkestra+ezgi"] = taraf(oku_mono(RED_VOK), band, "dest_start", "dest_end", False)
band2 = np.concatenate([np.zeros(int(ON * FS)), oku_mono(RED_BAND)])
sonuc["RED_yalniz_altyapi(ezgi_alti_yok)"] = taraf(oku_mono(RED_VOK), band2, "dest_start", "dest_end", False)
del band, band2
sonuc["REF"] = taraf(oku_mono(REF_VOK), oku_mono(REF_ENS), "dest_start", "dest_end", True)
json.dump(sonuc, open(os.path.join(ARA, "04_kroma_kayma.json"), "w"), ensure_ascii=False, indent=1)
for k, v in sonuc.items():
    if k == "tanim": continue
    for b, d in v.items(): print("%-34s %-10s kayma0 %.3f | en iyi %+d ms %.3f | +275 %.3f | -275 %.3f | 0/eniyi %.2f | %s" % (k, b, d["uyum_kayma_0"], d["en_iyi_kayma_ms"], d["en_iyi_uyum"], d["uyum_+275"], d["uyum_-275"], d["kayma0_bolu_en_iyi"], d["egri_her_100ms"]))
