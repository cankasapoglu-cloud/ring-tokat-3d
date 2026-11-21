#!/usr/bin/env python3
"""Soru 1 + 3: (a) orkestranın GERÇEKTEN duyulan vuruşları ızgaranın neresinde? (b) vokalin hece başlangıçları (ünlü girişi) ızgaranın ve
orkestranın gerçek vuruşlarının neresinde?  Aynı ölçüm iki tarafta:
  RED = reddedilen karışım (vokal_psola.wav; orkestra = 0.100 s dolgulu altyapi_G + ezgi_alti_G, karışımdaki gibi)
  REF = beğenilen v2_2 (MDX vokal kökü; MDX enstrüman kökü; ızgara = lattice.json)
Vuruş anı tanımı (lattice.json ile aynı): bant zarfının EN DİK YÜKSELDİĞİ an. Ünlü girişi: 250-4000 Hz zarfının hece başı-30 ms .. çekirdek arasında en dik yükseldiği an."""
import json, os, numpy as np
from scipy import signal
from ortak import *

Y = json.load(open(YERLESIM, encoding="utf8"))
BANTLAR = {"alt_120_300": (120, 300), "orta_300_2000": (300, 2000), "ust_2k_8k": (2000, 8000), "hava_8k_16k": (8000, 16000), "kick_40_120": (40, 120)}

def turev_zarf(x, lo, hi, ms=6.0):
    e, fe = zarf(bant(x, lo, hi), ms=ms); le = 20 * np.log10(e + 1e-5)
    d = np.gradient(signal.savgol_filter(le, 9, 2)) * fe / 1000.0          # dB/ms
    return e, d, fe

def orkestra_vuruslari(x, izgara, pencere=0.045):
    """Her ızgara noktası (sekizlik) için her bantta en dik yükselişin anı; yükseliş zayıfsa (o bantta vuruş yok) NaN."""
    cik = {}
    for ad, (lo, hi) in BANTLAR.items():
        e, d, fe = turev_zarf(x, lo, hi); t = np.full(len(izgara), np.nan); g = np.zeros(len(izgara))
        for i, tg in enumerate(izgara):
            a, b = int((tg - pencere) * fe), int((tg + pencere) * fe)
            if a < 0 or b >= len(d): continue
            j = a + np.argmax(d[a:b]); g[i] = d[j]
            # artış miktarı: tepe öncesi 20 ms ile sonrası 20 ms arasındaki dB farkı
            fark = 20 * np.log10((e[j:j + 20].max() + 1e-5) / (e[max(0, j - 25):max(1, j - 5)].mean() + 1e-5))
            if fark > 6 and j not in (a, b - 1): t[i] = j / fe
        cik[ad] = t
    return cik

def unlu_girisi(x, heceler, bas_anahtar, cek_anahtar, kaydirma=None):
    # taban: söylenen düzeyin 30 dB altı. (Tabansız log zarfında, kesilmiş parçanın dijital sessizlikten açılışı "en dik yükseliş" sanılıyordu:
    # 2. dizenin ilk hecesi RED'de 80-95 ms erken görünüyordu; bu ölçüm yapaylığıydı, taban ile giderildi.)
    xb = bant(x, 250, 4000); e, fe = zarf(xb, ms=8.0); taban = np.percentile(e[e > 1e-4], 95) * 10 ** (-30 / 20)
    le = 20 * np.log10(np.maximum(e, taban)); d = np.gradient(signal.savgol_filter(le, 9, 2)) * fe / 1000.0; sonuc = []
    for h in heceler:
        s = h[bas_anahtar] if kaydirma is None else h["dest_start"] - kaydirma[h["piece"]]
        c = h[cek_anahtar] if kaydirma is None else h["dest_nucleus"] - kaydirma[h["piece"]]
        a, b = int((s - 0.030) * fe), int(max(c, s + 0.03) * fe) + 1
        j = a + np.argmax(d[a:b]); sonuc.append(j / fe)
    return np.array(sonuc)

# ---- hece tablosu (çekirdek zamanlarıyla) ----
heceler = []
for L in Y["lines"]:
    for s in L["syllables"]:
        heceler.append(dict(s, verse=L["verse"], line=L["line"], piece=L["piece"], shift=L["shift_sec"], dest_bar_downbeat=L["dest_bar_downbeat"], src_bar_downbeat=L["src_bar_downbeat"]))
print("hece", len(heceler))

sonuc = {"tanim": __doc__}
# ================= RED =================
band = np.concatenate([np.zeros(int(ON * FS)), oku_mono(RED_BAND) + oku_mono(RED_EZGI) * 10 ** (-4 / 20)])
n8 = int((len(band) / FS - ON - 3.0) / (VURUS / 2)); izg_red = ON + np.arange(n8) * VURUS / 2
ov_red = orkestra_vuruslari(band, izg_red)
vok_red = oku_mono(RED_VOK); ug_red = unlu_girisi(vok_red, heceler, "dest_start", "dest_nucleus")
ug_dogal = unlu_girisi(oku_mono(os.path.join(A, "yeni4", "vokal", "vokal_dogal.wav")), heceler, "dest_start", "dest_nucleus")   # PSOLA öncesi yerleştirilmiş vokal
del band
# ================= REF =================
ens = oku_mono(REF_ENS); n8r = int((len(ens) / FS - 2.0 - REF_FAZ) / (REF_VURUS / 2)); izg_ref = REF_FAZ + np.arange(n8r) * REF_VURUS / 2
ov_ref = orkestra_vuruslari(ens, izg_ref)
vok_ref = oku_mono(REF_VOK); ug_ref = unlu_girisi(vok_ref, heceler, "src_start", "src_nucleus")
del ens

def orkestra_ozeti(ov, izg, ad):
    c = {}
    for b, t in ov.items():
        d = (t - izg) * 1000; vurus = np.arange(len(izg)) % 2 == 0
        c[b] = {"vurus_ustu": ozet(d[vurus]), "vurus_arasi_sekizlik": ozet(d[~vurus])}
    return c
sonuc["orkestra_gercek_vurus_eksi_izgara_ms"] = {"RED": orkestra_ozeti(ov_red, izg_red, "RED"), "REF": orkestra_ozeti(ov_ref, izg_ref, "REF")}

def en_yakin(t, adim, faz):
    k = np.round((t - faz) / adim); return (t - (faz + k * adim)) * 1000, k

def vokal_ozeti(ug, heceler, ov, izg, adim8, faz, bas_anahtar, olcu_anahtar, vurus):
    bas = np.array([h[bas_anahtar] for h in heceler])
    # ızgara yuvası: bölütlemenin verdiği yuva (beat_in_bar, 16'lık çözünürlük) -> o ölçünün başı + beat_in_bar * vuruş
    yuva = np.array([h[olcu_anahtar] + h["beat_in_bar"] * vurus for h in heceler])
    d_unlu_yuva = (ug - yuva) * 1000; d_bas_yuva = (bas - yuva) * 1000
    d8, k8 = en_yakin(ug, adim8, faz); d16, _ = en_yakin(ug, adim8 / 2, faz)
    # orkestranın gerçek vuruşuna göre: hecenin yuvası sekizlik üstündeyse o yuvadaki gerçek orkestra vuruşu (üst bant = hi-hat/trampet; alt bant = bas/kick tıkı)
    c = {"unlu_girisi_eksi_kendi_yuvasi_ms": ozet(d_unlu_yuva), "hece_basi(unsuz)_eksi_kendi_yuvasi_ms": ozet(d_bas_yuva),
         "unlu_girisi_eksi_en_yakin_sekizlik_ms": ozet(d8), "unlu_girisi_eksi_en_yakin_onaltilik_ms": ozet(d16)}
    for b in ("ust_2k_8k", "hava_8k_16k", "alt_120_300", "orta_300_2000", "kick_40_120"):
        fark = []
        for i, h in enumerate(heceler):
            q = (yuva[i] - faz) / adim8; qi = int(round(q))
            if abs(q - qi) > 0.05 or qi < 0 or qi >= len(izg): continue          # yalnız sekizlik yuvalarındaki heceler
            if not np.isnan(ov[b][qi]): fark.append((ug[i] - ov[b][qi]) * 1000)
        c["unlu_girisi_eksi_orkestranin_gercek_vurusu_ms[%s]" % b] = ozet(fark)
    # yuva türüne göre
    bib = np.array([h["beat_in_bar"] for h in heceler]); tur = np.where(bib % 1 == 0, "vurus", np.where(bib % 0.5 == 0, "sekizlik", "onaltilik"))
    c["yuva_turune_gore_unlu_girisi_eksi_yuva_ms"] = {t: ozet(d_unlu_yuva[tur == t]) for t in ("vurus", "sekizlik", "onaltilik")}
    c["satira_gore"] = {l: ozet(d_unlu_yuva[np.array([h["line"] == l for h in heceler])]) for l in ("L1", "L2", "diye", "L4")}
    return c, d_unlu_yuva
sonuc["vokal"] = {}
sonuc["vokal"]["RED"], dr = vokal_ozeti(ug_red, heceler, ov_red, izg_red, VURUS / 2, ON, "dest_start", "dest_bar_downbeat", VURUS)
# REF: hecenin kaynak ölçüsü = src_bar_downbeat (L4 ve diye için parça çapası bir ölçü önce olabilir; yuva = hedef yuvası - kaydırma ile aynıdır)
for h in heceler: h["src_slot_bar"] = h["dest_bar_downbeat"] - h["shift"] if False else None
ref_yuva_bar = []
for h in heceler:
    # hedefteki yuva zamanı eksi parçanın kaydırması = kaynaktaki yuva zamanı (kesme + tam örnek kaydırma)
    ref_yuva_bar.append(h["dest_grid_time"] - h["shift"] - h["beat_in_bar"] * REF_VURUS)
for h, v in zip(heceler, ref_yuva_bar): h["ref_bar"] = v
sonuc["vokal"]["REF"], df = vokal_ozeti(ug_ref, heceler, ov_ref, izg_ref, REF_VURUS / 2, REF_FAZ, "src_start", "ref_bar", REF_VURUS)
fark = dr - df
sonuc["ayni_hece_RED_eksi_REF_ms"] = dict(ozet(fark), aciklama="aynı 229 hecenin ünlü girişi - kendi yuvası; RED eksi REF. 0'a yakınsa kesip yerleştirme ve PSOLA hece zamanlamasını bozmamıştır.")
sonuc["PSOLA_etkisi_ayni_hece_psola_eksi_dogal_ms"] = dict(ozet((ug_red - ug_dogal) * 1000), aciklama="aynı hecenin ünlü girişi: vokal_psola.wav eksi vokal_dogal.wav (perde kaydırma zamanlamayı oynattı mı?)")
print("PSOLA etkisi:", sonuc["PSOLA_etkisi_ayni_hece_psola_eksi_dogal_ms"])
json.dump({"heceler": [{"verse": h["verse"], "line": h["line"], "index": h["index"], "text": h["text"], "beat_in_bar": h["beat_in_bar"], "red_unlu": round(float(a), 4), "ref_unlu": round(float(b), 4),
                        "red_eksi_yuva_ms": round(float(x), 1), "ref_eksi_yuva_ms": round(float(z), 1)} for h, a, b, x, z in zip(heceler, ug_red, ug_ref, dr, df)]},
          open(os.path.join(ARA, "02_hece_unlu_girisleri.json"), "w"), ensure_ascii=False, indent=0)
json.dump(sonuc, open(os.path.join(ARA, "02_vurus_izgara.json"), "w"), ensure_ascii=False, indent=1)

def yaz(o): return "n=%d ortanca %+.1f ort %+.1f ss %.1f [p10 %+.1f p90 %+.1f] |x|ortanca %.1f, 30ms içi %%%.0f, 50ms içi %%%.0f" % (o["n"], o["ortanca"], o["ortalama"], o["ss"], o["p10"], o["p90"], o["mutlak_ortanca"], o["yuzde_30ms_ici"], o["yuzde_50ms_ici"]) if o["n"] else "n=0"
for taraf in ("RED", "REF"):
    print("=====", taraf, "orkestranın gerçek vuruşu - ızgara (ms)")
    for b, v in sonuc["orkestra_gercek_vurus_eksi_izgara_ms"][taraf].items():
        print("  %-14s vuruş üstü: %s" % (b, yaz(v["vurus_ustu"]))); print("  %-14s sekizlik  : %s" % ("", yaz(v["vurus_arasi_sekizlik"])))
    print("=====", taraf, "vokal")
    for k, v in sonuc["vokal"][taraf].items():
        if "n" in v: print("  %-62s %s" % (k, yaz(v)))
        else:
            for kk, vv in v.items(): print("  %-62s %s" % (k[:40] + ":" + kk, yaz(vv)))
print("aynı hece RED-REF:", yaz(sonuc["ayni_hece_RED_eksi_REF_ms"]))
