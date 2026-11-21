#!/usr/bin/env python3
"""Rapor icin Markdown tablolarini sayilardan uretir (elle sayi kopyalamamak icin). Girdi: ara/*.json. Cikti: ara/tablolar.json"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from set import SET, KAL
M = {m["ad"]: m for m in json.load(open(os.path.join(KAL, "ara", "olcumler.json"), encoding="utf8"))}
SD = json.load(open(os.path.join(KAL, "ara", "soz_denetimi.json"), encoding="utf8"))
def oku(ad):
    y = os.path.join(KAL, "ara", ad)
    return json.load(open(y, encoding="utf8")) if os.path.exists(y) else {}
AK, UT, GK = oku("aksan_deneyi.json"), oku("unlu_tinisi.json"), oku("gercek_kanallar.json")
SIRA = [s["ad"] for s in SET]
KISA = {s["ad"]: s["yol"].replace(".mp3", "") for s in SET}
KISA["ali-baba__dogal_onizleme"] = "ali-baba/yeni3/…/dogal-onizleme"
KISA["ali-baba__demo_altyapi_sesli"] = "ali-baba/yeni/demo_altyapi_sesli"
KISA["ali-baba__ornek_kita1"] = "ali-baba/yeni/vokal/ornek_kita1"
KARAR = {"begendi": "beğendi", "reddetti": "reddetti"}

def s(v, n=1, isaret=False, yuzde=False):
    if v is None:
        return "–"
    if isinstance(v, bool):
        return "evet" if v else "hayır"
    if yuzde:
        return ("%%%.*f" % (n, 100 * v)).replace(".", ",")
    if isinstance(v, int) and not isaret:
        return str(v)
    return (("%+.*f" if isaret else "%.*f") % (n, v)).replace(".", ",")

def tablo(basliklar, satirlar):
    L = ["| " + " | ".join(basliklar) + " |", "|" + "|".join(["---"] * len(basliklar)) + "|"]
    for r in satirlar:
        L.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(L)

T = {}
ENERJI_ETIKET = {"el-yikama__coskulu_2": "**coşkulu diye seçildi**", "parmak-ailesi__coskulu_1": "**coşkulu diye seçildi**", "ali-baba__demo_altyapi_sesli": "**'olmuş'** (coşku istendikten sonra)",
                 "parmak-ailesi__yavas_2": "**'ninni gibi'**", "pitirin-ailesi__yavas_2": "**'ninni gibi'**", "el-yikama__sarki_1": "**'ninni gibi'**"}
def enerji_sira(ad):
    e = ENERJI_ETIKET.get(ad, "")
    return (0 if "seçildi" in e or "olmuş" in e else 2 if "ninni" in e else 1, -(M[ad].get("coca_cosku") or 0))
T["enerji"] = tablo(["Kayıt", "Kullanıcının coşku yargısı", "Hareketlilik puanı", "MusicCoCa coşku farkı", "CED 'ninni'", "Olay/sn", "Vurmalı/armonik dB", "Parlaklık Hz", "Hece/sn", "Aracın özet satırı"],
    [[KISA[a], ENERJI_ETIKET.get(a, "yargı yok (%s)" % KARAR[M[a]["karar"]]), s(M[a]["enerji_puani"], 0), s(M[a]["coca_cosku"], 2, True), s(M[a]["ced_ninni"], 3), s(M[a]["olay_sn"], 1), s(M[a]["vurmali_armonik_db"], 1, True),
      s(M[a]["parlaklik_hz"], 0), s(M[a]["hece_sn_obek_medyan"], 1), {"iyi": "coşkulu yana yakın", "dikkat": "ninni/sakin uyarısı", "bilgi": "yorum yok"}.get(M[a]["ozet"].get("Enerji / coşku"), "–")]
     for a in sorted([x for x in SIRA if x in M], key=enerji_sira)])

def soz_bulgu(a):
    k = (SD.get(a) or {}).get("kitalar") or []
    if not k:
        return "–"
    if "hayvan" in k[0]:
        return "; ".join("%s: %s%s" % (x["hayvan"] or "?", x["soylenen_ses"] or "–", "" if x["ses_hayvana_uyuyor"] else " ✗") for x in k)
    return "; ".join("%d. %s%s" % (i + 1, "+".join(x["adlar"]), "" if x["dogru"] or x["dogru"] is None else " ✗") for i, x in enumerate(k))
T["sozler"] = tablo(["Kayıt", "Karar", "Döküm", "Sözcük hata oranı", "Değişik / eksik / fazla", "Scribe'ın emin olmadığı sözcükler", "Kıta kıta yapısal denetim (✗ = uymuyor)"],
    [[KISA[a], KARAR[M[a]["karar"]], "bu çalışma" if (SD.get(a) or {}).get("guven") else ("eski dosya" if M[a]["wer"] is not None else "yok"), s(M[a]["wer"], 1, yuzde=True),
      "%s / %s / %s" % (s(M[a]["degisik"]), s(M[a]["eksik"]), s(M[a]["fazla"])) if M[a]["wer"] is not None else "–",
      (s(((SD.get(a) or {}).get("guven") or {}).get("oran_-0.3_alti"), 0, yuzde=True)) if (SD.get(a) or {}).get("guven") else "ölçülemedi", soz_bulgu(a)] for a in SIRA if a in M])

VOKAL_TURU = {"ali-baba__ornek_kita1": "**konuşma sentezi + vokoder**", "ali-baba__sarki_birlesik": "**esnetilmiş + perdesi düzlenmiş**", "ali-baba__dogal_onizleme": "doğal (dinle_2'nin vokali, başka orkestrada)",
              "ali-baba__demo_altyapi_sesli": "vokal yok (çalgısal)"}
def dog_sira(a):
    return (0 if a in ("ali-baba__ornek_kita1", "ali-baba__sarki_birlesik") else 2 if a == "ali-baba__demo_altyapi_sesli" else 1, SIRA.index(a))
T["dogallik"] = tablo(["Kayıt", "Vokal", "Karar", "Sözcük hata oranı", "Donmuş ünlü", "Nota içi oynaklık (cent)", "Izgaraya yapışma R", "Zarf titremesi dB", "Tiz doku", "Ünsüzde tiz dB", "Aracın işaretleri", "DNSMOS", "NISQA", "Distill", "UTMOS"],
    [[KISA[a], VOKAL_TURU.get(a, "doğal yapay şarkıcı"), KARAR[M[a]["karar"]], s(M[a]["wer"], 0, yuzde=True), s(M[a]["y_donmus_sure_orani"], 0, yuzde=True), s(M[a]["y_nota_ici_oynaklik_cent_medyan"], 1), s(M[a]["y_perde_izgaraya_yapisma_R"], 2),
      s(M[a]["y_zarf_titremesi_db"], 1, True), s(M[a]["y_tiz_doku_degisim_katsayisi"], 2), s(M[a]["y_unsuzlerde_tiz_payi_db"], 1, True),
      ("; ".join(x.split(":")[0].split("(")[0].strip() for x in (M[a]["y_isaretler"] or [])) or "yok"), s(M[a]["dnsmos"], 2), s(M[a]["nisqa"], 2), s(M[a]["distillmos"], 2), s(M[a]["utmos22"], 2)]
     for a in sorted([x for x in SIRA if x in M], key=dog_sira)])

def uy_sira(a):
    return (0 if a == "ali-baba__dogal_onizleme" else 2 if a == "ali-baba__demo_altyapi_sesli" else 1, SIRA.index(a))
T["uyum"] = tablo(["Kayıt", "Karar", "En iyi kaydırma (0 olmalı)", "Armonik destek (kaydırmasız)", "Destek farkı", "Gam içi", "±25 cent içinde", "Cent sapma", "Çakışan / uzun nota", "Ritim R", "Vokal − altyapı dB", "Sızıntı dB", "Aracın 'aynı armonide mi' satırı"],
    [[KISA[a], KARAR[M[a]["karar"]], s(M[a]["en_iyi_kaydirma"], 0, True) if M[a]["en_iyi_kaydirma"] is not None else "–", s(M[a]["destek_gercek"], 2), s(M[a]["destek_fark"], 2, True), s(M[a]["gam_ici"], 0, yuzde=True) + ("" if M[a]["gam_guvenilir"] else " (ton belirsiz)") if M[a]["gam_ici"] is not None else "–",
      ("%" + s(M[a]["yuzde_25cent"], 0)) if M[a]["yuzde_25cent"] is not None else "–", s(M[a]["cent_medyan"], 1), "%s / %s" % (s(M[a]["cakisan"]), s(M[a]["uzun_nota"])), s(M[a]["ritim_R"], 2), s(M[a]["vokal_eksi_altyapi_db"], 1, True), s(M[a]["sizinti_db"], 0, True),
      M[a]["ozet"].get("Vokal altyapıyla aynı armonide mi", "–")] for a in sorted([x for x in SIRA if x in M], key=uy_sira)])

PARMAK = ["parmak-ailesi__coskulu_1", "parmak-ailesi__duzgun_1", "parmak-ailesi__duzgun_2", "parmak-ailesi__turkce_2", "parmak-ailesi__yavas_2", "parmak-ailesi__sarki_2"]
def ak(a, k, alt="medyan"):
    v = (AK.get(a) or {}).get(k)
    return v.get(alt) if isinstance(v, dict) else None
def kita_araligi(a):
    k = (SD.get(a) or {}).get("kitalar") or []
    b = [x["bas_sn"] for x in k]
    d = [b[i + 1] - b[i] for i in range(len(b) - 1)]
    return (sum(d) / len(d)) if d else None
T["aksan"] = tablo(["Kayıt", "Karar ve gerekçe", "Sözcük hata oranı", "Scribe ortalama logprob", "Hece/sn", "'buradayım' süresi (sn)", "'parmak' r vekili (dB)", "'buradayım' son ünlü vekili (dB)", "DNSMOS", "NISQA", "UTMOS"],
    [[KISA[a], KARAR[M[a]["karar"]] + ": " + {"parmak-ailesi__coskulu_1": "seçilen kayıt", "parmak-ailesi__duzgun_1": "**'İngiliz gibi'**", "parmak-ailesi__duzgun_2": "**'İngiliz gibi'**", "parmak-ailesi__turkce_2": "sözler yanlış",
       "parmak-ailesi__yavas_2": "sözler yanlış + ninni", "parmak-ailesi__sarki_2": "çok hızlı"}[a], s(M[a]["wer"], 0, yuzde=True),
      s(((SD.get(a) or {}).get("guven") or {}).get("ortalama_logprob"), 3, True) if (SD.get(a) or {}).get("guven") else "yok (eski döküm)", s(M[a]["hece_sn_obek_medyan"], 1),
      s(((AK.get(a) or {}).get("sozcuk_suresi_sn") or {}).get("buradayım", [None])[0], 2), s(ak(a, "parmak_r_vekili_db"), 1, True), s(ak(a, "buradayim_son_unlu_on_art_db"), 1, True),
      s(M[a]["dnsmos"], 2), s(M[a]["nisqa"], 2), s(M[a]["utmos22"], 2)] for a in PARMAK if a in M])
T["hiz"] = tablo(["Kayıt", "Karar ve gerekçe", "Süre (sn)", "Kıtadan kıtaya ortalama süre (sn)", "Hece/sn (söz içi)", "Hece/sn (öbek medyanı)", "En hızlı öbek", "Aracın 'söyleyiş hızı' satırı"],
    [[KISA[a], KARAR[M[a]["karar"]] + (": **'sözler çok hızlı geçiyor'**" if a.endswith("sarki_2") else ""), s(M[a]["sure_sn"], 0), s(kita_araligi(a), 1), s(M[a]["hece_sn_soz_ici"], 1), s(M[a]["hece_sn_obek_medyan"], 1), s(M[a]["hece_sn_en_hizli"], 1),
      M[a]["ozet"].get("Söyleyiş hızı", "–")] for a in PARMAK if a in M])
T["sure"] = tablo(["Kayıt", "Karar", "Süre"], [[KISA[a], KARAR[M[a]["karar"]] + (" (**'çok uzun'**)" if a in ("ali-baba__coskulu_1", "ali-baba__coskulu_2") else ""), "%d sn (%d:%02d)" % (round(M[a]["sure_sn"]), M[a]["sure_sn"] // 60, round(M[a]["sure_sn"]) % 60)]
                                                for a in sorted([x for x in SIRA if x in M], key=lambda a: M[a]["sure_sn"])])
# aracin ozet satirlari: begenilen kayitlarda yanlis alarm, reddedilenlerde durum
KONU = ["Enerji / coşku", "Vokal / altyapı dengesi", "Vokal altyapıyla aynı armonide mi", "Gam içi söyleme", "Akort (detone mi)", "Çakışan uzun notalar", "Ritme oturma", "Yapaylık işaretleri (vekil)", "Sözler", "Söyleyiş hızı"]
IM = {"iyi": "✓", "dikkat": "!", "sorun": "✗", "bilgi": "·", "ölçülemedi": "?", None: "–"}
T["ozet_satirlari"] = tablo(["Kayıt", "Karar"] + ["Enerji", "Denge", "Armoni", "Gam içi", "Akort", "Çakışan nota", "Ritim", "Yapaylık", "Sözler", "Hız"] + ["! ve ✗ sayısı"],
    [[KISA[a], KARAR[M[a]["karar"]]] + [IM.get(M[a]["ozet"].get(k)) for k in KONU] + [sum(1 for k in KONU if M[a]["ozet"].get(k) in ("dikkat", "sorun"))] for a in SIRA if a in M])
# hayvan sesi (soylenen) tablosu
sat = []
for a in ("ali-baba__v2_2", "ali-baba__coskulu_1", "ali-baba__coskulu_2"):
    for k in (SD.get(a) or {}).get("kitalar", []):
        u = [r for r in UT.get(a, []) if k.get("ses_zamani") and k["ses_zamani"][0] - 0.01 <= r["bas"] <= k["ses_zamani"][1]]
        bant = " / ".join(s(r["bant_1800_2800_eksi_1200_1800_db"], 1, True) for r in u) if u else "–"
        sat.append([KISA[a], "%s. sn" % s(k["bas_sn"], 0), k["hayvan"] or "?", k["soylenen_ses"] or "–", "uyuyor" if k["ses_hayvana_uyuyor"] else "**uymuyor**", bant])
T["hayvan_sesi"] = tablo(["Kayıt", "Kıta başı", "Kıtanın hayvanı", "Dökümde söylenen ses", "Hayvana uyuyor mu (döküme göre)", "Ünlü tınısı, hece hece: 1,8–2,8 kHz eksi 1,2–1,8 kHz (dB)"], sat)
# gercek kanallar
if GK:
    sat = []
    for ad, g in GK.items():
        for yol_ad, m in g.items():
            sat.append([KISA.get(ad, ad), yol_ad, s(m.get("vokal_eksi_altyapi_db"), 1, True), s(m.get("en_iyi_kaydirma"), 0, True), s(m.get("destek_gercek"), 2), s(m.get("destek_fark"), 2, True), s(m.get("gam_ici"), 0, yuzde=True), s(m.get("akor_sesi"), 0, yuzde=True),
                        s(m.get("cent_medyan"), 1), ("%" + s(m.get("yuzde_25cent"), 0)) if m.get("yuzde_25cent") is not None else "–", "%s / %s" % (s(m.get("cakisan")), s(m.get("uzun_nota"))), s(m.get("ritim_R"), 2), s(m.get("ritim_kayma_ms"), 0, True),
                        s(m.get("y_donmus_sure_orani"), 0, yuzde=True), s(m.get("y_nota_ici_oynaklik_cent_medyan"), 1), s(m.get("y_perde_izgaraya_yapisma_R"), 2), s(m.get("y_zarf_titremesi_db"), 1, True), s(m.get("utmos22"), 2), s(m.get("nisqa"), 2)])
    T["gercek_kanallar"] = tablo(["Kayıt", "Kanallar", "Vokal − altyapı dB", "En iyi kaydırma", "Armonik destek", "Destek farkı", "Gam içi", "Akor sesi", "Cent sapma", "±25 cent", "Çakışan / uzun", "Ritim R", "Ritim kayması ms", "Donmuş ünlü", "Oynaklık (cent)", "Izgara R", "Zarf dB", "UTMOS", "NISQA"], sat)
json.dump(T, open(os.path.join(KAL, "ara", "tablolar.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
for k, v in T.items():
    print("\n##", k); print(v)
