#!/usr/bin/env python3
"""yan_yana.py - dinle.py raporlarini KALIBRE EDILMIS gozle okur; iki (ya da daha cok) raporu yan yana koyar.

Neden var: dinle.py'nin kendi ozet satirlarindaki esikler kabadir (kalibrasyonda begenilen kayitlarda da yanlis alarm verdiler).
Kullanicinin kulagiyla temiz ayrisan yalnizca uc sey cikti: SURE, ENERJI (MusicCoCa + CED 'ninni' birlikte) ve SOZLER.
Geri kalan sayilar ancak AYNI sarkinin iki hali yan yana olculunce anlam tasiyor (sinama: olcum gurultusunun 3 kati).
Kaynak: dinleme/kalibrasyon/kalibrasyon.md (17 kayit) ve dinleme/sinama/sinama.md (14 bozuk surum). Ornek sayisi kucuktur.

KULLANIM
  python3 yan_yana.py <rapor klasoru ya da rapor.json> [<ikinci rapor> ...]
  Iki rapor verilirse: ilki REFERANS (begenilen / onceki surum), ikincisi YENI kabul edilir; farklar gurultuyle karsilastirilir.
Ag gerektirmez, kredi harcamaz. Bu da bir olcum okumasidir; insan kulagi degildir.
"""
import json, os, sys

# (etiket, rapor.json icindeki yol, bicim, olcum gurultusu [sinama.md: kusursuz 5 kopya arasindaki en buyuk fark])
OLCULER = [
    ("süre (sn)",                        "temel/sure_sn",                                   "%.0f",  None),
    ("MusicCoCa coşku farkı",            "musiccoca/cosku/fark",                            "%+.2f", 0.009),
    ("CED 'ninni' olasılığı",            "etiket_karisim/ninni_olasiligi",                  "%.3f",  None),
    ("tempo (BPM)",                      "enerji/tempo_bpm",                                "%.1f",  0.1),
    ("hareketlilik puanı",               "enerji/enerji_puani/puan_0_100",                  "%.0f",  1.0),
    ("sözcük hata oranı (%)",            "sozler/karsilastirma/sozcuk_hata_orani",          "%%%.1f", None),
    ("vokal − altyapı (dB)",             "kanallar/vokal_eksi_altyapi_db_medyan",           "%+.1f", 3.0),
    ("armonik destek farkı",             "uyum/armonik_destek/fark",                        "%+.2f", 0.04),
    ("en iyi kaydırma (yarım ses)",      "uyum/ton_kaydirma_denemesi/en_iyi_kaydirma_yarim_ses", "%+d", None),
    ("notaya uzaklık (cent)",            "uyum/cent_sapma_medyan_mutlak",                   "%.1f",  0.4),
    ("çakışan uzun nota",                "uyum/cakisan_uzun_nota_sayisi",                   "%d",    None),
    ("ritim kayması (ms)",               "ritim/sekizlik/ortalama_kayma_ms",                "%+.0f", 2.0),
    ("40 ms içindeki başlangıç (%)",     "ritim/sekizlik/yuzde_40ms_icinde",                "%.0f",  None),
    ("çok düz nota oranı",               "perde/cok_duz_nota_orani",                        "%.2f",  None),
    ("donmuş ünlü süresi oranı",         "dogallik_vekilleri/donmus_sure_orani",            "%.2f",  None),
    ("zarf titremesi (dB)",              "dogallik_vekilleri/zarf_titremesi_db",            "%.1f",  0.6),
    ("UTMOS22 (yalnız karşılaştırma)",   "kalite_tahminleri/utmos22/genel",                 "%.2f",  0.01),
]
GURULTU_KATI = 3.0          # sinama.md'deki karar kurali: gurultunun 3 katindan buyuk fark "oynadi" sayilir


def yukle(yol):
    if os.path.isdir(yol):
        yol = os.path.join(yol, "rapor.json")
    return json.load(open(yol, encoding="utf8"))


def al(d, yol):
    for k in yol.split("/"):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def deger(d, yol):
    v = al(d, yol)
    if v is not None and yol.endswith("sozcuk_hata_orani"):
        v = v * 100.0
    return v


def kalibre_okuma(d):
    """Yalnizca kalibrasyonda temiz ayrisan boyutlar icin hukum; digerleri icin hukum YOK."""
    s = []
    sure = al(d, "temel/sure_sn")
    if sure is not None:
        s.append(("Süre", "ÇOK UZUN (180 sn üstü; kullanıcı 186 ve 213 sn'yi reddetti)" if sure > 180 else "kabul edilen aralıkta (en uzun kabul 155 sn)"))
    mc, ced = al(d, "musiccoca/cosku/fark"), al(d, "etiket_karisim/ninni_olasiligi")
    if mc is not None and ced is not None:
        mc2 = round(mc, 2)
        if mc2 >= 0.09 and ced < 0.01:
            e = "COŞKULU yanda (MusicCoCa %+.2f ≥ +0,09 ve CED ninni %.3f)" % (mc, ced)
        elif mc2 <= -0.04 and ced >= 0.01:
            e = "NİNNİ yanında (MusicCoCa %+.2f ≤ −0,04 ve CED ninni %.3f ≥ 0,01)" % (mc, ced)
        else:
            e = "KARARSIZ (MusicCoCa %+.2f, CED ninni %.3f: iki gösterge aynı yanı göstermiyor ya da arada)" % (mc, ced)
        s.append(("Enerji", e))
    k = al(d, "sozler/karsilastirma")
    if k:
        who = k.get("sozcuk_hata_orani", 0) * 100
        yan = ["%.0f. sn '%s' yerine '%s'" % (y.get("zaman", 0), y.get("beklenen"), y.get("duyulan")) for y in k.get("yanlis_sozcukler", [])[:8]]
        eks = ["%s" % (y.get("beklenen") or y.get("sozcuk") or "?") for y in k.get("eksik_sozcukler", [])[:8]]
        if who >= 30:
            m = "MAKİNE SÖZLERİ ANLAMIYOR (hata %%%.0f ≥ %%30): vokal bozulmuş olabilir" % who
        else:
            m = "hata %%%.1f (yüzde tek başına karar değildir; aşağıdaki sözcüklere kıta kıta bakın)" % who
        if yan:
            m += " | yanlış: " + "; ".join(yan)
        if eks:
            m += " | eksik: " + ", ".join(eks)
        if k.get("fazla"):
            m += " | fazla sözcük: %d" % k["fazla"]
        s.append(("Sözler", m))
    else:
        s.append(("Sözler", "DENETLENMEDİ (--sozler verilmemiş): en güçlü denetim eksik"))
    s.append(("Aksan, hoşluk, ezgi", "ÖLÇÜLEMEZ: kullanıcının kulağı"))
    return s


def main(arg):
    if not arg or arg[0] in ("-h", "--help"):
        sys.exit(__doc__)
    R = [yukle(a) for a in arg]
    adlar = [os.path.basename(os.path.dirname(os.path.abspath(a if not os.path.isdir(a) else os.path.join(a, "x")))) for a in arg]
    for ad, d in zip(adlar, R):
        print("== %s  (%s; kanal kaynağı: %s)" % (ad, os.path.basename(d.get("dosya", "?")), d.get("kanal_kaynagi", "yok: yalnız karışım")))
        for konu, hukum in kalibre_okuma(d):
            print("   %-20s %s" % (konu + ":", hukum))
    if len(R) < 2:
        print("\nTek rapor: öteki sayılar için mutlak eşik YOK. Beğenilmiş bir kayıtla yan yana verin.")
        return 0
    print("\n%-34s" % "ölçü" + "".join("%16s" % a[:15] for a in adlar) + ("   fark / gürültü" if len(R) == 2 else ""))
    for etiket, yol, bicim, gurultu in OLCULER:
        v = [deger(d, yol) for d in R]
        if all(x is None for x in v):
            continue
        satir = "%-34s" % etiket + "".join("%16s" % ("—" if x is None else bicim % x) for x in v)
        if len(R) == 2 and None not in v:
            fark = v[1] - v[0]
            if gurultu:
                kat = abs(fark) / gurultu
                satir += "   %+.3g  (%.0f kat%s)" % (fark, kat, "  ← OYNADI" if kat >= GURULTU_KATI else "")
            elif fark:
                satir += "   %+.3g" % fark
        print(satir)
    if len(R) == 2:
        a, b = (deger(d, "sozler/karsilastirma/sozcuk_hata_orani") for d in R)
        if a is not None and b is not None and b > 2 * a and b >= 5:
            print("\n! Sözcük hata oranı iki katını geçti (%%%.1f → %%%.1f): aynı vokal yeni karışımda kayboluyor olabilir (tek örneğe dayalı kural)." % (a, b))
        kaynak = [(d.get("kanal_kaynagi") or "").replace(", önbellekten", "") for d in R]
        if kaynak[0] != kaynak[1]:
            print("! Kanal kaynakları farklı (%s | %s): perde/akort/denge sayıları karşılaştırılamaz "
                  "(aynı vokal iki ayrı ayırmada 8,0 ve 15,5 cent ölçüldü)." % (kaynak[0] or "yok", kaynak[1] or "yok"))
        elif "otomatik" in kaynak[0]:
            print("! İki rapor da otomatik ayırmayla (--ayir): 'vokal − altyapı' ve akort farkı ayırma artığı olabilir "
                  "(kalibrasyonda −13,0 dB çıkan kayıt gerçek kanallarla +4,0 dB çıktı). Kanallar eldeyse --vokal/--altyapi ile ölçün.")
        print("\n'OYNADI' = fark, ölçüm gürültüsünün %g katından büyük (gürültü tek şarkıdan ölçüldü). Hangisinin daha İYİ olduğunu söylemez." % GURULTU_KATI)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
