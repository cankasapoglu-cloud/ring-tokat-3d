#!/usr/bin/env python3
"""degerlendir.py - sinama kosularinin rapor.json dosyalarini toplar; her olcu icin araci-aynen-yeniden-calistirma gurultusunu
hesaplar; her bozuk surumde hangi olcunun gurultunun kac kati oynadigini ve aracin OZET satirlarinin degisip degismedigini cikarir.

Cikti: dinleme/sinama/sinama.json  (sinama.md bu sayilardan elle yazilir; tablolar: sinama_tablolar.md)

KARAR KURALLARI (kosulardan ONCE yazildi; sonuclara gore degistirilmedi)
- Gurultu: kusursuz 5 kopya {asil, yeniden kodlanmis MP3, WAV, yeniden karisim, 1 dB kisik + 23 ms kaydirilmis} arasinda olcunun
  en buyuk - en kucuk degeri (aralik). Aralik 0 cikarsa olcunun yazim cozunurlugu taban alinir.
- Fark: bozuk surum - taban (n3_yeniden_karisim; butun bozuk surumler ondan turetildi).
- Kat: |fark| / gurultu.
- "TEK RAPORLA YAKALANDI": aracin kendi ozetinde, kusurla ILGILI satirin durumu tabandakinden kotu (iyi/bilgi -> dikkat/sorun, dikkat -> sorun)
  ya da ilgili turde yeni bir 'sorun' kaydi var. Claude tek dosyayi olcup raporu okudugunda gorecegi sey budur.
- "KARSILASTIRMAYLA YAKALANDI": kusur icin ONCEDEN secilmis olculerden en az biri gurultunun 3 katindan fazla oynadi (kat >= 3).
  Yani yalniz iyi bilinen bir surumle yan yana olculurse gorulur.
- "KACTI": ikisi de degil.
"""
import os, sys, json, math

BURASI = os.path.dirname(os.path.abspath(__file__))
SINAMA = os.path.dirname(BURASI)
RAP = os.path.join(SINAMA, "raporlar")

# (kisa ad, json yolu, Turkce ad, yazim cozunurlugu)
OLCU = [
    ("lufs", "temel.lufs", "ses yüksekliği (LUFS)", 0.1),
    ("tepe", "temel.gercek_tepe_dbtp", "gerçek tepe (dBTP)", 0.1),
    ("tepe_faktoru", "temel.tepe_faktoru_db", "tepe faktörü (dB)", 0.1),
    ("lra", "temel.lra_lu", "ses yüksekliği aralığı (LU)", 0.1),
    ("tam_olcek", "temel.kirpilma.tam_olcek_ornek", "tam ölçekteki örnek sayısı", 1),
    ("ust_frekans", "temel.ust_frekans_hz", "üst frekans sınırı (Hz)", 50),
    ("tempo", "enerji.tempo_bpm", "tempo (BPM)", 0.1),
    ("nabiz", "enerji.nabiz_netligi", "nabız netliği", 0.005),
    ("olay", "enerji.olay_yogunlugu_sn", "olay yoğunluğu (1/sn)", 0.01),
    ("aki", "enerji.spektral_aki_ort", "spektral akı", 0.005),
    ("vurmali", "enerji.vurmali_armonik_db", "vurmalı/armonik (dB)", 0.05),
    ("parlaklik", "enerji.parlaklik_agirlik_merkezi_hz", "parlaklık (Hz)", 5),
    ("tiz_payi", "enerji.tiz_payi_4khz_ustu_db", "4 kHz üstü pay (dB)", 0.1),
    ("puan", "enerji.enerji_puani.puan_0_100", "hareketlilik puanı (0-100)", 1),
    ("coca", "musiccoca.cosku.fark", "MusicCoCa coşku farkı", 0.002),
    ("coca_tempo", "musiccoca.tempo.fark", "MusicCoCa hızlı-yavaş farkı", 0.002),
    ("coca_kalite", "musiccoca.kayit_kalitesi.fark", "MusicCoCa kayıt kalitesi farkı", 0.002),
    ("ninni", "etiket_karisim.ninni_olasiligi", "CED ninni olasılığı", 0.001),
    ("ced_cosku", "etiket_karisim.coskulu_eksi_sakin", "CED coşkulu - sakin", 0.002),
    ("denge", "kanallar.vokal_eksi_altyapi_db_medyan", "vokal - altyapı (dB)", 0.1),
    ("vokalli", "kanallar.vokalli_sure_orani", "vokalli süre oranı", 0.002),
    ("sizinti", "kanallar.sizinti.fark_db", "vokal kanalına sızıntı (dB)", 0.1),
    ("destek", "uyum.armonik_destek.fark", "armonik destek farkı", 0.002),
    ("kaydirma", "uyum.ton_kaydirma_denemesi.en_iyi_kaydirma_yarim_ses", "en iyi kaydırma (yarım ses)", 1),
    ("cent", "uyum.cent_sapma_medyan_mutlak", "notaya uzaklık medyan (cent)", 0.1),
    ("cent_isaretli", "uyum.cent_sapma_ortalama_isaretli", "notaya uzaklık ortalama, işaretli (cent)", 0.1),
    ("y25", "uyum.yuzde_25cent_icinde", "±25 cent içinde (%)", 0.1),
    ("akort_kaymasi", "uyum.vokal_akort_kaymasi_cent", "vokalin genel akort kayması (cent)", 1),
    ("izgara_R", "uyum.perde_izgaraya_yapisma_R", "perde ızgarasına yapışma R", 0.01),
    ("gam_ici", "uyum.gam_ici_sure_orani", "gam içi süre oranı", 0.002),
    ("akor_sesi", "uyum.akor_sesi_sure_orani", "akor sesi süre oranı", 0.002),
    ("cakisan", "uyum.cakisan_uzun_nota_sayisi", "çakışan uzun nota sayısı", 1),
    ("ritim_R", "ritim.sekizlik.sikilik_R", "ritim sıkılığı R (sekizlik)", 0.01),
    ("ritim_kayma", "ritim.sekizlik.ortalama_kayma_ms", "ortalama kayma, sekizlik (ms)", 1),
    ("ritim_40", "ritim.sekizlik.yuzde_40ms_icinde", "40 ms içinde (%)", 1),
    ("ritim16_R", "ritim.onaltilik.sikilik_R", "ritim sıkılığı R (onaltılık)", 0.01),
    ("ritim16_kayma", "ritim.onaltilik.ortalama_kayma_ms", "ortalama kayma, onaltılık (ms)", 1),
    ("baslangic", "ritim.vokal_baslangic_sayisi", "vokal başlangıç sayısı", 1),
    ("nota_sayisi", "perde.nota_sayisi", "nota sayısı", 1),
    ("nota_suresi", "perde.nota_suresi_medyan_sn", "nota süresi medyan (sn)", 0.005),
    ("oynaklik", "perde.nota_ici_oynaklik_cent_medyan", "nota içi oynaklık (cent)", 0.1),
    ("cok_duz", "perde.cok_duz_nota_orani", "çok düz nota oranı", 0.01),
    ("vibrato", "perde.vibratolu_uzun_nota_orani", "vibratolu uzun nota oranı", 0.01),
    ("gecis", "perde.gecis_cerceve_orani", "geçiş çerçevesi oranı", 0.01),
    ("sesli_oran", "perde.izleme.sesli_cerceve_orani", "perdeli çerçeve oranı", 0.002),
    ("pyin_uyum", "perde.izleme.pyin_ile_uyum_yuzde_50cent", "iki perde izleyicinin uyumu (%)", 0.1),
    ("yapay_isaret", "dogallik_vekilleri.isaret_sayisi", "yapaylık işareti sayısı", 1),
    ("gecis_ms", "dogallik_vekilleri.bagli_gecis_suresi_ms_medyan", "bağlı geçiş süresi (ms)", 16),
    ("donmus", "dogallik_vekilleri.donmus_sure_orani", "donmuş ünlü süre oranı", 0.005),
    ("benzerlik", "dogallik_vekilleri.sesli_cercevelerde_ardisik_benzerlik_medyan", "ardışık çerçeve benzerliği", 0.0005),
    ("unsuz_tiz", "dogallik_vekilleri.unsuzlerde_tiz_payi_db", "ünsüzlerde tiz payı (dB)", 0.1),
    ("vokal_ust", "dogallik_vekilleri.vokal_ust_frekans_hz", "vokalin üst frekansı (Hz)", 50),
    ("tiz_doku", "dogallik_vekilleri.tiz_doku_degisim_katsayisi", "tiz doku değişim katsayısı", 0.01),
    ("zarf", "dogallik_vekilleri.zarf_titremesi_db", "zarf titremesi (dB)", 0.1),
    ("dnsmos", "kalite_tahminleri.dnsmos.genel", "DNSMOS", 0.01),
    ("nisqa", "kalite_tahminleri.nisqa.genel", "NISQA", 0.01),
    ("nisqa_kes", "kalite_tahminleri.nisqa.kesintisizlik", "NISQA kesintisizlik", 0.01),
    ("nisqa_renk", "kalite_tahminleri.nisqa.renklenmezlik", "NISQA renklenmezlik", 0.01),
    ("distillmos", "kalite_tahminleri.distillmos.genel", "Distill-MOS", 0.01),
    ("utmos", "kalite_tahminleri.utmos22.genel", "UTMOS22", 0.01),
    ("ced_sarki", "etiket_vokal.ses_turu.Singing", "CED (vokal) şarkı olasılığı", 0.002),
    ("ced_sentetik", "etiket_vokal.ses_turu.Synthetic singing", "CED (vokal) sentetik şarkı olasılığı", 0.002),
    ("wer", "sozler.karsilastirma.sozcuk_hata_orani", "sözcük hata oranı", 0.005),
    ("hece", "sozler.hece_hizi.obek_hece_sn_medyan", "hece hızı (hece/sn)", 0.05),
]
OLCU_AD = {k: ad for k, _, ad, _ in OLCU}
GURULTU_KUMESI = ["00_asil_a", "n1_yeniden_kodlama", "n2_wav", "n3_yeniden_karisim", "n4_kisik_kaydirilmis"]
TABAN = "n3_yeniden_karisim"
SIRA = {"iyi": 0, "bilgi": 0, "ölçülemedi": 0, "dikkat": 1, "sorun": 2}

# Her kusur icin ONCEDEN secilen: ilgili ozet satirlari, ilgili olculer, ilgili sorun turleri
KUSUR = [
    {"no": "1a", "ad": "b01a_detone_50c", "kusur": "Vokal 50 cent tiz (detone)", "satir": ["Akort (detone mi)", "Vokal altyapıyla aynı armonide mi", "Çakışan uzun notalar"],
     "olcu": ["cent", "y25", "akort_kaymasi", "cent_isaretli", "destek", "cakisan"], "sorun": ["çakışan / detone nota"]},
    {"no": "1b", "ad": "b01b_detone_100c", "kusur": "Vokal 100 cent (yarım ses) tiz", "satir": ["Akort (detone mi)", "Vokal altyapıyla aynı armonide mi", "Çakışan uzun notalar", "Gam içi söyleme"],
     "olcu": ["destek", "kaydirma", "cakisan", "gam_ici", "akor_sesi", "akort_kaymasi"], "sorun": ["çakışan / detone nota"]},
    {"no": "2a", "ad": "b02a_gec_ceyrek", "kusur": "Vokal çeyrek vuruş (129 ms) geç", "satir": ["Ritme oturma"],
     "olcu": ["ritim_kayma", "ritim_R", "ritim_40", "ritim16_kayma", "ritim16_R"], "sorun": []},
    {"no": "2b", "ad": "b02b_gec_yarim", "kusur": "Vokal yarım vuruş (259 ms) geç", "satir": ["Ritme oturma"],
     "olcu": ["ritim_kayma", "ritim_R", "ritim_40", "ritim16_kayma", "ritim16_R"], "sorun": []},
    {"no": "3a", "ad": "b03a_esnetme_15", "kusur": "Vokal 1,5 kat vokoder esnetmesi dokusunda (süre ve perde aynı)", "satir": ["Yapaylık işaretleri (vekil)"],
     "olcu": ["yapay_isaret", "donmus", "benzerlik", "zarf", "tiz_doku", "unsuz_tiz", "dnsmos", "nisqa", "distillmos", "utmos"], "sorun": ["donmuş ünlü"]},
    {"no": "3b", "ad": "b03b_esnetme_20", "kusur": "Vokal 2 kat vokoder esnetmesi dokusunda (süre ve perde aynı)", "satir": ["Yapaylık işaretleri (vekil)"],
     "olcu": ["yapay_isaret", "donmus", "benzerlik", "zarf", "tiz_doku", "unsuz_tiz", "dnsmos", "nisqa", "distillmos", "utmos"], "sorun": ["donmuş ünlü"]},
    {"no": "4", "ad": "b04_duz_perde", "kusur": "Vokalin perdesi hece başına düzleştirilmiş (otomatik akort benzeri)", "satir": ["Yapaylık işaretleri (vekil)"],
     "olcu": ["yapay_isaret", "oynaklik", "cok_duz", "gecis_ms", "vibrato", "izgara_R", "gecis"], "sorun": [], "denetim": "b04k_world_kontrol"},
    {"no": "5", "ad": "b05_tik", "kusur": "Her 3 saniyede bir tık (36 adet)", "satir": ["Kırpılma", "Tepe"],
     "olcu": ["tepe", "tam_olcek", "tepe_faktoru"], "sorun": ["kırpılma / sessizlik"]},
    {"no": "6a", "ad": "b06a_vokal_eksi6", "kusur": "Vokal 6 dB kısık", "satir": ["Vokal / altyapı dengesi"], "olcu": ["denge"], "sorun": ["gömük vokal"]},
    {"no": "6b", "ad": "b06b_vokal_arti6", "kusur": "Vokal 6 dB fazla açık", "satir": ["Vokal / altyapı dengesi"], "olcu": ["denge"], "sorun": []},
    {"no": "7", "ad": "b07_satir_sonu_kesik", "kusur": "Her satırın son sözcüğü 150 ms erken kesilmiş", "satir": ["Sözler"],
     "olcu": ["wer", "vokalli", "sesli_oran", "nisqa_kes"], "sorun": ["söz hatası"], "kisa": "c07_satir_sonu_kesik_kita12"},
    {"no": "8", "ad": "b08_yanlis_satir", "kusur": "Bir satırın yerine başka satır söyleniyor (yanlış söz)", "satir": ["Sözler"],
     "olcu": ["wer"], "sorun": ["söz hatası"], "kisa": "c08_yanlis_satir_kita12"},
    {"no": "9", "ad": "b09_tempo_80", "kusur": "Bütün şarkı %80 tempoya yavaşlatılmış (enerji düşük)", "satir": ["Enerji / coşku"],
     "olcu": ["tempo", "puan", "olay", "coca", "coca_tempo", "ninni"], "sorun": []},
    {"no": "10", "ad": "b10_alcak_geciren_4k", "kusur": "Bütün karışım 4 kHz'de kesilmiş (boğuk)", "satir": ["Yapaylık işaretleri (vekil)", "Enerji / coşku"],
     "olcu": ["ust_frekans", "parlaklik", "tiz_payi", "vokal_ust", "unsuz_tiz"], "sorun": []},
]


def al(R, yol):
    o = R
    for p in yol.split("."):
        if not isinstance(o, dict) or p not in o:
            return None
        o = o[p]
    return o if isinstance(o, (int, float)) and not isinstance(o, bool) else None


def yukle(ad):
    y = os.path.join(RAP, ad, "rapor.json")
    return json.load(open(y, encoding="utf8")) if os.path.exists(y) else None


def olculer(R):
    d = {k: al(R, yol) for k, yol, _, _ in OLCU}
    d["sorun_sayisi"] = len(R.get("sorunlar") or [])
    return d


def ozet(R):
    return {o["konu"]: o["durum"] for o in R.get("ozet", [])}


def sorun_turleri(R):
    c = {}
    for s in R.get("sorunlar") or []:
        c[s["sira"]] = c.get(s["sira"], 0) + 1
    return c


def yuv(x, n=3):
    return None if x is None else round(float(x), n)


def main():
    adlar = sorted(d for d in os.listdir(RAP) if os.path.exists(os.path.join(RAP, d, "rapor.json")))
    RJ = {a: yukle(a) for a in adlar}
    M = {a: olculer(RJ[a]) for a in adlar}
    OZ = {a: ozet(RJ[a]) for a in adlar}
    # ---- gurultu
    G = {}
    var = [a for a in GURULTU_KUMESI if a in M]
    for k, _, ad, coz in OLCU:
        v = [M[a][k] for a in var if M[a][k] is not None]
        if len(v) >= 2:
            ar = max(v) - min(v)
            ort = sum(v) / len(v)
            ss = math.sqrt(sum((x - ort) ** 2 for x in v) / (len(v) - 1))
            G[k] = {"n": len(v), "en_az": min(v), "en_cok": max(v), "aralik": yuv(ar, 4), "std": yuv(ss, 4), "gurultu": yuv(max(ar, coz), 4), "degerler": {a: M[a][k] for a in var}}
    sonuc = {"aciklama": __doc__.split("KARAR KURALLARI")[1].strip(), "gurultu_kumesi": var, "taban": TABAN, "gurultu": G,
             "olcu_adlari": OLCU_AD, "kosular": {a: {"olculer": M[a], "ozet": OZ[a], "sorun_turleri": sorun_turleri(RJ[a]),
                                                    "hatalar": RJ[a].get("hatalar"), "kanal_kaynagi": RJ[a].get("kanal_kaynagi")} for a in adlar}}

    def karsilastir(ad, taban, kusur):
        if ad not in M or taban not in M:
            return None
        fark = {}
        for k, _, _, coz in OLCU:
            a, b = M[ad][k], M[taban][k]
            if a is None or b is None or k not in G:
                continue
            g = G[k]["gurultu"]
            fark[k] = {"taban": b, "bozuk": a, "fark": yuv(a - b, 4), "gurultu": g, "kat": yuv(abs(a - b) / g, 1)}
        # ozet satirlari
        kotulesen, hepsi = [], []
        for konu in set(OZ[ad]) | set(OZ[taban]):
            d0, d1 = OZ[taban].get(konu), OZ[ad].get(konu)
            if d1 is not None and SIRA.get(d1, 0) > SIRA.get(d0 or "iyi", 0):
                hepsi.append({"konu": konu, "taban": d0, "bozuk": d1})
                if konu in kusur["satir"]:
                    kotulesen.append({"konu": konu, "taban": d0, "bozuk": d1})
        st0, st1 = sorun_turleri(RJ[taban]), sorun_turleri(RJ[ad])
        yeni_sorun = {t: st1.get(t, 0) - st0.get(t, 0) for t in kusur["sorun"] if st1.get(t, 0) > st0.get(t, 0)}
        ilgili = {k: fark[k] for k in kusur["olcu"] if k in fark}
        en_iyi = max(ilgili.items(), key=lambda kv: kv[1]["kat"]) if ilgili else None
        diger = sorted(((k, v) for k, v in fark.items() if k not in kusur["olcu"] and v["kat"] >= 3), key=lambda kv: -kv[1]["kat"])
        tek = bool(kotulesen or yeni_sorun)
        ab = bool(en_iyi and en_iyi[1]["kat"] >= 3)
        return {"tek_raporla": tek, "karsilastirmayla": ab, "karar": "tek raporla yakalandı" if tek else ("yalnız karşılaştırmayla yakalandı" if ab else "kaçtı"),
                "kotulesen_ilgili_satirlar": kotulesen, "kotulesen_butun_satirlar": hepsi, "yeni_ilgili_sorunlar": yeni_sorun,
                "ilgili_olculer": ilgili, "en_cok_oynayan_ilgili_olcu": ({"olcu": en_iyi[0], "ad": OLCU_AD[en_iyi[0]], **en_iyi[1]} if en_iyi else None),
                "ilgili_olmayan_ama_3_kat_oynayanlar": [{"olcu": k, "ad": OLCU_AD[k], **v} for k, v in diger[:12]]}

    T = []
    for ks in KUSUR:
        s = {"no": ks["no"], "ad": ks["ad"], "kusur": ks["kusur"], "ayirma_yolu": karsilastir(ks["ad"], TABAN, ks)}
        if ks.get("denetim"):
            s["denetim"] = {"ad": ks["denetim"], "sonuc": karsilastir(ks["denetim"], TABAN, ks)}
        v = "v_" + ks["ad"]
        if v in M and "v_" + TABAN in M:
            s["kanalli_yol"] = karsilastir(v, "v_" + TABAN, ks)
        T.append(s)
    sonuc["kusurlar"] = T
    json.dump(sonuc, open(os.path.join(SINAMA, "sinama_ham.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)

    # ---- okunur dokum
    L = []
    L.append("## Gürültü (kusursuz %d kopya: %s)\n" % (len(var), ", ".join(var)))
    L.append("| ölçü | " + " | ".join(var) + " | aralık | gürültü |")
    L.append("|---|" + "---|" * (len(var) + 2))
    for k, _, ad, _ in OLCU:
        if k in G:
            L.append("| %s | %s | %s | %s |" % (ad, " | ".join(str(M[a][k]) for a in var), G[k]["aralik"], G[k]["gurultu"]))
    L.append("")
    for s in T:
        for yol in ("ayirma_yolu", "kanalli_yol"):
            c = s.get(yol)
            if not c:
                continue
            L.append("## %s  %s  [%s]  -> %s\n" % (s["no"], s["kusur"], yol, c["karar"].upper()))
            L.append("ozet satirlari (ilgili, kotulesen): %s ; butun kotulesenler: %s ; yeni ilgili sorunlar: %s\n" % (
                c["kotulesen_ilgili_satirlar"], c["kotulesen_butun_satirlar"], c["yeni_ilgili_sorunlar"]))
            L.append("| ilgili ölçü | taban | bozuk | fark | gürültü | kat |")
            L.append("|---|---|---|---|---|---|")
            for k, v in c["ilgili_olculer"].items():
                L.append("| %s | %s | %s | %s | %s | %s |" % (OLCU_AD[k], v["taban"], v["bozuk"], v["fark"], v["gurultu"], v["kat"]))
            if c["ilgili_olmayan_ama_3_kat_oynayanlar"]:
                L.append("\nilgili sayilmayan ama 3 kattan fazla oynayanlar: " + "; ".join("%s %s->%s (%sx)" % (v["ad"], v["taban"], v["bozuk"], v["kat"]) for v in c["ilgili_olmayan_ama_3_kat_oynayanlar"]))
            L.append("")
        if s.get("denetim") and s["denetim"]["sonuc"]:
            c = s["denetim"]["sonuc"]
            L.append("### denetim %s -> %s" % (s["denetim"]["ad"], c["karar"]))
            for k, v in c["ilgili_olculer"].items():
                L.append("- %s: %s -> %s (%sx)" % (OLCU_AD[k], v["taban"], v["bozuk"], v["kat"]))
            L.append("")
    open(os.path.join(SINAMA, "sinama_tablolar.md"), "w", encoding="utf8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
