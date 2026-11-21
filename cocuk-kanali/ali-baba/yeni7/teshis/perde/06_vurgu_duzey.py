#!/usr/bin/env python3
"""Ek ölçümler (perde - gürlük - tını ilişkisi ve eşlik ezgisinin duyulurluğu):
 (a) Doğal söyleyişte perde yükseldikçe ses gürleşir ve parlaklaşır. Özgün kayıtta (ONCE) hece düzeyi / parlaklığı ile perde ilişkisi;
     PSOLA sonrası aynı hecelerin YENİ perdesiyle ilişkisi (PSOLA gürlüğü ve tınıyı değiştirmez, yalnız perdeyi).
     parlaklık = 2-5 kHz enerjisi / 0.2-1 kHz enerjisi (dB), hece çekirdeğinde.
 (b) Satır başı heceleri (yeni ezginin en güçlü vuruşu, 'do'): düzey, sesli süre, HNR; diğer hecelerle kıyas.
 (c) Karışımda eşlik ezgisinin (klarnet + glockenspiel, ezgi_alti -4 dB) vokale ve orkestraya göre düzeyi (söylenen karelerde);
     aynı ölçüm referansta: ayrılmış vokal / ayrılmış orkestra düzey farkı (söylenen karelerde).
 (d) Vokal steminde 200 Hz altı (vokalin temel frekansının altı = yalnız eski orkestradan sızıntı olabilir) enerji payı.
Çıktı: ara/06_vurgu_duzey.json"""
import json, os, subprocess, numpy as np
from scipy import signal
from ortak import *

Y, S, Z = yukle(); cik = {}
dogal = oku_mono(DOGAL_VOK); psola = oku_mono(RED_VOK); t, f0 = f0_izi(DOGAL_VOK, "dogal"); tp, f0p = f0_izi(RED_VOK, "red_psola")
db = lambda x: 10 * np.log10(np.mean(np.square(x)) + 1e-20)


def bant_db(seg, lo, hi):
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2; fr = np.fft.rfftfreq(len(seg), 1 / FS); return 10 * np.log10(sp[(fr >= lo) & (fr < hi)].sum() + 1e-20)


sat = []
for s in S:
    m = (t >= s["dest_start"]) & (t < s["dest_end"]) & (f0 > 0)
    if m.sum() < 6: sat.append(None); continue
    ca, cb = t[m][0], t[m][-1] + 0.005; seg = dogal[int(ca * FS):int(cb * FS)]; segp = psola[int(ca * FS):int(cb * FS)]
    sat.append({"duzey": db(seg), "duzey_p": db(segp), "parlak": bant_db(seg, 2000, 5000) - bant_db(seg, 200, 1000), "parlak_p": bant_db(segp, 2000, 5000) - bant_db(segp, 200, 1000), "sesli_ms": m.sum() * 5.0,
                "ozgun": s["midi"], "hedef": s["hedef"], "bas": s["index"] == 0 and s["line"] in ("L1", "L2", "L4"), "satir": s["line"], "sira": s["index"]})
v = [x for x in sat if x]; A = lambda k: np.array([x[k] for x in v], float)
r = lambda a, b: round(float(np.corrcoef(a, b)[0, 1]), 2); egim = lambda a, b: round(float(np.polyfit(a, b, 1)[0]), 2)
cik["a_perde_gurluk_tini"] = {"ozgun_perde~duzey_r": r(A("ozgun"), A("duzey")), "ozgun_perde~duzey_egim_dB/yarim_ses": egim(A("ozgun"), A("duzey")), "ozgun_perde~parlaklik_r": r(A("ozgun"), A("parlak")), "ozgun_perde~parlaklik_egim_dB/yarim_ses": egim(A("ozgun"), A("parlak")),
                             "yeni_perde~duzey_r_(psola)": r(A("hedef"), A("duzey_p")), "yeni_perde~duzey_egim": egim(A("hedef"), A("duzey_p")), "yeni_perde~parlaklik_r_(psola)": r(A("hedef"), A("parlak_p")), "yeni_perde~parlaklik_egim": egim(A("hedef"), A("parlak_p"))}
print("(a)", json.dumps(cik["a_perde_gurluk_tini"], ensure_ascii=False))
# yeni ezgide notaya göre düzey: G4 (do) / E4 / D4
cik["a_nota_bazli"] = {}
for nota, ad_ in ((67, "G4_do"), (64, "E4_la"), (62, "D4_sol")):
    g = [x for x in v if x["hedef"] == nota]; cik["a_nota_bazli"][ad_] = {"hece": len(g), "duzey_ort_dB": round(float(np.mean([x["duzey_p"] for x in g])), 1), "parlaklik_ort_dB": round(float(np.mean([x["parlak_p"] for x in g])), 1), "ozgun_perde_ort": round(float(np.mean([x["ozgun"] for x in g])), 2)}
ogG = [x for x in v if abs(x["ozgun"] - 67) < 0.5]; ogD = [x for x in v if abs(x["ozgun"] - 62) < 0.6]
cik["a_nota_bazli"]["ozgunde_G4_soylenenler"] = {"hece": len(ogG), "duzey_ort_dB": round(float(np.mean([x["duzey"] for x in ogG])), 1), "parlaklik_ort_dB": round(float(np.mean([x["parlak"] for x in ogG])), 1)}
cik["a_nota_bazli"]["ozgunde_D4_soylenenler"] = {"hece": len(ogD), "duzey_ort_dB": round(float(np.mean([x["duzey"] for x in ogD])), 1), "parlaklik_ort_dB": round(float(np.mean([x["parlak"] for x in ogD])), 1)}
print("    ", json.dumps(cik["a_nota_bazli"], ensure_ascii=False))
# (b) satır başı heceleri
H3 = json.load(open(os.path.join(ARA, "03_psola_hasar.json"), encoding="utf8"))["hece_bazli"]
bas = [i for i, x in enumerate(sat) if x and x["bas"]]; dig = [i for i, x in enumerate(sat) if x and not x["bas"]]
def oz(idx):
    return {"hece": len(idx), "duzey_ort_dB": round(float(np.mean([sat[i]["duzey_p"] for i in idx])), 1), "sesli_ms_ortanca": float(np.median([sat[i]["sesli_ms"] for i in idx])), "hnr_sonra_ortanca": round(float(np.nanmedian([H3[i]["sonra_hnr_db"] or np.nan for i in idx])), 1),
            "jitter_sonra_ortanca": round(float(np.nanmedian([H3[i]["sonra_jitter_%"] or np.nan for i in idx])), 2), "kaydirma_ort": round(float(np.mean([H3[i]["kaydirma"] for i in idx])), 2), "parlaklik_ort_dB": round(float(np.mean([sat[i]["parlak_p"] for i in idx])), 1)}
cik["b_satir_basi"] = {"satir_basi_(L1,L2,L4 ilk hece; yeni ezgide 1. vuruştaki 'do')": oz(bas), "diger_heceler": oz(dig), "ayni_notadaki_(G4)_diger_heceler": oz([i for i in dig if sat[i]["hedef"] == 67])}
print("(b)", json.dumps(cik["b_satir_basi"], ensure_ascii=False))

# (c) düzeyler
band, _ = None, None
import soundfile as sf
b2, _ = sf.read(RED_BAND); e2, _ = sf.read(RED_EZGI); pad = np.zeros((int(ON * FS), 2)); band = np.concatenate([pad, b2]); ezgi = np.concatenate([pad, e2]) * 10 ** (-4 / 20)
n = max(len(band), len(psola)); band = np.pad(band, ((0, n - len(band)), (0, 0))); ezgi = np.pad(ezgi, ((0, n - len(ezgi)), (0, 0))); vv = np.pad(psola, (0, n - len(psola)))
w = int(0.05 * FS); env = np.sqrt(np.convolve(vv ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1
zemin = (band + ezgi).mean(axis=1); bm = band.mean(axis=1); em = ezgi.mean(axis=1)
# ezgi_alti'nın çaldığı VE vokalin söylediği kareler
ecal = np.sqrt(np.convolve(em ** 2, np.ones(w) / w, "same")) > 1e-4; k = sesli & ecal
# klarnetin temel bölgesi (550-850 Hz) içinde orkestra ile kıyas
sos = signal.butter(4, [550, 850], "bandpass", fs=FS, output="sos"); bmb = signal.sosfiltfilt(sos, bm); emb = signal.sosfiltfilt(sos, em)
cik["c_duzey_reddedilen"] = {"vokal_orkestra_farki_dB_(04_karisim.py hedefi)": 8.5, "ezgi_alti - orkestra (söylenen karelerde, geniş bant) dB": round(db(em[k]) - db(bm[k]), 1), "ezgi_alti - vokal dB (yaklaşık)": round(db(em[k]) - db(zemin[k]) - 8.5, 1),
                             "ezgi_alti - orkestra 550-850 Hz (klarnetin temel bölgesi) dB": round(db(emb[k]) - db(bmb[k]), 1), "soylenen_kare_sn": round(float(sesli.sum() / FS), 1)}
rv = oku_mono(REF_VOK); re_ = oku_mono(REF_ENS); n2 = min(len(rv), len(re_)); rv = rv[:n2]; re_ = re_[:n2]
envr = np.sqrt(np.convolve(rv ** 2, np.ones(w) / w, "same")); sr_ = envr > envr.max() * 0.1
# yalnız kullanılan heceler (hayvan sesleri hariç): kaynak zamanları
mask = np.zeros(n2, bool)
for s in S: mask[int(s["src_start"] * FS):int(s["src_end"] * FS)] = True
kk = sr_ & mask
cik["c_duzey_referans"] = {"vokal - orkestra dB (ayrılmış stemler, söylenen hecelerde)": round(db(rv[kk]) - db(re_[kk]), 1), "soylenen_kare_sn": round(float(kk.sum() / FS), 1)}
print("(c)", json.dumps(cik["c_duzey_reddedilen"], ensure_ascii=False), json.dumps(cik["c_duzey_referans"], ensure_ascii=False))

# (d) 200 Hz altı sızıntı (işlenmemiş yerleşim, söylenen kareler)
sosl = signal.butter(6, 200, "lowpass", fs=FS, output="sos"); lo = signal.sosfiltfilt(sosl, dogal); sd = np.zeros(len(dogal), bool)
for s in S: sd[int(s["dest_start"] * FS):int(s["dest_end"] * FS)] = True
cik["d_sizinti"] = {"200Hz_alti - tum_bant dB (söylenen hecelerde)": round(db(lo[sd]) - db(dogal[sd]), 1), "kiyaslama": "yerlesim.json: kıtalar arasında (vokal yokken) stem artığı söylenen düzeyin %s dB altında" % Y["summary"]["noise_floor"]["stem_between_verses_db_re_sung"]}
print("(d)", json.dumps(cik["d_sizinti"], ensure_ascii=False))
json.dump(cik, open(os.path.join(ARA, "06_vurgu_duzey.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
