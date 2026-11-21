#!/usr/bin/env python3
"""Sorgu basina ilk sayfa gucu. Kullanim: python3 -I analiz.py <calisma klasoru> [ayrinti]
Girdi: arama-sonuclari-ham.csv, kanal-aboneleri.csv  Cikti: kanit-arama-sonuclari.csv, kanit-sorgu-ozeti.csv"""
import csv, os, re, statistics as st, sys, json
from collections import Counter, defaultdict
K = sys.argv[1]; AYR = len(sys.argv) > 2
oku = lambda f: list(csv.DictReader(open(os.path.join(K, f), encoding="utf-8")))
rows = oku("arama-sonuclari-ham.csv"); kan = oku("kanal-aboneleri.csv")
harita = json.load(open(os.path.join(K, "araclar", "sorgu-haritasi.json"), encoding="utf-8"))
grup = {q: ad[:2] for ad, q in harita.items()}
VID = {"01": "Ali Baba'nın Çiftliği", "02": "Pıtır'ın Ailesi", "03": "Parmak Ailesi", "04": "Beş Küçük Maymun", "05": "Balon Şarkısı (renkler)", "06": "El Yıkama Şarkısı", "07": "Otobüs Şarkısı", "08": "Gezegenler (planlı)", "09": "Harfler/Alfabe (planlı)", "10": "Sayılar 1-10 (planlı)", "11": "Banyo (planlı)", "12": "Pazar/Meyveler (planlı)"}
abone = {r["kanal_id"]: (int(r["abone_sayi"]) if r["abone_sayi"] else None) for r in kan}
I = lambda x: int(float(x)) if x not in ("", None) else None
F = lambda x: float(x) if x not in ("", None) else None
def low(t): return re.sub(r"['’`´]", "", t.replace("İ", "i").replace("I", "ı").lower())
def kisa(n):
    if n is None: return "?"
    return f"{n/1e6:.1f}Mn" if n >= 1e6 else (f"{n/1e3:.0f}B" if n >= 1e3 else str(n))
COCUK = re.compile(r"çocuk|bebek|kids|çizgi|okul öncesi|anaokul|ninni|tekerleme|eğitici|öğren|minik|baby|nursery")
ek = []; ozet = []
gr = defaultdict(list)
for r in rows: gr[r["sorgu"]].append(r)
for q, rs in gr.items():
    v = [r for r in rs if r["tur"] == "video" and r["goruntuleme_sayi"]]
    for r in rs:
        a = abone.get(r["kanal_id"]); s = I(r["sure_saniye"]) if r["tur"] == "video" else None; y = F(r["yas_ay"]) if r["tur"] == "video" else None
        ek.append(dict(r, video_grubu=VID[grup[q]], abone_sayi=a if a is not None else "",
                       kanal_boyu=("" if r["tur"] != "video" else "bilinmiyor" if a is None else "kucuk(<10B)" if a < 1e4 else "orta(10B-100B)" if a < 1e5 else "buyuk(100B-1Mn)" if a < 1e6 else "dev(1Mn+)"),
                       uzun_derleme=("evet" if s is not None and s >= 600 else "hayir" if s is not None else ""),
                       son_12_ay=("evet" if y is not None and y <= 12 else "hayir" if y is not None else ""),
                       sorgu_baslikta=("evet" if low(q) in low(r["baslik"]) else "hayir")))
    g = sorted(I(r["goruntuleme_sayi"]) for r in v); sn = [I(r["sure_saniye"]) for r in v if r["sure_saniye"]]
    ab = [abone.get(r["kanal_id"]) for r in v]
    kucuk = [r for r in v if abone.get(r["kanal_id"]) is not None and abone[r["kanal_id"]] < 1e4]
    yeni = [r for r in v if r["yas_ay"] and F(r["yas_ay"]) <= 12]
    kuc_ya_yeni = [r for r in v if (abone.get(r["kanal_id"]) is not None and abone[r["kanal_id"]] < 1e4) or (r["yas_ay"] and F(r["yas_ay"]) <= 12 and (abone.get(r["kanal_id"]) or 0) < 1e5)]
    ilk10 = [r for r in v if I(r["sira"]) <= 10]
    k10 = [r for r in ilk10 if abone.get(r["kanal_id"]) is not None and abone[r["kanal_id"]] < 1e4]
    kc = Counter(r["kanal"] for r in v)
    tam = sum(1 for r in v if low(q) in low(r["baslik"]))
    coc = sum(1 for r in v if COCUK.search(low(r["baslik"] + " " + r["kanal"])))
    med = int(st.median(g)) if g else 0
    der = sum(1 for s in sn if s >= 600); orta = sum(1 for s in sn if 300 <= s < 600); tek = sum(1 for s in sn if s < 300)
    dev = sum(1 for a in ab if a is not None and a >= 1e6)
    if med >= 5e6 and len(k10) <= 1: karar = "UMUTSUZ"
    elif len(k10) >= 3 or (med < 3e5 and len(kucuk) >= 5): karar = "KAZANILABILIR"
    elif len(k10) >= 2 or med < 1e6: karar = "ORTA-IYI"
    else: karar = "ZOR"
    o = dict(video_grubu=VID[grup[q]], sorgu=q, video_sayisi=len(v), short_sayisi=sum(1 for r in rs if r["tur"] == "short"), medyan_goruntuleme=med,
             en_dusuk_goruntuleme=g[0] if g else "", ilk5_medyan_goruntuleme=int(st.median([I(r["goruntuleme_sayi"]) for r in v[:5]])) if v else "",
             goruntuleme_100B_alti=sum(1 for x in g if x < 1e5), goruntuleme_10B_alti=sum(1 for x in g if x < 1e4),
             kucuk_kanal_video=len(kucuk), kucuk_kanal_ilk10=len(k10), en_iyi_kucuk_kanal_sirasi=min((I(r["sira"]) for r in kucuk), default=""),
             orta_kanal_video=sum(1 for a in ab if a is not None and 1e4 <= a < 1e5), dev_kanal_video=dev, abonesi_bilinmeyen=sum(1 for a in ab if a is None),
             son_12_ay_video=len(yeni), kucuk_veya_yeni=len(kuc_ya_yeni), uzun_derleme_10dk=der, orta_5_10dk=orta, tek_sarki_5dk_alti=tek,
             sorgu_baslikta_gecen=tam, cocuk_icerigi_ipucu=coc, farkli_kanal=len(kc), en_cok_cikan_kanal=(kc.most_common(1)[0][0] + " x" + str(kc.most_common(1)[0][1])) if kc else "", karar=karar)
    ozet.append(o)
    print(f"{grup[q]} {q[:30]:30} n={len(v):2} med={kisa(med):>7} ilk5={kisa(o['ilk5_medyan_goruntuleme']):>7} min={kisa(g[0]) if g else '?':>6} <100B={o['goruntuleme_100B_alti']:2} kucuk={len(kucuk):2} k10={len(k10)} eniyi#={str(o['en_iyi_kucuk_kanal_sirasi']):>2} dev={dev:2} ?={o['abonesi_bilinmeyen']:2} yeni12={len(yeni):2} der={der:2} tek={tek:2} tam={tam:2} coc={coc:2} sh={o['short_sayisi']} {karar}")
    if AYR:
        gos = v[:4] + [r for r in kucuk if r not in v[:4]][:3]
        for r in gos:
            print(f"     #{r['sira']:>2} {kisa(I(r['goruntuleme_sayi'])):>7} {r['sure_metni']:>8} {r['yas_metni'][:11]:11} ab={kisa(abone.get(r['kanal_id'])):>6} {r['kanal'][:20]:20} | {r['baslik'][:58]}")
for ad, veri in [("kanit-arama-sonuclari.csv", ek), ("kanit-sorgu-ozeti.csv", ozet)]:
    with open(os.path.join(K, ad), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(veri[0].keys())); w.writeheader(); w.writerows(veri)
