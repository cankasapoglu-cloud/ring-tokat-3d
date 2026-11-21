#!/usr/bin/env python3
"""SORU 2: Söylenen her hecenin perdesi o anda çalınan akora uyuyor mu; vokalin altındaki ezgi (klarnet) aynı notayı mı çalıyor?
 (A) Reddedilen karışım, nota verisinden (zaman_G.json + 0.100 s) ve stemlerden:
     hece -> ölçülen nota (Praat), o hecenin süresince geçerli akor(lar), aynı anda çalan klarnet notası (json + stemden f0 ile doğrulanır).
 (B) İki kayıt için AYNI ölçüm (nota verisi olmayan referansa da uygulanabilen): orkestra kromasında vokalin söylediği perde sınıfının payı
     ("kroma uyumu") ve o perde sınıfının 12 sınıf içindeki sırası; hece hece. Reddedilen: altyapi+ezgi (karışımdaki oranla). Referans: ayrılmış orkestra.
Çıktı: ara/02_armoni.json + ekrana tablo."""
import json, os, numpy as np, librosa
from ortak import *

Y, S, Z = yukle(); cik = {}
t, f0 = f0_izi(RED_VOK, "red_psola"); tr, f0r = f0_izi(REF_VOK, "ref_vokal")
te, f0e = f0_izi(RED_EZGI, "ezgi_klarnet", taban=400, tavan=1000)

# ---------- (A) nota verisinden ----------
vurus = []                                                   # (başlangıç, bitiş, akor) karışım zamanında
for bolum in [Z["giris"]["olculer"]] + [k["olculer"] for k in Z["kitalar"]] + [Z["bitis"]["olculer"]]:
    for o in bolum:
        for i, a in enumerate(o["akorlar"]): vurus.append((o["baslangic"] + i * VURUS + ON, o["baslangic"] + (i + 1) * VURUS + ON, a))
klar = [(n["baslangic"] + ON, n["baslangic"] + n["sure"] + ON, n["midi"]) for n in Z["ezgi_notalari"] if n["parti"] == "ezgi_alti" and n["enstruman"] == "klarnet"]
klar.sort()
# klarnet notasının "geçerli olduğu" aralık: bir sonraki notanın başına kadar (aradaki 20-30 ms'lik boşluk önceki notaya sayılır)
klar_ar = [(a, (klar[i + 1][0] if i + 1 < len(klar) and klar[i + 1][0] - b < 0.1 else b), m) for i, (a, b, m) in enumerate(klar)]


def ortusme(a, b, liste):
    r = {}
    for x0, x1, v in liste:
        o = min(b, x1) - max(a, x0)
        if o > 0: r[v] = r.get(v, 0) + o
    return r


sat = []
for s in S:
    a, b = s["dest_start"], s["dest_end"]; m, _ = hece_perdesi(t, f0, a, b); pc = int(round(m)) % 12
    # sesli çekirdek: hecenin sesli karelerinin ilk ve son zamanı
    sm = (t >= a) & (t < b) & (f0 > 0); ca, cb = (t[sm][0], t[sm][-1] + 0.005) if sm.sum() else (a, b)
    ak = ortusme(ca, cb, vurus); kl = ortusme(ca, cb, klar_ar); top = cb - ca
    ak_ana = max(ak, key=ak.get); uyum_sure = sum(v for k, v in ak.items() if pc in AKOR[k]) / top
    kl_ana = max(kl, key=kl.get) if kl else None; ayni_sure = sum(v for k, v in kl.items() if k % 12 == pc) / top if kl else None
    me, _ = hece_perdesi(te, f0e, ca, cb, orta=1.0)
    fark = None if kl_ana is None else min((pc - kl_ana) % 12, (kl_ana - pc) % 12)
    sat.append({"kita": s["verse"], "satir": s["line"], "sira": s["index"], "hece": s["text"], "vurus": s["beat_in_bar"], "bas": round(a, 3), "bit": round(b, 3), "cekirdek_ms": round(top * 1000),
                "soylenen_midi": round(m, 2), "soylenen": ad(m), "hedef": ad(s["hedef"]), "akor": ak_ana, "akorlar": {k: round(v / top, 2) for k, v in ak.items()}, "akor_sesi_orani": round(uyum_sure, 2),
                "klarnet": None if kl_ana is None else ad(kl_ana), "klarnetler": {ad(k): round(v / top, 2) for k, v in kl.items()}, "klarnet_ayni_nota_orani": None if ayni_sure is None else round(ayni_sure, 2),
                "klarnet_olculen": None if np.isnan(me) else ad(me), "klarnet_olculen_midi": None if np.isnan(me) else round(me, 2), "klarnetle_aralik_yarim_ses": fark})
cik["heceler"] = sat
n = len(sat); akor_disi = [x for x in sat if x["akor_sesi_orani"] < 0.5]; farkli = [x for x in sat if x["klarnet_ayni_nota_orani"] is not None and x["klarnet_ayni_nota_orani"] < 0.5]
ikili = [x for x in farkli if x["klarnetle_aralik_yarim_ses"] in (1, 2)]
sure = lambda L: round(sum(x["cekirdek_ms"] for x in L) / 1000, 1)
cik["ozet_A"] = {"hece": n, "toplam_sesli_sn": sure(sat), "akor_sesi_olmayan_hece": len(akor_disi), "akor_sesi_olmayan_sn": sure(akor_disi),
                 "klarnetten_farkli_nota_hece": len(farkli), "klarnetten_farkli_sn": sure(farkli), "klarnetle_ikili_aralik_(1-2_yarim_ses)_hece": len(ikili), "ikili_sn": sure(ikili),
                 "klarnet_stem_dogrulama_uyusan": sum(1 for x in sat if x["klarnet_olculen"] and x["klarnet"] and x["klarnet_olculen"] == x["klarnet"]), "klarnet_olculen_hece": sum(1 for x in sat if x["klarnet_olculen"])}
print("(A) REDDEDİLEN, nota verisinden:", json.dumps(cik["ozet_A"], ensure_ascii=False))
# satır x hece sırası tablosu (7 kıtada hedefler aynı): 1. kıtanın hecesiyle
print("\n satır  # vuruş hece   söylenen(ölç.)  akor(vuruş)       akor sesi?  klarnet(json)      klarnet(stem)  aralık  çakışan kıta/7")
tab = []
for satir in ("L1", "L2", "diye", "L4"):
    for i in range(10):
        g = [x for x in sat if x["satir"] == satir and x["sira"] == i and not (satir == "L2" and sum(1 for y in sat if y["kita"] == x["kita"] and y["satir"] == "L2") == 8)]
        if not g: continue
        x = g[0]; cak = sum(1 for y in g if (y["klarnet_ayni_nota_orani"] or 0) < 0.5); akd = sum(1 for y in g if y["akor_sesi_orani"] < 0.5)
        tab.append({"satir": satir, "sira": i, "vurus": x["vurus"], "hece_K1": x["hece"], "soylenen": x["soylenen"], "akor": x["akor"], "akor_disi_kita": akd, "klarnet": x["klarnet"], "klarnetten_farkli_kita": cak, "kita": len(g),
                    "aralik": x["klarnetle_aralik_yarim_ses"], "ornek_zamanlar": [y["bas"] for y in g[:3]]})
        print(" %-5s %d %-5s %-6s %-4s(%.2f)   %-16s %-10s  %-18s %-13s  %-6s  klarnet≠ %d/%d, akor dışı %d/%d" % (satir, i, x["vurus"], x["hece"], x["soylenen"], x["soylenen_midi"], json.dumps(x["akorlar"]), "evet" if x["akor_sesi_orani"] >= 0.5 else "HAYIR",
              json.dumps(x["klarnetler"]), x["klarnet_olculen"], x["klarnetle_aralik_yarim_ses"], cak, len(g), akd, len(g)))
cik["tablo_satir_sira"] = tab
print("\n 8 heceli L2 kıtaları (3: atları, 4: horozları?):")
for x in sat:
    if x["satir"] == "L2" and sum(1 for y in sat if y["kita"] == x["kita"] and y["satir"] == "L2") == 8:
        print("   K%d #%d v%-4s %-5s %s akor %s %s klarnet %s aralık %s" % (x["kita"], x["sira"], x["vurus"], x["hece"], x["soylenen"], x["akor"], "evet" if x["akor_sesi_orani"] >= 0.5 else "HAYIR", json.dumps(x["klarnetler"]), x["klarnetle_aralik_yarim_ses"]))

# ezgi çizgisi düzlüğü: satır başına farklı nota sayısı ve art arda aynı nota (reddedilen hedef / referansta söylenen)
def duzluk(deger):
    r = []
    for k in range(1, 8):
        for satir in ("L1", "L2", "diye", "L4"):
            g = [int(round(deger(x))) for x in S if x["verse"] == k and x["line"] == satir]
            deg = sum(1 for i in range(1, len(g)) if g[i] != g[i - 1]); r.append((len(set(g)), deg / (len(g) - 1), max(g) - min(g)))
    r = np.array(r, float); return {"satirda_farkli_nota_ort": round(r[:, 0].mean(), 2), "nota_degisen_hece_gecisi_orani": round(r[:, 1].mean(), 2), "satir_araligi_yarim_ses_ort": round(r[:, 2].mean(), 2)}
cik["ezgi_duzlugu"] = {"reddedilen_hedef": duzluk(lambda x: x["hedef"]), "referans_soylenen": duzluk(lambda x: x["midi"])}
print("\n ezgi düzlüğü:", json.dumps(cik["ezgi_duzlugu"], ensure_ascii=False))

# ---------- (B) kroma uyumu: iki kayıtta aynı ölçüm ----------
SR = 22050; HOP = 512
def kroma(x, akort_sent):
    y = librosa.resample(x, orig_sr=FS, target_sr=SR); y = librosa.effects.harmonic(y, margin=3.0)      # davul/vurmalı çıkarılır (yoksa kroma anlamsızlaşıyor: denendi)
    C = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP, tuning=akort_sent / 100, n_chroma=12, bins_per_octave=36, fmin=librosa.note_to_hz("C2"), n_octaves=5, norm=None)
    return C, librosa.frames_to_time(np.arange(C.shape[1]), sr=SR, hop_length=HOP)
def uyum(C, tc, heceler):
    r = []
    for a, b, m in heceler:
        k = (tc >= a) & (tc < b)
        if k.sum() < 1 or np.isnan(m): continue
        c = C[:, k].mean(axis=1); c = c / (c.sum() + 1e-12); pc = int(round(m)) % 12
        r.append((c[pc], 1 + int((c > c[pc]).sum()), c[(pc + 1) % 12] + c[(pc - 1) % 12], c[(pc + 2) % 12] + c[(pc - 2) % 12]))
    r = np.array(r); return {"hece": int(len(r)), "soylenen_sinifin_payi_ortanca": round(float(np.median(r[:, 0])), 3), "pay_p25": round(float(np.percentile(r[:, 0], 25)), 3),
                             "ilk3_sirada_%": round(float((r[:, 1] <= 3).mean() * 100), 1), "ilk1_sirada_%": round(float((r[:, 1] <= 1).mean() * 100), 1), "6dan_sonra_%": round(float((r[:, 1] > 6).mean() * 100), 1),
                             "yarim_ses_komsu_payi_ortanca": round(float(np.median(r[:, 2])), 3), "tam_ses_komsu_payi_ortanca": round(float(np.median(r[:, 3])), 3)}, r
band = oku_mono(RED_BAND); ez = oku_mono(RED_EZGI) * 10 ** (-4 / 20); pad = np.zeros(int(ON * FS))
red_ens = np.concatenate([pad, band + ez]); red_ens_ezgisiz = np.concatenate([pad, band]); ref_ens = oku_mono(REF_ENS)
A1 = json.load(open(os.path.join(ARA, "01_akort.json"), encoding="utf8"))
hr = []; hf = []
for s in S:
    sm = (t >= s["dest_start"]) & (t < s["dest_end"]) & (f0 > 0); m, _ = hece_perdesi(t, f0, s["dest_start"], s["dest_end"])
    if sm.sum(): hr.append((t[sm][0], t[sm][-1] + 0.005, m))
    sm = (tr >= s["src_start"]) & (tr < s["src_end"]) & (f0r > 0); m, _ = hece_perdesi(tr, f0r, s["src_start"], s["src_end"])
    if sm.sum(): hf.append((tr[sm][0], tr[sm][-1] + 0.005, m))
Cr, tcr = kroma(red_ens, 1.0); Cz, tcz = kroma(red_ens_ezgisiz, 1.0); Cf, tcf = kroma(ref_ens, 4.0)
u_red, rr = uyum(Cr, tcr, hr); u_red0, _ = uyum(Cz, tcz, hr); u_ref, rf = uyum(Cf, tcf, hf)
# rastgele taban: aynı heceler, perde sınıfı rastgele kaydırılmış (0..11 ortalaması)
def taban(C, tc, heceler):
    p = []
    for k in range(1, 12): p.append(uyum(C, tc, [(a, b, m + k) for a, b, m in heceler])[0]["soylenen_sinifin_payi_ortanca"])
    return round(float(np.mean(p)), 3)
cik["kroma_uyumu"] = {"reddedilen_(altyapi+ezgi)": u_red, "reddedilen_(ezgi_alti_olmadan)": u_red0, "referans_(ayrilmis_orkestra)": u_ref,
                      "rastgele_taban_reddedilen": taban(Cr, tcr, hr), "rastgele_taban_referans": taban(Cf, tcf, hf),
                      "uyari": "Referans orkestrası MDX ile ayrılmıştır: içinde vokal kalıntısı varsa referansın payını yukarı çeker. Reddedilende orkestra temizdir."}
print("\n(B) kroma uyumu (orkestra kromasında söylenen perde sınıfının payı; 1/12 = 0.083 rastgele düzey):")
for k, v in cik["kroma_uyumu"].items(): print("   ", k, json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v)
# ---------- (C) aynı yöntemle akor kestirimi (vuruş başına 24 üçlü akor şablonu) ve "söylenen nota akor sesi mi?" ----------
def akor_kestir(C, tc, v0, vurus_sn, n):
    sab = {}
    for k in range(12):
        sab[NOTA[k]] = {k, (k + 4) % 12, (k + 7) % 12}; sab[NOTA[k] + "m"] = {k, (k + 3) % 12, (k + 7) % 12}
    r = []
    for i in range(n):
        a = v0 + i * vurus_sn; k = (tc >= a) & (tc < a + vurus_sn)
        if k.sum() < 2: r.append((a, a + vurus_sn, None, set())); continue
        c = C[:, k].mean(axis=1); c = c / (np.linalg.norm(c) + 1e-12)
        en = max(sab, key=lambda q: sum(c[j] for j in sab[q]) / np.sqrt(3) - 0.0 * 1); r.append((a, a + vurus_sn, en, sab[en]))
    return r
def akor_sesi_orani(akorlar, heceler):
    ev = 0; top = 0; yarim = 0
    for a, b, m in heceler:
        pc = int(round(m)) % 12; o = [(min(b, x1) - max(a, x0), ss) for x0, x1, ad_, ss in akorlar if min(b, x1) - max(a, x0) > 0 and ss]
        if not o: continue
        ss = max(o, key=lambda q: q[0])[1]; top += 1; ev += pc in ss; yarim += any(((pc - q) % 12) in (1, 11) for q in ss) and pc not in ss
    return {"hece": top, "akor_sesi_%": round(100 * ev / top, 1), "akor_sesine_yarim_ses_komsu_%": round(100 * yarim / top, 1)}
ak_red = akor_kestir(Cr, tcr, ON, VURUS, 256); ak_ref = akor_kestir(Cf, tcf, 0.00011546, 0.5714133459, 222)
from collections import Counter
cik["akor_sablonu"] = {"reddedilen": akor_sesi_orani(ak_red, hr), "referans": akor_sesi_orani(ak_ref, hf),
                       "reddedilen_kestirilen_akorlar_soylenen_vuruslar": dict(Counter(x[2] for x in ak_red if any(min(b, x[1]) - max(a, x[0]) > 0.1 for a, b, m in hr)).most_common(6)),
                       "referans_kestirilen_akorlar_soylenen_vuruslar": dict(Counter(x[2] for x in ak_ref if any(min(b, x[1]) - max(a, x[0]) > 0.1 for a, b, m in hf)).most_common(8)),
                       "referans_1_kita_vurus_akorlari": [x[2] for x in ak_ref[15:15 + 24]], "reddedilen_1_kita_vurus_akorlari": [x[2] for x in ak_red[16:16 + 32]]}
print("\n(C) kestirilen akora göre akor sesi oranı:"); [print("   ", k, json.dumps(v, ensure_ascii=False)) for k, v in cik["akor_sablonu"].items()]
json.dump(cik, open(os.path.join(ARA, "02_armoni.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
