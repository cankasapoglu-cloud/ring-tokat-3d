#!/usr/bin/env python3
"""SORU 1: Orkestra A=440'ta mı, vokal orkestranın akorduna göre kaç sent sapıyor (hece hece)?
Aynı ölçüm sevilen referansa (v2_2: ayrılmış vokal + ayrılmış orkestra) da uygulanır.
Yöntemler:
  (a) klarnet (ezgi_alti) notaları: bilinen her nota için, nota başından 50 ms sonra 180 ms'lik pencerede sıfır dolgulu FFT,
      beklenen temel frekansın +-1 yarım ses çevresinde tepe (parabolik ara değer) -> sent (A=440 eşit aralıklı diziye göre)
  (b) bas (yalın dokulu hayvan ölçüleri): aynı tepe ölçümü, G2'nin 2. ve 3. armoniği
  (c) tüm orkestra: librosa.estimate_tuning (aynı ayarlarla reddedilen orkestra ve referans orkestra)
  (d) vokal: Praat f0, hece çekirdeği ortancası -> hedef notadan ve en yakın yarım sesten sapma
Çıktı: ara/01_akort.json + ekrana özet."""
import json, os, numpy as np, librosa
from ortak import *

Y, S, Z = yukle(); cik = {}


def tepe_sent(x, t0, sure, f_bek, yari=1.0):
    a = int(t0 * FS); n = int(sure * FS); seg = x[a:a + n]
    if len(seg) < n or np.sqrt(np.mean(seg ** 2)) < 1e-5: return np.nan
    N = 1 << 18; sp = np.abs(np.fft.rfft(seg * np.hanning(n), N)); fr = np.fft.rfftfreq(N, 1 / FS)
    lo, hi = f_bek * 2 ** (-yari / 12), f_bek * 2 ** (yari / 12); m = np.where((fr >= lo) & (fr <= hi))[0]
    i = m[np.argmax(sp[m])]
    if i in (m[0], m[-1]): return np.nan
    y0, y1, y2 = np.log(sp[i - 1:i + 2] + 1e-20); d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2); f = (i + d) * FS / N
    return 1200 * np.log2(f / f_bek)


# (a) klarnet
ez = oku_mono(RED_EZGI); sent = []; nota_bazli = {}
for n in Z["ezgi_notalari"]:
    if n["parti"] == "ezgi_alti" and n["enstruman"] == "klarnet":
        f = 440 * 2 ** ((n["midi"] - 69) / 12); c = tepe_sent(ez, n["baslangic"] + 0.05, 0.18, f)
        if not np.isnan(c): sent.append(c); nota_bazli.setdefault(n["nota"], []).append(c)
sent = np.array(sent)
cik["klarnet"] = {"nota_sayisi": int(len(sent)), "ortanca_sent": round(float(np.median(sent)), 1), "p10": round(float(np.percentile(sent, 10)), 1), "p90": round(float(np.percentile(sent, 90)), 1),
                  "nota_bazli_ortanca": {k: round(float(np.median(v)), 1) for k, v in nota_bazli.items()}}
print("(a) klarnet (ezgi_alti) %d nota: A=440'a göre ortanca %+.1f sent (p10 %+.1f, p90 %+.1f); nota bazında %s" % (len(sent), np.median(sent), np.percentile(sent, 10), np.percentile(sent, 90), cik["klarnet"]["nota_bazli_ortanca"]))

# (b) bas: hayvan ölçülerinde (kıta içi ö3, ö4) vuruş 0'dan 80 ms sonra 300 ms
band = oku_mono(RED_BAND); bs = {2: [], 3: []}
for k in Z["kitalar"]:
    for ob in (k["olcu_baslangiclari"][3], k["olcu_baslangiclari"][4]):
        for v in range(4):
            for h in (2, 3):
                c = tepe_sent(band, ob + v * VURUS + 0.08, 0.30, 98.0 * h * (440 * 2 ** ((43 - 69) / 12)) / 98.0, yari=0.7)
                if not np.isnan(c): bs[h].append(c)
cik["bas"] = {"armonik_%d" % h: {"n": len(v), "ortanca_sent": round(float(np.median(v)), 1), "p10": round(float(np.percentile(v, 10)), 1), "p90": round(float(np.percentile(v, 90)), 1)} for h, v in bs.items() if v}
print("(b) bas G2 (yalın ölçüler):", cik["bas"])


# (c) tüm orkestra: librosa.estimate_tuning, 22.05 kHz, 60 s'lik kesit (aynı ayar iki kayıtta)
def ton(x, bas, sure=60.0):
    y = librosa.resample(x[int(bas * FS):int((bas + sure) * FS)], orig_sr=FS, target_sr=22050)
    yh = librosa.effects.harmonic(y, margin=4.0)
    return float(librosa.estimate_tuning(y=yh, sr=22050, n_fft=8192, resolution=0.01, fmin=120, fmax=2000)) * 100


ref_ens = oku_mono(REF_ENS)
ez_pad = ez * 10 ** (-4 / 20)
cik["orkestra_librosa_sent"] = {"reddedilen_altyapi+ezgi_9-69s": round(ton(band + ez_pad, 9.14), 1), "reddedilen_altyapi+ezgi_69-129s": round(ton(band + ez_pad, 69.0), 1),
                                "referans_orkestra_8-68s": round(ton(ref_ens, 8.57), 1), "referans_orkestra_68-128s": round(ton(ref_ens, 68.0), 1)}
print("(c) librosa.estimate_tuning (sent, A=440'a göre):", cik["orkestra_librosa_sent"])

# (d) vokal
t, f0 = f0_izi(RED_VOK, "red_psola"); td, f0d = f0_izi(DOGAL_VOK, "dogal"); tr, f0r = f0_izi(REF_VOK, "ref_vokal")
band_sent = float(np.median(sent))
sat = []
for s in S:
    m, n = hece_perdesi(t, f0, s["dest_start"], s["dest_end"]); md, _ = hece_perdesi(td, f0d, s["dest_start"], s["dest_end"]); mr, _ = hece_perdesi(tr, f0r, s["src_start"], s["src_end"])
    sat.append({"kita": s["verse"], "satir": s["line"], "sira": s["index"], "hece": s["text"], "zaman": round(s["dest_start"], 3), "sure_ms": round((s["dest_end"] - s["dest_start"]) * 1000),
                "hedef": s["hedef"], "olculen_midi": None if np.isnan(m) else round(m, 3), "sesli_kare": n,
                "hedeften_sent": None if np.isnan(m) else round((m - s["hedef"]) * 100, 1), "orkestraya_gore_sent": None if np.isnan(m) else round((m - s["hedef"]) * 100 - band_sent, 1),
                "dogal_midi": None if np.isnan(md) else round(md, 3), "ref_midi": None if np.isnan(mr) else round(mr, 3), "yerlesim_midi": s["midi"]})
cik["heceler"] = sat
e = np.array([x["orkestraya_gore_sent"] for x in sat if x["orkestraya_gore_sent"] is not None]); ae = np.abs(e)
# referans: orkestranın librosa akordu çıkarılır, en yakın yarım sesten sapma (aynı ölçüm reddedilen vokale de uygulanır)
ref_ton = np.mean([cik["orkestra_librosa_sent"]["referans_orkestra_8-68s"], cik["orkestra_librosa_sent"]["referans_orkestra_68-128s"]])
red_ton = np.mean([cik["orkestra_librosa_sent"]["reddedilen_altyapi+ezgi_9-69s"], cik["orkestra_librosa_sent"]["reddedilen_altyapi+ezgi_69-129s"]])
def yakin(ms, ton_sent):
    ms = np.array([m for m in ms if m is not None]); c = (ms - ton_sent / 100); return (c - np.round(c)) * 100
yr = yakin([x["ref_midi"] for x in sat], ref_ton); yp = yakin([x["olculen_midi"] for x in sat], red_ton); ydg = yakin([x["dogal_midi"] for x in sat], ref_ton)
oz = lambda a: {"n": int(len(a)), "ortanca": round(float(np.median(a)), 1), "mutlak_ortanca": round(float(np.median(np.abs(a))), 1), "mutlak_p90": round(float(np.percentile(np.abs(a), 90)), 1),
                "en_cok": round(float(np.abs(a).max()), 1), "25_sentten_fazla": int((np.abs(a) > 25).sum()), "40_sentten_fazla": int((np.abs(a) > 40).sum())}
cik["vokal_hedeften_sapma_(klarnet_akorduna_gore)"] = oz(e)
cik["en_yakin_yarim_sesten_sapma"] = {"reddedilen_vokal_psola_(kendi_orkestrasinin_akorduna_gore)": oz(yp), "referans_vokal_(kendi_orkestrasinin_akorduna_gore)": oz(yr), "dogal_yerlesim_(referans_akorduna_gore)": oz(ydg),
                                      "ref_akort_sent": round(float(ref_ton), 1), "red_akort_sent": round(float(red_ton), 1)}
print("(d) reddedilen vokal, hedef notadan sapma (klarnet akorduna göre):", cik["vokal_hedeften_sapma_(klarnet_akorduna_gore)"])
print("    en yakın yarım sesten sapma:", json.dumps(cik["en_yakin_yarim_sesten_sapma"], ensure_ascii=False))
kotu = sorted([x for x in sat if x["orkestraya_gore_sent"] is not None], key=lambda x: -abs(x["orkestraya_gore_sent"]))[:15]
print("    en çok sapan 15 hece:")
for x in kotu: print("      K%d %-4s #%d %-5s t=%.2f s (%d ms)  hedef %s  ölçülen %.2f  sapma %+.0f sent" % (x["kita"], x["satir"], x["sira"], x["hece"], x["zaman"], x["sure_ms"], ad(x["hedef"]), x["olculen_midi"], x["orkestraya_gore_sent"]))
olc = [x for x in sat if x["olculen_midi"] is None]; print("    perdesi ölçülemeyen hece:", len(olc), [(x["kita"], x["satir"], x["hece"]) for x in olc])
# ölçüm güveni: aynı heceler için bu betiğin 'ref' ölçümü ile yerlesim.json'daki özgün midi farkı
df = np.array([x["ref_midi"] - x["yerlesim_midi"] for x in sat if x["ref_midi"] is not None and x["yerlesim_midi"] is not None]) * 100
cik["olcum_denetimi_ref_vs_yerlesim_sent"] = {"mutlak_ortanca": round(float(np.median(np.abs(df))), 1), "mutlak_p90": round(float(np.percentile(np.abs(df), 90)), 1)}
print("    denetim: bu ölçüm ile yerlesim.json özgün perde farkı |ortanca| %.1f sent, p90 %.1f sent" % (np.median(np.abs(df)), np.percentile(np.abs(df), 90)))
json.dump(cik, open(os.path.join(ARA, "01_akort.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
