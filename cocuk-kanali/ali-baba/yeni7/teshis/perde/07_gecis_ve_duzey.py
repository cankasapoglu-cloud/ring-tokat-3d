#!/usr/bin/env python3
"""(a) Nota geçişleri: art arda iki hecenin perdesi >= 1.5 yarım ses farklıysa ve geçiş boyunca ses kesilmiyorsa, f0'ın
    adımın %20'sinden %80'ine gitme süresi (ms). Reddedilen vokal (PSOLA) ve referans vokal, aynı yöntem.
(b) Vokal / orkestra düzey farkının sağlaması (mercek dışı ama aynı stemlerden ucuz ölçüm):
    - referans: ayrılmış vokal - ayrılmış orkestra, söylenen karelerde; tek kanala indirerek ve kanal başına güçle (stereo genişliği etkisi)
    - reddedilen: bitmiş mp3'e en küçük kareler ile [orkestra+ezgi, vokal] uydurularak GERÇEK oran (sınırlayıcı sonrası)
Çıktı: ara/07_gecis_ve_duzey.json"""
import json, os, subprocess, numpy as np, soundfile as sf
from scipy import signal
from ortak import *

Y, S, Z = yukle(); cik = {}
tp, fp = f0_izi(RED_VOK, "red_psola"); tr, fr = f0_izi(REF_VOK, "ref_vokal")


def gecisler(t, f0, bas, bit, perde):
    r = []
    for i in range(len(S) - 1):
        a, b = S[i], S[i + 1]
        if a["piece"] != b["piece"]: continue
        pa, pb = perde(i), perde(i + 1)
        if np.isnan(pa) or np.isnan(pb) or abs(pb - pa) < 1.5: continue
        sinir = bit(a); m = (t >= sinir - 0.15) & (t <= sinir + 0.15); tt = t[m]; ff = f0[m]
        if (ff > 0).mean() < 0.9: continue                      # ünsüzle kesilen geçişler ölçülmez
        mm = hz2midi(np.where(ff > 0, ff, np.nan)); ok = ~np.isnan(mm); mm = np.interp(tt, tt[ok], mm[ok]); u = (mm - pa) / (pb - pa)
        # %20'nin son aşıldığı an ile %80'in ilk aşıldığı an
        i80 = np.where(u >= 0.8)[0]
        if len(i80) == 0: continue
        i80 = i80[0]; i20 = np.where(u[:i80 + 1] <= 0.2)[0]
        if len(i20) == 0: continue
        r.append(((tt[i80] - tt[i20[-1]]) * 1000, abs(pb - pa)))
    return np.array(r)


def hp(t, f0, a, b):
    return hece_perdesi(t, f0, a, b)[0]


gr = gecisler(tp, fp, lambda s: s["dest_start"], lambda s: s["dest_end"], lambda i: hp(tp, fp, S[i]["dest_start"], S[i]["dest_end"]))
gf = gecisler(tr, fr, lambda s: s["src_start"], lambda s: s["src_end"], lambda i: hp(tr, fr, S[i]["src_start"], S[i]["src_end"]))
oz = lambda g: {"gecis": int(len(g)), "sure_ortanca_ms": round(float(np.median(g[:, 0])), 1), "p25": round(float(np.percentile(g[:, 0], 25)), 1), "p75": round(float(np.percentile(g[:, 0], 75)), 1), "adim_ortanca_yarim_ses": round(float(np.median(g[:, 1])), 2),
                "hiz_ortanca_yarim_ses/sn": round(float(np.median(0.6 * g[:, 1] / (g[:, 0] / 1000 + 1e-9))), 1), "30ms_ve_alti_%": round(float((g[:, 0] <= 30).mean() * 100), 1)}
cik["a_gecis"] = {"reddedilen_psola": oz(gr), "referans": oz(gf)}
print("(a) nota geçişi %20-%80:", json.dumps(cik["a_gecis"], ensure_ascii=False))

# (b) düzey
db = lambda x: 10 * np.log10(np.mean(np.square(x)) + 1e-20); w = int(0.05 * FS)
rv2, _ = sf.read(REF_VOK, always_2d=True); re2, _ = sf.read(REF_ENS, always_2d=True); n = min(len(rv2), len(re2)); rv2 = rv2[:n]; re2 = re2[:n]; rv = rv2.mean(axis=1); re_ = re2.mean(axis=1)
env = np.sqrt(np.convolve(rv ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1; mask = np.zeros(n, bool)
for s in S: mask[int(s["src_start"] * FS):int(s["src_end"] * FS)] = True
kanal = lambda x, m: 10 * np.log10(np.mean(np.square(x[m])) + 1e-20)                       # iki kanalın ortalama gücü
hece_fark = np.array([db(rv[int(s["src_start"] * FS):int(s["src_end"] * FS)]) - db(re_[int(s["src_start"] * FS):int(s["src_end"] * FS)]) for s in S])
cik["b_referans"] = {"tek_kanal_toplam, kullanilan_hecelerde": round(db(rv[sesli & mask]) - db(re_[sesli & mask]), 1), "tek_kanal_toplam, tum_soylenen_kareler_(hayvan_sesleri_dahil)": round(db(rv[sesli]) - db(re_[sesli]), 1),
                     "kanal_basina_guc, kullanilan_hecelerde": round(kanal(rv2, sesli & mask) - kanal(re2, sesli & mask), 1), "hece_bazinda_ortanca": round(float(np.median(hece_fark)), 1), "hece_p10": round(float(np.percentile(hece_fark, 10)), 1), "hece_p90": round(float(np.percentile(hece_fark, 90)), 1),
                     "orkestra_stereo_genisligi_(yan/orta dB)": round(db((re2[:, 0] - re2[:, 1])[sesli] / 2) - db(re_[sesli]), 1), "vokal_stereo_(yan/orta dB)": round(db((rv2[:, 0] - rv2[:, 1])[sesli] / 2) - db(rv[sesli]), 1)}
print("(b) REFERANS vokal - orkestra (dB):", json.dumps(cik["b_referans"], ensure_ascii=False))
# reddedilen: bitmiş mp3'e en küçük kareler
wav = os.path.join(ARA, "red_karisim.wav")
if not os.path.exists(wav): subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", RED_MP3, "-ar", str(FS), "-c:a", "pcm_s16le", wav], check=True)
km2, _ = sf.read(wav, always_2d=True); b2, _ = sf.read(RED_BAND); e2, _ = sf.read(RED_EZGI); pad = np.zeros((int(ON * FS), 2)); ork2 = np.concatenate([pad, b2 + e2 * 10 ** (-4 / 20)]); v = oku_mono(RED_VOK)
n = min(len(km2), len(ork2), len(v)); km = km2[:n].mean(axis=1); ork = ork2[:n].mean(axis=1); v = v[:n]
# vokale mp3 zincirindeki yüksek geçiren uygulanır (sıkıştırma/yankı yok: yaklaşık)
vh = signal.sosfilt(signal.butter(2, 130, "highpass", fs=FS, output="sos"), v)
envv = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same")); ss = envv > envv.max() * 0.1
# mp3 gecikmesini bul
seg = slice(int(9 * FS), int(27 * FS)); c = signal.correlate(km[seg], ork[seg] + 3 * vh[seg], "full", "fft"); gec = int(np.argmax(np.abs(c)) - (seg.stop - seg.start - 1))
km = np.roll(km, -gec); Am = np.stack([ork[ss], vh[ss]], axis=1); g, *_ = np.linalg.lstsq(Am, km[ss], rcond=None); art = km[ss] - Am @ g
cik["b_reddedilen"] = {"mp3_gecikme_ornek": gec, "uydurulan_kazanc_orkestra": round(float(g[0]), 3), "uydurulan_kazanc_vokal": round(float(g[1]), 3), "aciklanan_varyans_%": round(float(100 * (1 - art.var() / km[ss].var())), 1),
                       "bitmis_mp3te_vokal - orkestra dB (söylenen karelerde)": round(db(g[1] * vh[ss]) - db(g[0] * ork[ss]), 1), "kanal_basina_guc_ile": round(db(g[1] * vh[ss]) - (kanal(ork2[:n], ss) + 20 * np.log10(abs(g[0]))), 1),
                       "orkestra_stereo_genisligi_(yan/orta dB)": round(db((ork2[:n, 0] - ork2[:n, 1])[ss] / 2) - db(ork[ss]), 1)}
hece_r = np.array([db(g[1] * vh[int(s["dest_start"] * FS):int(s["dest_end"] * FS)]) - db(g[0] * ork[int(s["dest_start"] * FS):int(s["dest_end"] * FS)]) for s in S])
cik["b_reddedilen"].update({"hece_bazinda_ortanca": round(float(np.median(hece_r)), 1), "hece_p10": round(float(np.percentile(hece_r, 10)), 1), "hece_p90": round(float(np.percentile(hece_r, 90)), 1)})
print("(b) REDDEDİLEN vokal - orkestra (dB):", json.dumps(cik["b_reddedilen"], ensure_ascii=False))
json.dump(cik, open(os.path.join(ARA, "07_gecis_ve_duzey.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
