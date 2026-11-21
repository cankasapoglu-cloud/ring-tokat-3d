#!/usr/bin/env python3
"""SORU 3 (ek deney): Bu şarkıcının sesinde TD-PSOLA kaydırma büyüklüğü -> ölçülen hasar eğrisi.
İşlenmemiş yerleşimden (vokal_dogal.wav) sesli çekirdeği >= 150 ms olan heceler alınır; her biri Praat PSOLA (03_psola.py ile aynı
'To Manipulation 0.005 150 720' + overlap-add) ile SABİT bir miktarda kaydırılır: -9 .. +9 yarım ses. Her sonuçta aynı ölçümler:
HNR (cc), jitter, shimmer, CPP. Taban = kaydırmasız yeniden sentez (0). Böylece 'şu ton şu kadar hasar verir' tahmini yapılabilir.
Çıktı: ara/05_doz_tepki.json. Hiçbir ses dosyası yazılmaz."""
import json, os, warnings, numpy as np, parselmouth
warnings.filterwarnings('ignore')
from parselmouth.praat import call
from ortak import *


def cpp_db(seg, fs=FS, f_lo=150, f_hi=900):
    n = int(0.04 * fs); h = int(0.01 * fs); r = []
    if len(seg) < n: return np.nan
    for a in range(0, len(seg) - n + 1, h):
        x = seg[a:a + n] * np.hanning(n); N = 4096
        ls = 20 * np.log10(np.abs(np.fft.rfft(x, N)) + 1e-9); ls = ls[: int(5000 / (fs / N))]
        c = np.abs(np.fft.irfft(ls)); q = np.arange(len(c)) / (2 * 5000.0); cd = 20 * np.log10(c + 1e-9)
        m = (q >= 1.0 / f_hi) & (q <= 1.0 / f_lo); g = (q >= 0.001) & (q <= 0.02); p = np.polyfit(q[g], cd[g], 1); i = np.where(m)[0][np.argmax(cd[m])]; r.append(cd[i] - np.polyval(p, q[i]))
    return float(np.mean(r)) if r else np.nan


Y, S, Z = yukle(); x = oku_mono(DOGAL_VOK); t, f0 = f0_izi(DOGAL_VOK, "dogal")
KAY = [-9, -7, -5, -3, -1, 0, 1, 3, 5, 7, 9]; sonuc = {k: [] for k in KAY}; ham = []; sec = []
for s in S:
    m = (t >= s["dest_start"]) & (t < s["dest_end"]) & (f0 > 0)
    if m.sum() * 5 >= 150: sec.append((s, t[m][0], t[m][-1] + 0.005))
print("deney heceleri:", len(sec), "/", len(S))
for s, ca, cb in sec:
    a = int((ca - 0.08) * FS); b = int((cb + 0.08) * FS); seg = x[a:b]; snd = parselmouth.Sound(seg, sampling_frequency=FS); k15 = (cb - ca) * 0.15
    def olc(sn, f_orta):
        lo = max(120.0, f_orta * 0.6); hi = min(1200.0, f_orta * 1.7); c0, c1 = 0.08 + k15, 0.08 + (cb - ca) - k15
        har = sn.to_harmonicity_cc(time_step=0.01, minimum_pitch=lo, silence_threshold=0.1, periods_per_window=1.0); th = har.xs(); hv = har.values[0]; hm = (th >= c0) & (th < c1) & (hv > -100)
        part = sn.extract_part(from_time=c0 - 0.01, to_time=c1 + 0.01); pp = call(part, "To PointProcess (periodic, cc)", lo, hi)
        try: ji = 100 * call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3); sh = 100 * call([part, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        except Exception: ji = sh = np.nan
        y = sn.values[0]; return (float(np.mean(hv[hm])) if hm.sum() else np.nan, ji, sh, cpp_db(y[int(c0 * FS):int(c1 * FS)]))
    fm = float(np.median(f0[(t >= ca) & (t < cb) & (f0 > 0)])); o0 = olc(snd, fm); ham.append(o0)
    man = call(snd, "To Manipulation", 0.005, 150, 720); pt0 = call(man, "Extract pitch tier")       # özgün perde katmanı bir kez alınır
    for k in KAY:
        pt = call(pt0, "Copy", "kopya"); call(pt, "Multiply frequencies", 0, snd.duration, 2 ** (k / 12.0)); call([pt, man], "Replace pitch tier")
        y = call(man, "Get resynthesis (overlap-add)"); sonuc[k].append(olc(y, fm * 2 ** (k / 12.0)))
ham = np.array(ham); cik = {"hece": len(sec), "aciklama": "fark = kaydırılmış - kaydırmasız yeniden sentez (aynı hece), ortanca [p25..p75]", "egri": {}}
taban = np.array(sonuc[0])
print(" kaydırma   HNR farkı (dB)          jitter farkı (%)       shimmer farkı (%)      CPP farkı (dB)     | mutlak ortanca HNR / jitter / shimmer")
for k in KAY:
    v = np.array(sonuc[k]); d = v - taban; q = lambda j: (float(np.nanmedian(d[:, j])), float(np.nanpercentile(d[:, j], 25)), float(np.nanpercentile(d[:, j], 75)))
    cik["egri"][str(k)] = {"hnr_fark_db": [round(z, 2) for z in q(0)], "jitter_fark": [round(z, 2) for z in q(1)], "shimmer_fark": [round(z, 2) for z in q(2)], "cpp_fark_db": [round(z, 2) for z in q(3)],
                           "hnr_ortanca": round(float(np.nanmedian(v[:, 0])), 2), "jitter_ortanca": round(float(np.nanmedian(v[:, 1])), 2), "shimmer_ortanca": round(float(np.nanmedian(v[:, 2])), 2), "cpp_ortanca": round(float(np.nanmedian(v[:, 3])), 2),
                           "hnr_3dB_dusen_hece_%": round(float((d[:, 0] <= -3).mean() * 100), 1)}
    print("   %+3d     %+5.2f [%+5.2f..%+5.2f]   %+5.2f [%+5.2f..%+5.2f]   %+5.2f [%+5.2f..%+5.2f]   %+5.2f [%+5.2f..%+5.2f] |  %5.2f / %4.2f / %4.2f   (HNR 3 dB+ düşen %%%.0f)" % ((k,) + q(0) + q(1) + q(2) + q(3) + (np.nanmedian(v[:, 0]), np.nanmedian(v[:, 1]), np.nanmedian(v[:, 2]), (d[:, 0] <= -3).mean() * 100)))
cik["islenmemis_ortanca"] = {"hnr": round(float(np.nanmedian(ham[:, 0])), 2), "jitter": round(float(np.nanmedian(ham[:, 1])), 2), "shimmer": round(float(np.nanmedian(ham[:, 2])), 2), "cpp": round(float(np.nanmedian(ham[:, 3])), 2)}
print(" işlenmemiş (PSOLA'sız) ortanca:", cik["islenmemis_ortanca"], "| kaydırmasız yeniden sentez:", {"hnr": cik["egri"]["0"]["hnr_ortanca"], "jitter": cik["egri"]["0"]["jitter_ortanca"], "shimmer": cik["egri"]["0"]["shimmer_ortanca"]})
json.dump(cik, open(os.path.join(ARA, "05_doz_tepki.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
