#!/usr/bin/env python3
"""Soru 4 (başka ritmik etkenler), iki tarafta aynı ölçüm:
 a) salınım (swing): vuruş arası sekizliğin vuruş içindeki yeri (%50 = düz), orkestra ve vokal
 b) orkestranın ölçü içi vuruş deseni: söylenen ölçülerde 16'lık yuvalara düşen vuruş gücü (pes / orta / tiz bant)
    UYARI: bu ölçümün "onaltılık" sayıları GÜVENİLİR DEĞİL (log zarfın küçük dalgalanmalarını da topluyor; 09_alt_bolunme.py ile bitmiş
    karışımda doğrulanamadı: REF onaltılık/sekizlik = 0.01). Yalnız "vuruş arası sekizlik / vuruş" oranı iki yöntemde de aynı yöne çıktı.
 c) hece uzunlukları ve ezgi notası uzunlukları
 d) dize sonu: son hecenin bitişinden sonra vokal düzeyi ne kadar hızlı düşüyor (kuyruk)
 e) vokalin altındaki ezginin (ezgi_alti) karışımdaki düzeyi (duyulur mu?)
 f) hayvan seslerinin ölçü başına göre gerçek başlangıcı"""
import json, os, numpy as np
from scipy import signal
from ortak import *

Y = json.load(open(YERLESIM, encoding="utf8")); Z = json.load(open(ZAMAN, encoding="utf8"))
V2 = json.load(open(os.path.join(ARA, "02_vurus_izgara.json"))); U = json.load(open(os.path.join(ARA, "02_hece_unlu_girisleri.json")))["heceler"]
sonuc = {"tanim": __doc__}
# ---------- a) salınım ----------
def sal(ms, vurus): return round(50 + ms / (vurus * 1000) * 100, 1)
o = V2["orkestra_gercek_vurus_eksi_izgara_ms"]
sonuc["a_salinim_yuzde(50=duz, 66.7=uclemeli)"] = {
    "RED_orkestra_tiz": sal(o["RED"]["ust_2k_8k"]["vurus_arasi_sekizlik"]["ortanca"] - o["RED"]["ust_2k_8k"]["vurus_ustu"]["ortanca"], VURUS),
    "REF_orkestra_tiz": sal(o["REF"]["ust_2k_8k"]["vurus_arasi_sekizlik"]["ortanca"] - o["REF"]["ust_2k_8k"]["vurus_ustu"]["ortanca"], REF_VURUS),
    "RED_vokal": sal(V2["vokal"]["RED"]["yuva_turune_gore_unlu_girisi_eksi_yuva_ms"]["sekizlik"]["ortanca"] - V2["vokal"]["RED"]["yuva_turune_gore_unlu_girisi_eksi_yuva_ms"]["vurus"]["ortanca"], VURUS),
    "REF_vokal": sal(V2["vokal"]["REF"]["yuva_turune_gore_unlu_girisi_eksi_yuva_ms"]["sekizlik"]["ortanca"] - V2["vokal"]["REF"]["yuva_turune_gore_unlu_girisi_eksi_yuva_ms"]["vurus"]["ortanca"], REF_VURUS)}
# 16'lık çiftler: x ve x.25 yuvalarındaki ardışık hecelerin ünlü girişleri arası süre / sekizlik süre (0.5 = düz)
def cift_orani(anahtar, sekizlik):
    r = []
    for a, b in zip(U[:-1], U[1:]):
        if (a["verse"], a["line"]) == (b["verse"], b["line"]) and b["beat_in_bar"] % 0.5 == 0.25 and abs(b["beat_in_bar"] - a["beat_in_bar"] - 0.25) < 1e-6: r.append((b[anahtar] - a[anahtar]) / sekizlik)
    return {"n": len(r), "ortanca": round(float(np.median(r)), 3), "ss": round(float(np.std(r)), 3)}
sonuc["a_onaltilik_cift_orani(0.5=duz)"] = {"RED_vokal": cift_orani("red_unlu", VURUS / 2), "REF_vokal": cift_orani("ref_unlu", REF_VURUS / 2)}

# ---------- b) ölçü içi vuruş deseni ----------
def desen(x, olcu_baslari, vurus):
    c = {}
    for ad, (lo, hi) in {"pes_40_300": (40, 300), "orta_300_2000": (300, 2000), "tiz_2k_16k": (2000, 16000)}.items():
        e, fe = zarf(bant(x, lo, hi), ms=6.0); le = 20 * np.log10(e + 1e-5); d = np.maximum(np.gradient(signal.savgol_filter(le, 9, 2)), 0)
        g = np.zeros(16)
        for tb in olcu_baslari:
            for s in range(16):
                t = tb + s * vurus / 4; a, b = int((t - 0.03) * fe), int((t + 0.03) * fe)
                if a >= 0 and b < len(d): g[s] += d[a:b].sum()            # o yuvadaki toplam yükseliş (dB)
        g /= len(olcu_baslari); c[ad] = [round(float(v), 1) for v in g]
        sek = g[0::2].mean(); onal = g[1::2].mean(); c[ad + "_onaltilik_bolu_sekizlik"] = round(float(onal / (sek + 1e-9)), 2); c[ad + "_vurus_arasi_sekizlik_bolu_vurus"] = round(float(g[2::4].mean() / (g[0::4].mean() + 1e-9)), 2)
    return c
red_olcu = sorted({L["dest_bar_downbeat"] for L in Y["lines"] if L["line"] in ("L1", "L2", "L4")})
ref_olcu = sorted({round(L["dest_bar_downbeat"] - L["shift_sec"], 4) for L in Y["lines"] if L["line"] in ("L1", "L2", "L4")})
band = np.concatenate([np.zeros(int(ON * FS)), oku_mono(RED_BAND) + oku_mono(RED_EZGI) * 10 ** (-4 / 20)]); ens = oku_mono(REF_ENS)
sonuc["b_olcu_ici_desen_16lik_yuvalar(soylenen_olculer)"] = {"RED_orkestra": desen(band, red_olcu, VURUS), "REF_orkestra": desen(ens, ref_olcu, REF_VURUS),
    "vokal_hece_sayisi_yuvaya_gore": {str(k): int(sum(1 for u in U if u["line"] != "diye" and u["beat_in_bar"] * 4 == k)) for k in range(16)}, "olcu_sayisi": {"RED": len(red_olcu), "REF": len(ref_olcu)}}

# ---------- c) uzunluklar ----------
hec = [dict(s, line=L["line"]) for L in Y["lines"] for s in L["syllables"]]
def sonraki_yuva_araligi(i):
    a = hec[i]; b = hec[i + 1] if i + 1 < len(hec) and hec[i + 1]["dest_grid_time"] > a["dest_grid_time"] and hec[i + 1]["dest_grid_time"] - a["dest_grid_time"] < 0.6 else None
    return (b["dest_grid_time"] - a["dest_grid_time"]) if b else None
dol = [(h["dest_end"] - h["dest_start"]) / sonraki_yuva_araligi(i) for i, h in enumerate(hec) if sonraki_yuva_araligi(i)]
kl = [n for n in Z["ezgi_notalari"] if n["parti"] == "ezgi_alti" and n["enstruman"] == "klarnet"]
sonuc["c_uzunluklar"] = {"vokal_hece_suresi_ms": ozet([(h["dest_end"] - h["dest_start"]) * 1000 for h in hec]), "vokal_hece_suresi_bolu_yuva_araligi": {"ortanca": round(float(np.median(dol)), 2), "p10": round(float(np.percentile(dol, 10)), 2), "p90": round(float(np.percentile(dol, 90)), 2)},
    "klarnet_nota_suresi_ms": dict((str(int(k * 1000)), int(v)) for k, v in zip(*np.unique([round(n["sure"], 3) for n in kl], return_counts=True))), "klarnet_nota_suresi_bolu_sekizlik": round(0.2629 / (VURUS / 2), 2),
    "olcu_basina_vokal_hece_girisi": round(len([h for h in hec if h["line"] != "diye"]) / 21, 2), "olcu_basina_klarnet_nota_girisi": 7,
    "vokalde_olup_klarnette_olmayan_giris_yuvalari(sekizlik)": "2.5 (1. dize), 6.5, 7", "klarnette_olup_vokalde_olmayan": "yok"}

# ---------- d) dize sonu kuyruğu ----------
def kuyruk(x, bitisler, son_heceler):
    e, fe = zarf(x, ms=10.0); c = {k: [] for k in (50, 100, 200, 400)}
    for tb, (a, b) in zip(bitisler, son_heceler):
        ref = 20 * np.log10(np.sqrt(np.mean(e[int(a * fe):int(b * fe)] ** 2)) + 1e-9)
        for k in c: c[k].append(20 * np.log10(e[int((tb + k / 1000) * fe)] + 1e-9) - ref)
    return {"son_hece_duzeyine_gore_dB_+%dms" % k: round(float(np.median(np.maximum(v, -90))), 1) for k, v in c.items()}
# RED: karışımdaki vokal = kök + 38 ms'de -17 dB tek yankı (aecho 1:1:38:0.14) -> aynı şeyi burada uygula
vr = oku_mono(RED_VOK); g = int(0.038 * FS); vre = vr.copy(); vre[g:] += 0.14 * vr[:-g]
L4 = [L for L in Y["lines"] if L["line"] == "L4"]; tum = [L for L in Y["lines"] if L["line"] in ("L1", "L2", "L4")]
vf = oku_mono(REF_VOK)
sonuc["d_dize_sonu_kuyrugu"] = {
    "RED_4_dize_sonu(7)": kuyruk(vre, [L["dest_end"] for L in L4], [(L["syllables"][-1]["dest_core_start"], L["syllables"][-1]["dest_core_end"]) for L in L4]),
    "RED_tum_dize_sonlari(21)": kuyruk(vre, [L["dest_end"] for L in tum], [(L["syllables"][-1]["dest_core_start"], L["syllables"][-1]["dest_core_end"]) for L in tum]),
    "REF_4_dize_sonu(7)": kuyruk(vf, [L["src_end"] for L in L4], [(L["syllables"][-1]["src_core_start"], L["syllables"][-1]["src_core_end"]) for L in L4]),
    "not": "REF'te yalnız 4. dizeden sonra vokal susar (ardından 2 enstrümantal ölçü); MDX kökü yankı kuyruğunun bir kısmını enstrüman köküne bırakmış olabilir, yani REF kuyruğu burada olduğundan KISA ölçülmüş olabilir."}

# ---------- e) ezgi_alti düzeyi ----------
db = lambda q: 20 * np.log10(np.sqrt(np.mean(np.square(q))) + 1e-12)
bandy = np.concatenate([np.zeros(int(ON * FS)), oku_mono(RED_BAND)]); ezg = np.concatenate([np.zeros(int(ON * FS)), oku_mono(RED_EZGI)]) * 10 ** (-4 / 20)
n = min(len(bandy), len(vr)); t = np.arange(n) / FS; m = np.zeros(n, bool)
for L in tum: m |= (t >= L["dest_start"]) & (t <= L["dest_end"])
w = int(0.05 * FS); env = np.sqrt(signal.fftconvolve(vr[:n] ** 2, np.ones(w) / w, "same").clip(0)); sesli = env > env.max() * 0.1
vkaz = db((bandy[:n] + ezg[:n])[sesli]) + 8.5 - db(vr[:n][sesli])                       # 04_karisim.py'nin kuralı (zincir öncesi yaklaşık)
sonuc["e_ezgi_alti_duzeyi_soylenen_dizelerde_dB"] = {"altyapi": round(db(bandy[:n][m]), 1), "ezgi_alti(-4dB ile)": round(db(ezg[:n][m]), 1), "vokal(yaklasik)": round(db(vr[:n][m]) + vkaz, 1),
    "ezgi_eksi_altyapi": round(db(ezg[:n][m]) - db(bandy[:n][m]), 1), "ezgi_eksi_vokal": round(db(ezg[:n][m]) - db(vr[:n][m]) - vkaz, 1),
    "bant_500_2000Hz": {"altyapi": round(db(bant(bandy[:n], 500, 2000)[m]), 1), "ezgi_alti": round(db(bant(ezg[:n], 500, 2000)[m]), 1), "vokal": round(db(bant(vr[:n], 500, 2000)[m]) + vkaz, 1)},
    "bant_1000_2000Hz(çan)": {"altyapi": round(db(bant(bandy[:n], 1000, 2000)[m]), 1), "ezgi_alti": round(db(bant(ezg[:n], 1000, 2000)[m]), 1), "vokal": round(db(bant(vr[:n], 1000, 2000)[m]) + vkaz, 1)}}

# ---------- f) hayvan sesleri ----------
import soundfile as sf
SIRA = ["inek", "koyun", "at", "horoz", "ordek", "kopek", "kedi"]; hs = []
for k in range(7):
    for j in (1, 2):
        s, fs_ = sf.read(os.path.join(A, "yeni3", "ses", "%s_%d.wav" % (SIRA[k], j))); s = s if s.ndim == 1 else s.mean(axis=1)
        e, fe = zarf(s, fs=fs_, ms=10.0); tepe = e.max(); t10 = np.argmax(e > tepe * 0.1) / fe; t50 = np.argmax(e > tepe * 0.5) / fe; tt = np.argmax(e) / fe
        son = (len(e) - np.argmax(e[::-1] > tepe * 0.1)) / fe
        hs.append({"ses": "%s_%d" % (SIRA[k], j), "sure_sn": round(len(s) / fs_, 2), "olcu_basina_gore_%10_ms": round((t10 - 0.04) * 1000), "olcu_basina_gore_%50_ms": round((t50 - 0.04) * 1000), "olcu_basina_gore_tepe_ms": round((tt - 0.04) * 1000),
                   "duyulur_bitis_olcu_basindan_sn": round(son - 0.04, 2), "olcunun_dolan_kismi_yuzde": round(100 * (son - 0.04) / OLCU)})
sonuc["f_hayvan_sesleri"] = {"sesler": hs, "ozet_%50_ms": ozet([h["olcu_basina_gore_%50_ms"] for h in hs]), "ozet_tepe_ms": ozet([h["olcu_basina_gore_tepe_ms"] for h in hs]), "ozet_olcunun_dolan_kismi_yuzde": ozet([h["olcunun_dolan_kismi_yuzde"] for h in hs])}
json.dump(sonuc, open(os.path.join(ARA, "08_ek_ritim.json"), "w"), ensure_ascii=False, indent=1)
for k, v in sonuc.items():
    if k not in ("tanim",): print(k, json.dumps(v, ensure_ascii=False)[:2600])
