#!/usr/bin/env python3
"""Boyut boyut ayrisma: kullanicinin etiketine gore 'olumlu' ve 'olumsuz' gruplarda aracin sayilari ayrisiyor mu?
Her olcu icin: iki grubun degerleri, aralarinda TEMIZ BOSLUK var mi (bir grubun en kotusu oteki grubun en iyisinden ayri mi),
etiketsiz 'diger' kayitlar bu boslugun neresinde. Esik YALNIZCA bosluk temizse onerilir (boslugun ortasi).
Girdi: ara/olcumler.json (05_olcumleri_topla.py), ara/soz_denetimi.json.  Cikti: ara/ayrisma.json + ekrana ozet."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from set import SET, KAL
M = {m["ad"]: m for m in json.load(open(os.path.join(KAL, "ara", "olcumler.json"), encoding="utf8"))}
SD = json.load(open(os.path.join(KAL, "ara", "soz_denetimi.json"), encoding="utf8"))
for ad, m in M.items():
    g = (SD.get(ad) or {}).get("guven") or {}
    m["logprob_ort"] = g.get("ortalama_logprob"); m["logprob_dusuk_oran"] = g.get("oran_-0.3_alti")
    m["uzun_nota_orani"] = (m["uzun_nota_035"] / m["nota_sayisi"]) if m.get("nota_sayisi") and m.get("uzun_nota_035") is not None else None
    m["vokalli_nota_sn"] = (m["nota_sayisi"] / (m["sure_sn"] * m["vokalli_oran"])) if m.get("nota_sayisi") and m.get("vokalli_oran") else None

P = "parmak-ailesi__"; A = "ali-baba__"; E = "el-yikama__"
DOGAL_YZ = [A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1", A + "coskulu_1", A + "coskulu_2", P + "duzgun_1", P + "duzgun_2", P + "turkce_2", P + "yavas_2",
            "pitirin-ailesi__yavas_2", E + "sarki_1", P + "sarki_2"]          # tek parca uretilmis, islenmemis yapay sarkici kayitlari
BOYUT = {
 "enerji": dict(
    aciklama="Kullanicinin 'cosku' yargisi: olumlu = sectigi coskulu kayitlar ve 'olmus' dedigi altyapi; olumsuz = 'ninni gibi, cosku yok' dedigi kayitlar",
    olumlu=[E + "coskulu_2", P + "coskulu_1", A + "demo_altyapi_sesli"], olumsuz=[P + "yavas_2", "pitirin-ailesi__yavas_2", E + "sarki_1"],
    olculer=[("enerji_puani", "hareketlilik puani (0-100)"), ("coca_cosku", "MusicCoCa cosku farki"), ("coca_tempo", "MusicCoCa tempo farki"), ("ced_ninni", "CED 'ninni' olasiligi"),
             ("ced_coskulu_eksi_sakin", "CED coskulu-sakin"), ("ced_yumusak", "CED 'Tender music'"), ("ced_mutlu", "CED 'Happy music'"), ("olay_sn", "olay yogunlugu /sn"),
             ("nabiz", "nabiz netligi"), ("vurmali_armonik_db", "vurmali/armonik dB"), ("aki", "spektral aki"), ("parlaklik_hz", "parlaklik Hz"), ("tempo_bpm", "tempo BPM (otomatik)"),
             ("hece_sn_obek_medyan", "hece/sn (obek medyani)"), ("hece_sn_soz_ici", "hece/sn (soz ici)")]),
 "dogallik": dict(
    aciklama="olumlu = sesi begenilen / uygun bulunan dogal yapay sarkici kayitlari; olumsuz = vokoderle ezgiye oturtulmus ve esnetilip perdesi duzlenmis vokaller. 'diger' = islenmemis ama baska nedenle reddedilmis yapay sarkici kayitlari (bunlar da 'dogal' tarafta kalmali)",
    olumlu=[A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1"], olumsuz=[A + "ornek_kita1", A + "sarki_birlesik"],
    diger=[x for x in DOGAL_YZ if x not in (A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1")] + [A + "dogal_onizleme"],   # onizleme: ISLENMEMIS dogal vokal, baska orkestrada
    olculer=[("wer", "sozcuk hata orani"), ("logprob_dusuk_oran", "Scribe'in emin olmadigi sozcuk orani (logprob<-0,3)"), ("logprob_ort", "Scribe ortalama logprob"),
             ("y_donmus_sure_orani", "donmus unlu sure orani"), ("y_nota_ici_oynaklik_cent_medyan", "nota ici oynaklik (cent)"), ("y_cok_duz_nota_orani", "cok duz nota orani"),
             ("y_perde_izgaraya_yapisma_R", "perde izgaraya yapisma R"), ("y_vibratolu_uzun_nota_orani", "vibratolu uzun nota orani"), ("y_zarf_titremesi_db", "zarf titremesi dB"),
             ("y_tiz_doku_degisim_katsayisi", "tiz doku degisim katsayisi"), ("y_unsuzlerde_tiz_payi_db", "unsuzlerde tiz payi dB"), ("y_bagli_gecis_suresi_ms_medyan", "bagli gecis suresi ms"),
             ("y_sesli_cercevelerde_ardisik_benzerlik_medyan", "ardisik cerceve benzerligi"), ("y_isaret_sayisi", "yapaylik isareti sayisi"),
             ("dnsmos", "DNSMOS"), ("nisqa", "NISQA"), ("nisqa_kesintisizlik", "NISQA kesintisizlik"), ("distillmos", "Distill-MOS"), ("utmos22", "UTMOS22"),
             ("v_sarki", "CED vokal: Singing"), ("v_konusma", "CED vokal: Speech"), ("v_sentetik_sarki", "CED vokal: Synthetic singing"), ("v_konusma_sentezi", "CED vokal: Speech synthesizer"),
             ("ritim_R", "ritim sikiligi R"), ("vokalli_nota_sn", "vokalli saniye basina bulunan nota"),
             ("nota_suresi_medyan", "nota suresi medyani sn"), ("gecis_cerceve_orani", "gecis cercevesi orani"), ("kayan_nota_orani", "kayan nota orani"), ("ani_gecis_orani", "ani gecis orani (35 ms alti)"),
             ("uzun_nota_orani", "uzun nota (0,35 sn ustu) orani")]),
 "uyum": dict(
    aciklama="olumlu = sarkici ve orkestrasi birlikte uretilmis, kabul edilmis kayitlar; olumsuz = dogal vokalin baska ezgi calan orkestranin ustune kondugu on dinleme ('olmamis'). 'diger' = birlikte uretilmis ama baska nedenle reddedilmis kayitlar (bunlar da 'uyumlu' tarafta kalmali)",
    olumlu=[A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1"], olumsuz=[A + "dogal_onizleme"],
    diger=[x for x in DOGAL_YZ if x not in (A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1")] + [A + "ornek_kita1", A + "sarki_birlesik"],
    olculer=[("en_iyi_kaydirma", "en iyi kaydirma (yarim ses; 0 olmali)"), ("sifir_kacinci", "0 kaydirmanin sirasi (1 olmali)"), ("destek_gercek", "armonik destek (kaydirmasiz)"), ("destek_fark", "armonik destek farki"),
             ("gam_ici", "gam ici sure orani"), ("akor_sesi", "akor sesi sure orani"), ("gam_disi", "gam disi oran"), ("cent_medyan", "cent sapma medyani"), ("yuzde_25cent", "+-25 cent icinde %"),
             ("y_perde_izgaraya_yapisma_R", "perde izgaraya yapisma R"), ("cakisan_oran", "cakisan uzun nota orani"), ("ritim_R", "ritim sikiligi R"), ("ritim_40ms", "40 ms icinde %"),
             ("vokal_eksi_altyapi_db", "vokal - altyapi dB"), ("sizinti_db", "vokal kanalina sizinti dB"), ("wer", "sozcuk hata orani"), ("v_sarki", "CED vokal: Singing"), ("v_konusma", "CED vokal: Speech"),
             ("ses_araligi_ys", "bulunan ses araligi (yarim ses)")]),
 "aksan": dict(
    aciklama="olumsuz = 'Turkce konusan Ingiliz gibi' denen iki kayit; olumlu = ayni sarkinin secilen kaydi; 'diger' = ayni sarkinin baska nedenle reddedilen kayitlari ve oteki dogal kayitlar (aksan sikayeti yok)",
    olumlu=[P + "coskulu_1"], olumsuz=[P + "duzgun_1", P + "duzgun_2"], diger=[P + "turkce_2", P + "yavas_2", P + "sarki_2", A + "v2_2", A + "dinle_2", E + "coskulu_2", E + "sarki_1", "pitirin-ailesi__yavas_2"],
    olculer=[("wer", "sozcuk hata orani"), ("logprob_ort", "Scribe ortalama logprob"), ("logprob_dusuk_oran", "emin olunmayan sozcuk orani"), ("dil_olasiligi", "Scribe dil olasiligi (Turkce)"),
             ("dnsmos", "DNSMOS"), ("nisqa", "NISQA"), ("distillmos", "Distill-MOS"), ("utmos22", "UTMOS22"), ("v_konusma", "CED vokal: Speech"), ("y_unsuzlerde_tiz_payi_db", "unsuzlerde tiz payi dB"),
             ("hece_sn_obek_medyan", "hece/sn (obek medyani)"), ("y_isaret_sayisi", "yapaylik isareti sayisi")]),
 "hiz": dict(
    aciklama="olumsuz = 'sozler cok hizli geciyor' denen kayit; olumlu = ayni sarkinin secilen kaydi; 'diger' = ayni sarkinin oteki kayitlari",
    olumlu=[P + "coskulu_1"], olumsuz=[P + "sarki_2"], diger=[P + "duzgun_1", P + "duzgun_2", P + "turkce_2", P + "yavas_2"],
    olculer=[("hece_sn_soz_ici", "hece/sn (soz ici)"), ("hece_sn_obek_medyan", "hece/sn (obek medyani)"), ("hece_sn_en_hizli", "hece/sn (en hizli obek)"), ("cok_hizli_obek", "cok hizli obek sayisi"),
             ("sure_sn", "sure sn"), ("tempo_bpm", "tempo BPM (otomatik)"), ("vokalli_oran", "vokalli sure orani")]),
 "sure": dict(
    aciklama="olumsuz = 'cok uzun (3-3,5 dk)' denen iki kayit; olumlu = kabul edilen kayitlar",
    olumlu=[A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1", A + "demo_altyapi_sesli"], olumsuz=[A + "coskulu_1", A + "coskulu_2"],
    olculer=[("sure_sn", "sure sn")]),
 "sozler": dict(
    aciklama="olumsuz = kullanicinin soz hatasi soyledigi kayitlar; olumlu = sozleri icin sikayet etmedigi / 'bes ad da dogru' dedigi secilmis kayitlar",
    olumlu=[P + "coskulu_1", E + "coskulu_2", A + "dinle_2"], olumsuz=[A + "v2_2", A + "coskulu_1", A + "coskulu_2", P + "turkce_2", P + "yavas_2", A + "ornek_kita1"],
    olculer=[("wer", "sozcuk hata orani"), ("wer_kucuksuz", "kucuk farklar sayilmazsa"), ("degisik", "degisik sozcuk"), ("eksik", "eksik sozcuk"), ("fazla", "fazla sozcuk"),
             ("logprob_dusuk_oran", "emin olunmayan sozcuk orani")]),
}

def deger(adlar, anahtar):
    return [(a.split("__")[-1] if True else a, M[a].get(anahtar)) for a in adlar if a in M and M[a].get(anahtar) is not None and not isinstance(M[a].get(anahtar), (list, dict, str))]

C = {}
for boyut, b in BOYUT.items():
    sat = []
    for anahtar, ad in b["olculer"]:
        po, ne, di = deger(b["olumlu"], anahtar), deger(b["olumsuz"], anahtar), deger(b.get("diger", []), anahtar)
        r = {"olcu": anahtar, "ad": ad, "olumlu": po, "olumsuz": ne, "diger": di, "n_olumlu": len(po), "n_olumsuz": len(ne)}
        if po and ne:
            pv, nv = [float(v) for _, v in po], [float(v) for _, v in ne]
            if min(pv) > max(nv):
                r.update(yon="olumlu yuksek", bosluk=[max(nv), min(pv)])
            elif max(pv) < min(nv):
                r.update(yon="olumlu dusuk", bosluk=[max(pv), min(nv)])
            else:
                r.update(yon=None, bosluk=None)
            r["temiz_bosluk"] = r["bosluk"] is not None and abs(r["bosluk"][1] - r["bosluk"][0]) > 1e-9
            if r["temiz_bosluk"]:
                lo, hi = r["bosluk"]
                r["bosluk_genisligi"] = round(hi - lo, 4)
                yayilim = max(max(pv + nv) - min(pv + nv), 1e-9)
                r["bosluk_orani"] = round((hi - lo) / yayilim, 2)                 # boslugun, butun degerlerin yayilimina orani
                r["esik_adayi"] = round((lo + hi) / 2, 4)
                if di:
                    dv = [float(v) for _, v in di]
                    r["diger_bosluk_icinde"] = [n for n, v in di if lo < float(v) < hi]
                    if r["yon"] == "olumlu yuksek":
                        r["diger_olumsuz_tarafta"] = [n for n, v in di if float(v) <= lo]
                    else:
                        r["diger_olumsuz_tarafta"] = [n for n, v in di if float(v) >= hi]
        sat.append(r)
    C[boyut] = {"aciklama": b["aciklama"], "olculer": sat}
json.dump(C, open(os.path.join(KAL, "ara", "ayrisma.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)

def f(v):
    return ("%.3g" % v) if isinstance(v, float) else str(v)
for boyut, b in C.items():
    print("\n================ %s ================\n%s" % (boyut.upper(), b["aciklama"]))
    for r in b["olculer"]:
        if not r["n_olumlu"] or not r["n_olumsuz"]:
            print("  %-48s (veri eksik: olumlu %d, olumsuz %d)" % (r["ad"], r["n_olumlu"], r["n_olumsuz"])); continue
        durum = ("TEMIZ BOSLUK %s..%s (oran %.2f) esik~%s%s" % (f(r["bosluk"][0]), f(r["bosluk"][1]), r["bosluk_orani"], f(r["esik_adayi"]),
                 (" | DIGER olumsuz tarafta: %s; bosluk icinde: %s" % (r.get("diger_olumsuz_tarafta"), r.get("diger_bosluk_icinde"))) if r.get("diger") else "")) if r.get("temiz_bosluk") else "ORTUSUYOR"
        print("  %-48s + %s | - %s  => %s" % (r["ad"], " ".join("%s=%s" % (n, f(v)) for n, v in r["olumlu"]), " ".join("%s=%s" % (n, f(v)) for n, v in r["olumsuz"]), durum))
        if r.get("diger"):
            print("  %-48s   diger: %s" % ("", " ".join("%s=%s" % (n, f(v)) for n, v in r["diger"])))
