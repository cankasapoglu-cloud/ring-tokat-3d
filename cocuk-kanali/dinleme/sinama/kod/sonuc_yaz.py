#!/usr/bin/env python3
"""sonuc_yaz.py - sinama_ham.json (degerlendir.py ciktisi) + kisa parca sozleri + elle yazilmis notlardan sinama.json uretir
ve sinama.md icin tespit tablosunu (sinama_tablo_ozet.md) basar.  Once degerlendir.py calistirilmalidir."""
import os, sys, json

BURASI = os.path.dirname(os.path.abspath(__file__))
SINAMA = os.path.dirname(BURASI)
DINLEME = os.path.dirname(SINAMA)
sys.path.insert(0, BURASI)
import degerlendir as d


def tr(x, n=None):
    if x is None:
        return "—"
    if isinstance(x, float):
        if n is None:
            n = 0 if abs(x) >= 100 else (1 if abs(x) >= 10 or float(x).is_integer() else (2 if abs(x) >= 0.1 else 3))
        s = ("%." + str(n) + "f") % x
        if "." in s:
            s = s.rstrip("0").rstrip(".") if n > 1 else s
        return s.replace(".", ",")
    return str(x)


# Elle yazilan aciklamalar (sayilar asagida kosulardan otomatik gelir)
NOT = {
    "1a": "Araç 'Akort' satırını ❌ yaptı ve 14 uzun notayı tek tek detone diye işaretledi. Ölçtüğü kayma +46 cent (gerçek: +50).",
    "1b": "Tam yarım ses kayınca 'Akort' satırı ✅ kalır (notalar yine ızgaraya oturuyor); kusuru 'aynı armonide mi' satırı yakaladı: destek eksiye döndü, 'en iyi kaydırma −1' çıktı, 21 uzun nota çakışıyor.",
    "2a": "Araç satıra ✅ 'iyi' yazdı, çünkü durum yalnız sıkılığa (R) bakıyor ve R arttı. Aynı satırdaki sayı ise kusuru gösteriyor: başlangıçların yalnız %6'sı ızgaraya 40 ms içinde, kayma −109 ms. Yön yanlış: 129 ms geç olan vokal 'erken' görünüyor (yarım sekizlik kayma, ileri mi geri mi ayırt edilemez).",
    "2b": "Hiçbir ritim sayısı oynamadı. Araç başlangıçları sekizlik ızgaraya göre ölçer; tam bir sekizlik (yarım vuruş) kayan vokal yine ızgaranın üstüne düşer. Kanallar elde olsa da sonuç aynı.",
    "3a": "Yapaylık satırı 'işaret yok' dedi. Karşılaştırınca: zarf titremesi ve konuşma-kalitesi tahminleri (Distill-MOS, UTMOS22) belirgin düştü. Kuru vokalde de aynı (aşağıda).",
    "3b": "3a ile aynı. Kanallar elde verilince araç 1 yapaylık işareti verdi (ama 'basamaklı perde' diye, yani doğru satır, yanlış gerekçe).",
    "4": "2 yapaylık işareti: 'notaların içi çok düz' ve 'geçişler ani'. Aynı vokoderden perdeye dokunmadan geçirilen denetim sürümünde işaret çıkmadı; yani yakalanan şey düzleştirme, vokoder değil.",
    "5": "Hiçbir sayı oynamadı, panoda da görünmüyor (asıl ve tıklı panolar yan yana aynı). 'Tepe' satırı çıktı ama o satır asıl kayıtta da var; tıkla ilgisi yok. Not: bu tık çok kısa (0,18 ms); tiz bantta çoğu yerde müziğin 12 dB üstünde, bütün bantta müziğin içinde kayboluyor.",
    "5c": "Şüphe götürmeyecek kadar duyulur bir çıtırtı (5 ms, tiz bantta müziğin 27 dB üstünde, 36 kez). Aracın bunu doğrudan arayan bir ölçüsü yok.",
    "5b": "Kısık tık: çoğu yerde müzik örter, duyulup duyulmadığı şüpheli. SAYIMA KATILMADI.",
    "6a": "Araç ölçtü: vokal altyapının 9,8 dB altında (tabanda 4,1); eşik −6. Ayrıca 5 yerde 'gömük vokal' diye zaman verdi.",
    "6b": "Araç farkı doğru ölçtü (+6,6 dB; gerçek +6) ama 'çok açık' eşiği +9 dB olduğu için satır ✅ kaldı.",
    "7": "Scribe kesik sözcükleri tamamlayıp doğru yazdı ('va' → 'var', 'ba' → 'bak'): sözcük hata oranı %0, düşük güvenli sözcük yok. Tek iz: vokalli süre oranı %58,0 → %57,1 ve perdeli çerçeve oranı; gürültünün 4 katı kadar, kusurun ne olduğunu söylemeyen küçük oynamalar. Panoda, asıl sürümle yan yana bakılırsa satır aralarındaki boşluklar görülüyor.",
    "8": "Sözler satırı ⚠️ oldu: iki yanlış sözcük, yeri ve kendisiyle ('Koyunlar' yerine 'İnekler', 'meler' yerine 'bağırır'). Yalnız söz dosyası + ücretli döküm varsa çalışır; onlarsız hiçbir sayı oynamaz (ezgi aynı).",
    "9": "Tempo 116 → 93 BPM diye doğru ölçüldü ama Enerji satırı ✅ 'coşkulu yana yakın' kaldı (hareketlilik 69, eşik 62; MusicCoCa +0,09, eşik 0).",
    "10": "2 yapaylık işareti (ünsüzlerde tiz yok; vokalin enerjisi 4,8 kHz'de bitiyor) ve Enerji satırı ⚠️. Dosyanın üst frekans sınırı 18,8 → 5,2 kHz.",
}
SIRA = ["1a", "1b", "2a", "2b", "3a", "3b", "4", "5", "5c", "6a", "6b", "7", "8", "9", "10"]
ISTENEN = ["1a", "1b", "2a", "2b", "3a", "3b", "4", "5", "6a", "6b", "7", "8", "9", "10"]            # gorevde sayilan 14 surum
OLCU_SEC = {"1a": "cent", "1b": "destek", "2a": "ritim_kayma", "2b": "ritim_kayma", "3a": "zarf", "3b": "zarf", "4": "cok_duz", "5": "tepe", "5b": "tepe", "5c": "tepe",
            "6a": "denge", "6b": "denge", "7": "vokalli", "8": "wer", "9": "tempo", "10": "ust_frekans"}
IKINCI = {"1a": "y25", "1b": "cakisan", "2a": "ritim_40", "3a": "distillmos", "3b": "distillmos", "4": "oynaklik", "9": "coca", "10": "unsuz_tiz", "7": "sesli_oran"}


def main():
    H = json.load(open(os.path.join(SINAMA, "sinama_ham.json"), encoding="utf8"))
    K = {k["no"]: k for k in H["kusurlar"]}
    kos = H["kosular"]
    # kisa parcalar (sozler)
    def soz(ad):
        R = d.yukle(ad)
        S = (R or {}).get("sozler") or {}
        kr = S.get("karsilastirma") or {}
        return {"dosya": ad, "duyulan": S.get("duyulan_metin"), "sozcuk_hata_orani": kr.get("sozcuk_hata_orani"), "yanlis": kr.get("yanlis_sozcukler"),
                "eksik": kr.get("eksik_sozcukler"), "fazla": kr.get("fazla_sozcukler"), "dusuk_guvenli": S.get("dusuk_guvenli_sozcukler"),
                "hece_sn": (S.get("hece_hizi") or {}).get("obek_hece_sn_medyan"), "kredi": (S.get("dokum_kaynagi") or {}).get("kredi"),
                "sozler_satiri": next((o["durum"] for o in (R or {}).get("ozet", []) if o["konu"] == "Sözler"), None)}
    c07, c08, k13 = soz("c07_satir_sonu_kesik_kita12"), soz("c08_yanlis_satir_kita12"), soz("k13b_kita1_esnetme_20")
    T = []
    for no in SIRA:
        if no not in K or not K[no]["ayirma_yolu"]:
            continue
        s = K[no]
        c = s["ayirma_yolu"]
        o = c["ilgili_olculer"].get(OLCU_SEC[no]) or {}
        o2 = c["ilgili_olculer"].get(IKINCI.get(no, "")) or {}
        sonuc = c["karar"]
        guc = None
        if no == "8":                                           # sozler kisa parcada olculdu
            sonuc = "tek raporla yakalandı" if c08["sozler_satiri"] in ("dikkat", "sorun") else "kaçtı"
            o = {"taban": c07["sozcuk_hata_orani"], "bozuk": c08["sozcuk_hata_orani"], "fark": c08["sozcuk_hata_orani"] - c07["sozcuk_hata_orani"], "gurultu": None, "kat": None}
        if no == "7":
            guc = "zayıf"
        if no in ("5", "5b", "5c"):
            pass
        satir = "; ".join("%s: %s → %s" % (x["konu"], x.get("kusursuz_kopyalarin_en_kotusu") or "yok", x["bozuk"]) for x in c["kotulesen_ilgili_satirlar"]) or "ilgili satır değişmedi"
        if no == "8":
            satir = "Sözler: iyi → %s (kısa parçada, Scribe ile)" % c08["sozler_satiri"]
        kay = {"no": no, "kusur": s["kusur"], "dosya": s["ad"], "sonuc": sonuc, "guc": guc, "aracin_ozet_satiri": satir,
               "olcu": d.OLCU_AD[OLCU_SEC[no]], "taban": o.get("taban"), "bozuk": o.get("bozuk"), "fark": o.get("fark"), "gurultu": o.get("gurultu"), "kat": o.get("kat"),
               "ikinci_olcu": ({"olcu": d.OLCU_AD[IKINCI[no]], **o2} if o2 else None),
               "ilgisiz_kotulesen_satirlar": [x["konu"] for x in c["kotulesen_butun_satirlar"] if x["konu"] not in [y["konu"] for y in c["kotulesen_ilgili_satirlar"]]],
               "kanallar_elde_yolu": (s.get("kanalli_yol") or {}).get("karar"), "sayima_dahil": no in ISTENEN, "not": NOT.get(no, "")}
        T.append(kay)
    say = {}
    for k in T:
        if k["sayima_dahil"]:
            say[k["sonuc"]] = say.get(k["sonuc"], 0) + 1
    # yanlis alarmlar
    def alarmlar(ad):
        R = d.yukle(ad)
        return [{"durum": o["durum"], "konu": o["konu"], "bulgu": o["bulgu"]} for o in R["ozet"] if o["durum"] in ("dikkat", "sorun")]
    ya = {"asil_dinle_2": alarmlar("00_asil_a"), "ikinci_el_yikama_coskulu_2": alarmlar("e1_el_yikama_coskulu_2")}
    # kuru esnetme
    kuru = {a: {k: kos[a]["olculer"][k] for k in ("yapay_isaret", "zarf", "benzerlik", "donmus", "dnsmos", "nisqa", "distillmos", "utmos", "oynaklik", "ced_sentetik")}
            for a in ("k00_kuru_vokal", "k03a_kuru_esnetme_15", "k03b_kuru_esnetme_20") if a in kos}
    kanalli = {k["no"]: {"sonuc": k.get("kanalli_yol", {}).get("karar"), "olculer": k["kanalli_yol"]["ilgili_olculer"]} for k in H["kusurlar"] if k.get("kanalli_yol")}
    defter = json.load(open(os.path.join(DINLEME, "onbellek", "kredi_defteri.json"), encoding="utf8"))
    benim = [x for x in defter["kayitlar"] if x["dosya"].startswith(("c07_", "c08_", "k13b_"))]
    S = {
        "ne": "Dinleme takiminin (dinleme/arac/dinle.py 1.0) karsi sinamasi: kabul edilmis bir kayda TEK bilinen kusur eklenip aracin fark edip etmedigine bakildi.",
        "tarih": "2026-11-21",
        "uyari": "Kusurlari Claude duyamadi; her kusurun varligi aractan bagimsiz olcumlerle dogrulandi (bozuk_dogrulama.json). 'Dinleyici fark eder' yargisi varsayimdir.",
        "yontem": {
            "kaynak": "cocuk-kanali/ali-baba/dinle_2.mp3 ve onun UVR-MDX-NET-Voc_FT ile ayrilmis vokal/altyapi kanallari (toplamlari asil dosyayi -42 dB artikla verir)",
            "taban": "n3_yeniden_karisim (kanallarin toplami, 192 kb/sn MP3); butun bozuk surumler bundan tek degisiklikle turetildi",
            "ana_yol": "dinle.py <bozuk.mp3> --ayir  (bitmis dosya; arac vokali kendisi ayirir)",
            "ikinci_yol": "dinle.py <bozuk.mp3> --vokal <bozuk vokal kanali> --altyapi <altyapi kanali> --hizli  (kanallar elde)",
            "sozler": "ucretli Scribe dokumu yalniz 22,5 sn'lik iki kisa parcada (7 ve 8 numarali kusurlar) ve 18 sn'lik bir kuru parcada yapildi (kredi siniri)",
            "karar_kurallari": H["aciklama"],
        },
        "tekrar_calistirma": "Ayni dosya iki kez olculdu: 320 sayisal alanin hepsi birebir ayni (yalniz calisma sureleri farkli). Arac belirlenimci.",
        "gurultu": {k: {"ad": d.OLCU_AD[k], "aralik": v["aralik"], "gurultu": v["gurultu"], "degerler": v["degerler"]} for k, v in H["gurultu"].items()},
        "tespit_tablosu": T,
        "sayim_gorevdeki_14_surum": say,
        "kanallar_elde_yolu": kanalli,
        "kuru_vokalde_esnetme": {"olculer": kuru, "scribe_2_kat_esnetilmis_1_kita": k13},
        "soz_denetimi_kisa_parcalar": {"c07_satir_sonu_kesik": c07, "c08_yanlis_satir": c08},
        "yanlis_alarmlar": ya,
        "kredi": {"bu_sinamanin_harcadigi": round(sum(x["tahmini_kredi"] for x in benim), 1), "cagrilar": benim, "defter_toplami": defter.get("toplam_tahmini_kredi"), "sinir": defter.get("sinir")},
    }
    json.dump(S, open(os.path.join(SINAMA, "sinama.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    # ---- ozet tablo
    im = {"tek raporla yakalandı": "✅ yakalandı", "yalnız karşılaştırmayla yakalandı": "🔶 yalnız karşılaştırınca", "kaçtı": "❌ kaçtı"}
    L = ["| No | Kusur | Sonuç | En çok oynayan ölçü | Asıl → bozuk | Gürültünün kaç katı | Kanallar elde olunca |", "|---|---|---|---|---|---|---|"]
    for k in T:
        son = im[k["sonuc"]] + (" (zayıf)" if k["guc"] else "") + ("" if k["sayima_dahil"] else " *")
        L.append("| %s | %s | %s | %s | %s → %s | %s | %s |" % (k["no"], k["kusur"], son, k["olcu"], tr(k["taban"]), tr(k["bozuk"]), (tr(k["kat"]) + " kat") if k["kat"] is not None else "—",
                                                            {"tek raporla yakalandı": "yakalandı", "yalnız karşılaştırmayla yakalandı": "yalnız karşılaştırınca", "kaçtı": "kaçtı", None: "denenmedi"}[k["kanallar_elde_yolu"]]))
    open(os.path.join(SINAMA, "sinama_tablo_ozet.md"), "w", encoding="utf8").write("\n".join(L) + "\n")
    print("\n".join(L))
    print(json.dumps(say, ensure_ascii=False))
    for k in T:
        print(k["no"], "|", k["aracin_ozet_satiri"], "| ilgisiz:", k["ilgisiz_kotulesen_satirlar"], "| ikinci:", k["ikinci_olcu"] and (k["ikinci_olcu"]["olcu"], k["ikinci_olcu"]["taban"], k["ikinci_olcu"]["bozuk"], k["ikinci_olcu"]["kat"]))


if __name__ == "__main__":
    main()
